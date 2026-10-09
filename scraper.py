#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rozgar Automated Exam Feed Scraper
Fetches active vacancies, admit cards, and results from public portals and official feeds,
normalizes them into Rozgar's structured schema (with All-India/State scopes, eligibility,
and 5-stage lifecycles), and updates vacancies.json safely.
"""

import sys
import os
import json
import re
import urllib.request
from datetime import datetime, timedelta

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
VACANCIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vacancies.json")

def fetch_html(url, timeout=15):
    """Fetch HTML content with standard headers and robust timeout."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[WARN] Failed to fetch {url}: {e}", file=sys.stderr)
    return None

def infer_scope_and_state(title, org=""):
    """Identify whether a recruitment is Central or State level."""
    combined = f"{title} {org}".upper()

    if any(k in combined for k in ["BIHAR", "BPSC", "BSSC", "CSBC", "BPSSC"]):
        return "State", "Bihar", False
    if any(k in combined for k in ["UPSSSC", "UP POLICE", "UPPBPB", "UPPSC", "UTTAR PRADESH"]) or re.search(r'\bUP\b', combined):
        return "State", "UP", False
    if any(k in combined for k in ["DELHI", "DSSSB"]):
        return "State", "Delhi", False
    if any(k in combined for k in ["RAJASTHAN", "RSMSSB", "RPSC"]):
        return "State", "Rajasthan", False
    if any(k in combined for k in ["JHARKHAND", "JSSC", "JPSC"]):
        return "State", "Jharkhand", False
    if any(k in combined for k in ["HARYANA", "HSSC", "HPSC"]):
        return "State", "Haryana", False
    if any(k in combined for k in ["MADHYA PRADESH", "MPESB", "MPPSC", "MP POLICE"]) or re.search(r'\bMP\b', combined):
        return "State", "MP", False
    if any(k in combined for k in ["ODISHA", "OSSC", "OPSC"]):
        return "State", "Odisha", False
    if any(k in combined for k in ["WEST BENGAL", "WBPSC", "WBPRB"]):
        return "State", "West Bengal", False

    # Default to Central / All-India (SSC, RRB, UPSC, Defence, Banking, Coast Guard, etc.)
    return "Central", "All-India", True

def infer_education(title):
    """Infer minimum educational criteria and category tag."""
    t = title.upper()
    if any(k in t for k in ["10TH", "MATRIC", "GD CONSTABLE", "MTS", "GROUP D"]):
        return "10TH", "10th Standard (Matriculation)", "10वीं कक्षा (मैट्रिक) उत्तीर्ण", "10th", "GEN_PHOTO"
    if any(k in t for k in ["12TH", "INTER", "CHSL", "CONSTABLE", "NAVIK", "NDA"]):
        return "12TH", "12th Standard (Intermediate)", "12वीं कक्षा (इंटरमीडिएट) उत्तीर्ण", "12th", "GEN_PHOTO"
    # Default: Graduate level
    return "GRADUATE", "Bachelor's Degree in Any Stream", "किसी भी विषय में स्नातक डिग्री उत्तीर्ण", "graduate", "GEN_PHOTO"

def clean_title(raw_text):
    """Clean title text by removing date stamps, trailing tags, and clutter."""
    cleaned = re.sub(r'\s+', ' ', raw_text).strip()
    cleaned = re.sub(r'\|\s*Last Date.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\(Last Date.*?\)', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'Apply Online.*$', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def slugify(text):
    """Generate a clean identifier for a job."""
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', text.upper()).strip('_')
    return slug[:40]

def parse_sarkari_result_page(html):
    """Parse Result, Admit Card, and Latest Jobs from public listings."""
    items = []
    if not html:
        return items

    # SarkariResult organizes sections inside div blocks or tables
    # Find links with relevant patterns
    link_pattern = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)

    # Patterns for categorization based on URL or anchor text
    for match in link_pattern.finditer(html):
        href = match.group(1).strip()
        raw_anchor = match.group(2)
        text = re.sub(r'<[^>]+>', '', raw_anchor).strip()

        if not text or len(text) < 10:
            continue

        # Filter out navigation links
        if any(nav in text.lower() for nav in ["home", "contact", "privacy", "disclaimer", "view more", "more..."]):
            continue

        href_lower = href.lower()
        category = None

        if "result" in href_lower or "result" in text.lower():
            category = "results"
        elif "admit" in href_lower or "admit" in text.lower() or "hall ticket" in text.lower():
            category = "admit-card"
        elif any(k in href_lower for k in ["recruitment", "vacancy", "online", "apply", "form"]) or any(k in text.lower() for k in ["online form", "recruitment", "vacancy", "apply"]):
            category = "jobs"

        if not category:
            continue

        title = clean_title(text)
        if len(title) < 12:
            continue

        items.append({
            "category": category,
            "title": title,
            "url": href
        })

    return items

def build_vacancy_object(scraped_item):
    """Construct a full Rozgar vacancy schema object from scraped snippet."""
    title = scraped_item["title"]
    category = scraped_item["category"]
    url = scraped_item["url"]

    scope, state, is_central = infer_scope_and_state(title)
    min_edu, edu_en, edu_hi, cat_tag, preset_key = infer_education(title)

    today = datetime.now()
    start_date = (today - timedelta(days=10)).strftime("%Y-%m-%d")
    last_date = (today + timedelta(days=25)).strftime("%Y-%m-%d")
    cutoff_date = f"{today.year}-07-01"

    # Default Age bounds
    min_age = 18
    max_age_gen = 30 if min_edu == "10TH" else (32 if min_edu == "12TH" else 35)

    item_id = slugify(title) + f"_{today.year}"

    # Extract organization name heuristics
    org_match = re.search(r'^(SSC|UPSC|RRB|BPSC|BSSC|DSSSB|UPSSSC|RSMSSB|JSSC|NTA|IBPS|SBI|CSBC)', title, re.IGNORECASE)
    org_name = org_match.group(1).upper() if org_match else "Recruitment Board"

    return {
        "id": item_id,
        "category": category,
        "scope": scope,
        "state": state,
        "isCentral": is_central,
        "title": title,
        "title_hi": title,
        "title_hinglish": title,
        "org": f"{org_name} Govt Exam",
        "org_hi": f"{org_name} सरकारी भर्ती",
        "org_hinglish": f"{org_name} Govt Exam",
        "vacancies": "Various Posts",
        "vacancies_hi": "विभिन्न पद",
        "vacancies_hinglish": "Various Posts",
        "startDate": start_date,
        "lastDate": last_date,
        "cutoffDate": cutoff_date,
        "fee": "₹100–₹500 (Per Official Notice)",
        "fee_hi": "₹100–₹500 (विज्ञप्ति अनुसार)",
        "fee_hinglish": "₹100–₹500 (Official Notice ke mutabik)",
        "minAge": min_age,
        "maxAge": {
            "GENERAL_MALE": max_age_gen,
            "GENERAL_FEMALE": max_age_gen,
            "EWS_MALE": max_age_gen,
            "EWS_FEMALE": max_age_gen,
            "BC_OBC2_MALE": max_age_gen + 3,
            "BC_OBC2_FEMALE": max_age_gen + 3,
            "EBC_OBC1_MALE": max_age_gen + 3,
            "EBC_OBC1_FEMALE": max_age_gen + 3,
            "SC_MALE": max_age_gen + 5,
            "SC_FEMALE": max_age_gen + 5,
            "ST_MALE": max_age_gen + 5,
            "ST_FEMALE": max_age_gen + 5
        },
        "minEducation": min_edu,
        "minEduLabel": edu_en,
        "minEduLabel_hi": edu_hi,
        "minEduLabel_hinglish": edu_en,
        "categoryTag": cat_tag,
        "presetKey": preset_key,
        "officialApplyUrl": url if url.startswith("http") else "https://www.sarkariresult.com",
        "requiredDocs": [
            {"key": "m10", "name": "10th Marksheet", "name_hi": "10वीं अंकतालिका", "name_hinglish": "10th Marksheet", "mandatory": True},
            {"key": "id", "name": "Aadhaar Card", "name_hi": "आधार कार्ड", "name_hinglish": "Aadhaar Card", "mandatory": True},
            {"key": "dom", "name": f"{state} Domicile" if state != "All-India" else "Domicile Certificate", "name_hi": "निवास प्रमाण पत्र", "name_hinglish": "Domicile", "mandatory": True}
        ],
        "lifecycle": [
            {"stage": "apply", "status": "active" if category == "jobs" else "completed", "titleEn": "Application Window", "titleHi": "आवेदन प्रक्रिया", "titleHinglish": "Application Window", "dateEn": "Active" if category == "jobs" else "Closed", "dateHi": "सक्रिय" if category == "jobs" else "सम्पन्न", "dateHinglish": "Active" if category == "jobs" else "Closed"},
            {"stage": "admit", "status": "active" if category == "admit-card" else ("upcoming" if category == "jobs" else "completed"), "titleEn": "Admit Card", "titleHi": "प्रवेश पत्र जारी", "titleHinglish": "Admit Card", "dateEn": "Available Now" if category == "admit-card" else "Upcoming", "dateHi": "उपलब्ध" if category == "admit-card" else "आगामी", "dateHinglish": "Available Now" if category == "admit-card" else "Upcoming"},
            {"stage": "exam", "status": "upcoming" if category != "results" else "completed", "titleEn": "Exam Date", "titleHi": "परीक्षा तिथि", "titleHinglish": "Exam Date", "dateEn": "Check Notice", "dateHi": "विज्ञप्ति देखें", "dateHinglish": "Check Notice"},
            {"stage": "anskey", "status": "pending" if category != "results" else "completed", "titleEn": "Answer Key", "titleHi": "उत्तर कुंजी", "titleHinglish": "Answer Key", "dateEn": "Pending", "dateHi": "प्रतीक्षित", "dateHinglish": "Pending"},
            {"stage": "result", "status": "active" if category == "results" else "pending", "titleEn": "Result / Scorecard", "titleHi": "अंतिम परिणाम", "titleHinglish": "Final Result", "dateEn": "Declared" if category == "results" else "Pending", "dateHi": "घोषित" if category == "results" else "प्रतीक्षित", "dateHinglish": "Declared" if category == "results" else "Pending"}
        ]
    }

def run_sync():
    """Main synchronization routine."""
    print(f"[{datetime.now().isoformat()}] Starting Rozgar Vacancy Auto-Sync...")

    # 1. Load existing curated vacancies
    existing_vacancies = []
    if os.path.exists(VACANCIES_FILE):
        try:
            with open(VACANCIES_FILE, "r", encoding="utf-8") as f:
                existing_vacancies = json.load(f)
            print(f"[OK] Loaded {len(existing_vacancies)} existing vacancies from vacancies.json")
        except Exception as e:
            print(f"[WARN] Error reading vacancies.json: {e}", file=sys.stderr)

    existing_ids = {v.get("id"): v for v in existing_vacancies}

    # 2. Fetch fresh listings from public portals
    scraped_items = []
    portal_html = fetch_html("https://www.sarkariresult.com/")
    if portal_html:
        scraped_items = parse_sarkari_result_page(portal_html)
        print(f"[OK] Parsed {len(scraped_items)} potential updates from portal")
    else:
        print("[INFO] Live portal unreachable or blocked. Preserving verified dataset.")

    # 3. Merge and deduplicate
    added_count = 0
    updated_count = 0

    for item in scraped_items[:25]:  # Process top 25 fresh items
        cand_obj = build_vacancy_object(item)
        c_id = cand_obj["id"]

        if c_id not in existing_ids:
            # Check if similar title already exists
            title_prefix = cand_obj["title"][:25].upper()
            duplicate = any(v.get("title", "")[:25].upper() == title_prefix for v in existing_vacancies)
            if not duplicate:
                existing_vacancies.append(cand_obj)
                existing_ids[c_id] = cand_obj
                added_count += 1
        else:
            # Update category/dates if needed
            existing_vac = existing_ids[c_id]
            if existing_vac.get("category") != cand_obj["category"]:
                existing_vac["category"] = cand_obj["category"]
                existing_vac["lifecycle"] = cand_obj["lifecycle"]
                updated_count += 1

    # Ensure all entries have valid scope & state
    for v in existing_vacancies:
        if not v.get("scope") or not v.get("state"):
            scope, state, is_central = infer_scope_and_state(v.get("title", ""), v.get("org", ""))
            v["scope"] = scope
            v["state"] = state
            v["isCentral"] = is_central

    # 4. Save back to vacancies.json atomically
    temp_file = VACANCIES_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(existing_vacancies, f, ensure_ascii=False, indent=2)

    os.replace(temp_file, VACANCIES_FILE)
    print(f"[SUCCESS] vacancies.json updated successfully. Added: {added_count}, Updated: {updated_count}, Total: {len(existing_vacancies)}")

if __name__ == "__main__":
    run_sync()
