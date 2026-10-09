#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rozgar Master Recruitment Data Aggregator & Pipeline
Executes all board scrapers in parallel, normalizes records into the standard Rozgar schema,
performs robust deduplication, and atomically updates data/vacancies.json and root vacancies.json.
"""

import os
import sys
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scrapers.ssc_scraper import SSCScraper
from scrapers.upsc_scraper import UPSCScraper
from scrapers.rrb_scraper import RRBScraper
from scrapers.ibps_scraper import IBPSScraper
from scrapers.state_psc_scraper import StatePSCScraper

DATA_DIR = os.path.join(REPO_ROOT, "data")
DATA_FILE = os.path.join(DATA_DIR, "vacancies.json")
ROOT_FILE = os.path.join(REPO_ROOT, "vacancies.json")

def load_existing_dataset():
    """Load existing dataset from data/vacancies.json or root vacancies.json."""
    target_path = DATA_FILE if os.path.exists(DATA_FILE) else ROOT_FILE
    if os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"[WARN] Could not parse existing dataset at {target_path}: {e}", file=sys.stderr)
    return []

def run_scraper(scraper_instance):
    """Safely run a single scraper instance and return its structured items."""
    try:
        t0 = time.time()
        items = scraper_instance.scrape()
        elapsed = time.time() - t0
        print(f"[PIPELINE] {scraper_instance.name}: collected {len(items)} items in {elapsed:.2f}s")
        return items
    except Exception as e:
        print(f"[PIPELINE] [ERROR] Scraper {scraper_instance.name} failed: {e}", file=sys.stderr)
        return []

def deduplicate_and_merge(existing_items, fresh_items):
    """
    Deduplicate by ID and normalized title prefix.
    Preserves rich historical data while updating dynamic fields (status, links, dates).
    """
    merged = list(existing_items)
    index_by_id = {item.get("id"): item for item in merged if item.get("id")}
    index_by_title = {item.get("title", "")[:30].upper(): item for item in merged if item.get("title")}

    added = 0
    updated = 0

    for fresh in fresh_items:
        f_id = fresh.get("id")
        f_title_prefix = fresh.get("title", "")[:30].upper()

        target = None
        if f_id and f_id in index_by_id:
            target = index_by_id[f_id]
        elif f_title_prefix and f_title_prefix in index_by_title:
            target = index_by_title[f_title_prefix]

        if target:
            # Update dynamic fields
            changed = False
            for key in ["category", "status", "last_date", "lastDate", "apply_link", "officialApplyUrl", "notification_pdf", "admit_card_link", "result_link", "lifecycle"]:
                val = fresh.get(key)
                if val and target.get(key) != val:
                    target[key] = val
                    changed = True
            if changed:
                updated += 1
        else:
            merged.append(fresh)
            if f_id:
                index_by_id[f_id] = fresh
            if f_title_prefix:
                index_by_title[f_title_prefix] = fresh
            added += 1

    return merged, added, updated

def atomic_save(dataset):
    """Atomically write dataset to data/vacancies.json and sync to root vacancies.json."""
    os.makedirs(DATA_DIR, exist_ok=True)

    json_str = json.dumps(dataset, ensure_ascii=False, indent=2)

    # 1. Save data/vacancies.json
    tmp_data = DATA_FILE + ".tmp"
    with open(tmp_data, "w", encoding="utf-8") as f:
        f.write(json_str)
    os.replace(tmp_data, DATA_FILE)

    # 2. Sync root vacancies.json for backward compatibility
    tmp_root = ROOT_FILE + ".tmp"
    with open(tmp_root, "w", encoding="utf-8") as f:
        f.write(json_str)
    os.replace(tmp_root, ROOT_FILE)

def main():
    print("=" * 65)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Rozgar Automated Data Pipeline Starting...")
    print("=" * 65)

    existing_data = load_existing_dataset()
    print(f"[PIPELINE] Baseline dataset loaded: {len(existing_data)} vacancies.")

    scrapers = [
        SSCScraper(),
        UPSCScraper(),
        RRBScraper(),
        IBPSScraper(),
        StatePSCScraper()
    ]

    fresh_collected = []
    # Run scrapers in parallel with thread pool
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(run_scraper, sc): sc.name for sc in scrapers}
        for future in as_completed(futures):
            sc_name = futures[future]
            try:
                items = future.result()
                if items:
                    fresh_collected.extend(items)
            except Exception as e:
                print(f"[PIPELINE] Exception in future for {sc_name}: {e}", file=sys.stderr)

    print(f"[PIPELINE] Total fresh records harvested: {len(fresh_collected)}")

    merged_data, added_count, updated_count = deduplicate_and_merge(existing_data, fresh_collected)

    atomic_save(merged_data)

    # Print Summary Breakdown
    categories = {}
    scopes = {}
    quals = {}
    for v in merged_data:
        cat = v.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        sc = v.get("scope", "Central")
        scopes[sc] = scopes.get(sc, 0) + 1
        q = v.get("qualification") or v.get("minEducation") or "GRADUATE"
        quals[q] = quals.get(q, 0) + 1

    print("-" * 65)
    print(f"[SUCCESS] Pipeline Finished Successfully!")
    print(f" • Total Records in Dataset: {len(merged_data)}")
    print(f" • Newly Added: {added_count}")
    print(f" • Updated: {updated_count}")
    print(f" • Category Breakdown: {dict(categories)}")
    print(f" • Scope Breakdown: {dict(scopes)}")
    print(f" • Qualification Breakdown: {dict(quals)}")
    print(f" • Files Saved: {DATA_FILE} & {ROOT_FILE}")
    print("=" * 65)

if __name__ == "__main__":
    main()
