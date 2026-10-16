#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rozgar Multi-Source Aggregator Scraper
Fetches active vacancies, admit cards, results, and answer keys from:
- Sarkari Result (sarkariresult.com)
- FreeJobAlert (freejobalert.com)
- Result Bharat (resultbharat.com)
- SarkariExam (sarkariexam.com)
- Rojgar Result (rojgarresult.com)
- Jagran Josh (jagranjosh.com/jobs)

Performs comprehensive cross-portal deduplication, text sanitization,
uniform schema generation, and updates data/vacancies.json atomically.
"""

import os
import sys
import json
import re
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
DATA_FILE = os.path.join(DATA_DIR, "vacancies.json")
ROOT_FILE = os.path.join(REPO_ROOT, "vacancies.json")

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Referer": "https://www.google.com/"
}

# -------------------------------------------------------------
# Heuristics & Classification Helpers
# -------------------------------------------------------------
def clean_text(raw):
    if not raw:
        return ""
    text = re.sub(r'<[^>]+>', ' ', str(raw))
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    # Remove common promotional or noise words
    text = re.sub(r'\|\s*Apply Online.*$', '', text, flags=re.I)
    text = re.sub(r'\|\s*Last Date.*$', '', text, flags=re.I)
    text = re.sub(r'\(Last Date.*?\)', '', text, flags=re.I)
    text = re.sub(r'Online Form\s*\d{4}', '', text, flags=re.I)
    text = re.sub(r'Click Here.*$', '', text, flags=re.I)
    return text.strip(" -|:")

def infer_category(title, url=""):
    combined = f"{title} {url}".lower()
    if any(k in combined for k in ["admit card", "admit-card", "hall ticket", "call letter"]):
        return "Admit Cards"
    if any(k in combined for k in ["answer key", "ans key", "ans-key", "key challenge"]):
        return "Results & Keys"
    if any(k in combined for k in ["result", "marks", "scorecard", "merit list", "cutoff"]):
        return "Results & Keys"
    if any(k in combined for k in ["admission", "counseling", "counselling", "entrance"]):
        return "Admission"
    if any(k in combined for k in ["syllabus", "exam pattern"]):
        return "Syllabus"
    return "Latest Jobs"

def infer_qualification(title):
    t = title.upper()
    if any(k in t for k in ["10TH", "MATRIC", "HIGH SCHOOL", "MTS", "GROUP D", "DRIVER", "SWEEPER"]):
        return "10th Pass", "10TH"
    if any(k in t for k in ["ITI", "APPRENTICE", "TRADE CERTIFICATE"]):
        return "ITI", "ITI"
    if any(k in t for k in ["12TH", "INTERMEDIATE", "10+2", "CHSL", "CONSTABLE", "NAVIK", "NDA"]):
        return "12th Pass", "12TH"
    if any(k in t for k in ["GRADUATE", "DEGREE", "BACHELOR", "CGL", "OFFICER", "INSPECTOR", "SI ", "DAROGA", "PO ", "CLERK", "B.TECH", "B.E"]):
        return "Graduate", "GRADUATE"
    return "Other", "GRADUATE"

def infer_organization(title):
    t = title.upper()
    org_map = [
        (r'\bSSC\b|STAFF SELECTION', "Staff Selection Commission (SSC)"),
        (r'\bUPSC\b|UNION PUBLIC', "Union Public Service Commission (UPSC)"),
        (r'\bRRB\b|\bRAILWAY\b|\bRPF\b', "Railway Recruitment Board (RRB)"),
        (r'\bIBPS\b|\bSBI\b|\bBANK\b', "Banking / IBPS"),
        (r'\bBPSC\b', "Bihar Public Service Commission (BPSC)"),
        (r'\bBSSC\b', "Bihar Staff Selection Commission (BSSC)"),
        (r'\bCSBC\b|\bBPSSC\b|BIHAR POLICE', "Bihar Police Recruitment"),
        (r'\bUPSSSC\b', "Uttar Pradesh Subordinate Services (UPSSSC)"),
        (r'\bUPPSC\b', "Uttar Pradesh Public Service Commission (UPPSC)"),
        (r'\bUPPBPB\b|UP POLICE', "Uttar Pradesh Police Recruitment (UPPRPB)"),
        (r'\bDSSSB\b', "Delhi Subordinate Services Selection Board (DSSSB)"),
        (r'\bRSMSSB\b|\bRPSC\b|RAJASTHAN', "Rajasthan Recruitment Board (RSMSSB/RPSC)"),
        (r'\bJSSC\b|\bJPSC\b|JHARKHAND', "Jharkhand Staff Selection Commission (JSSC)"),
        (r'\bNTA\b', "National Testing Agency (NTA)"),
        (r'\bCOAST GUARD\b|ICG', "Indian Coast Guard (ICG)"),
        (r'\bNAVY\b', "Indian Navy"),
        (r'\bAIR FORCE\b|\bAFCAT\b', "Indian Air Force"),
        (r'\bARMY\b|\bAGNIVEER\b', "Indian Army")
    ]
    for pattern, org_name in org_map:
        if re.search(pattern, t):
            return org_name
    # Default fallback
    words = title.split()
    return " ".join(words[:2]) + " Recruitment" if len(words) >= 2 else "Govt Recruitment Board"

def infer_scope_and_state(title, org):
    combined = f"{title} {org}".upper()
    if any(k in combined for k in ["BIHAR", "BPSC", "BSSC", "CSBC", "BPSSC"]):
        return "State", "Bihar", False
    if any(k in combined for k in ["UTTAR PRADESH", "UPSSSC", "UPPBPB", "UPPSC"]) or re.search(r'\bUP\b', combined):
        return "State", "UP", False
    if any(k in combined for k in ["DELHI", "DSSSB"]):
        return "State", "Delhi", False
    if any(k in combined for k in ["RAJASTHAN", "RSMSSB", "RPSC"]):
        return "State", "Rajasthan", False
    if any(k in combined for k in ["JHARKHAND", "JSSC", "JPSC"]):
        return "State", "Jharkhand", False
    if any(k in combined for k in ["HARYANA", "HSSC", "HPSC"]):
        return "State", "Haryana", False
    if any(k in combined for k in ["MADHYA PRADESH", "MPESB", "MPPSC"]) or re.search(r'\bMP\b', combined):
        return "State", "MP", False
    if any(k in combined for k in ["ODISHA", "OSSC", "OPSC"]):
        return "State", "Odisha", False
    if any(k in combined for k in ["WEST BENGAL", "WBPSC", "WBPRB"]):
        return "State", "West Bengal", False
    return "Central", "All-India", True

def extract_posts_count(title):
    match = re.search(r'(\d[\d,]*)\s*(?:Post|Posts|Vacancy|Vacancies|Pad|Pado)', title, re.I)
    if match:
        return f"{match.group(1)} Posts"
    return "Various Posts"

def slugify(text):
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', text.upper()).strip('_')
    return slug[:45]

# -------------------------------------------------------------
# Portal Scrapers
# -------------------------------------------------------------
def scrape_sarkari_result():
    items = []
    url = "https://www.sarkariresult.com/"
    try:
        resp = requests.get(url, headers=COMMON_HEADERS, timeout=12)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                text = clean_text(a.get_text())
                href = a["href"].strip()
                if len(text) < 12 or not href.startswith("http"):
                    continue
                if any(noise in text.lower() for noise in ["home", "contact", "disclaimer", "privacy", "syllabus", "view more"]):
                    continue
                if any(kw in href.lower() or kw in text.lower() for kw in ["job", "recruitment", "vacancy", "admit", "result", "answer", "online"]):
                    items.append({
                        "raw_title": text,
                        "url": href,
                        "source": "SarkariResult"
                    })
    except Exception as e:
        print(f"[WARN] SarkariResult scrape error: {e}", file=sys.stderr)
    return items

def scrape_free_job_alert():
    items = []
    url = "https://www.freejobalert.com/"
    try:
        resp = requests.get(url, headers=COMMON_HEADERS, timeout=12)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                text = clean_text(a.get_text())
                href = a["href"].strip()
                if len(text) < 14 or not href.startswith("http"):
                    continue
                if any(kw in href.lower() or kw in text.lower() for kw in ["posts", "recruitment", "admit", "result", "answer-key"]):
                    items.append({
                        "raw_title": text,
                        "url": href,
                        "source": "FreeJobAlert"
                    })
    except Exception as e:
        print(f"[WARN] FreeJobAlert scrape error: {e}", file=sys.stderr)
    return items

def scrape_result_bharat():
    items = []
    url = "https://www.resultbharat.com/"
    try:
        resp = requests.get(url, headers=COMMON_HEADERS, timeout=12)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                text = clean_text(a.get_text())
                href = a["href"].strip()
                if len(text) < 12 or not href.startswith("http"):
                    continue
                if any(kw in href.lower() or kw in text.lower() for kw in ["recruitment", "online", "admit", "result", "answer"]):
                    items.append({
                        "raw_title": text,
                        "url": href,
                        "source": "ResultBharat"
                    })
    except Exception as e:
        print(f"[WARN] ResultBharat scrape error: {e}", file=sys.stderr)
    return items

def scrape_sarkari_exam():
    items = []
    url = "https://www.sarkariexam.com/"
    try:
        resp = requests.get(url, headers=COMMON_HEADERS, timeout=12)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                text = clean_text(a.get_text())
                href = a["href"].strip()
                if len(text) < 12 or not href.startswith("http"):
                    continue
                if any(kw in href.lower() or kw in text.lower() for kw in ["job", "recruitment", "admit", "result", "form"]):
                    items.append({
                        "raw_title": text,
                        "url": href,
                        "source": "SarkariExam"
                    })
    except Exception as e:
        print(f"[WARN] SarkariExam scrape error: {e}", file=sys.stderr)
    return items

def scrape_rojgar_result():
    items = []
    url = "https://www.rojgarresult.com/"
    try:
        resp = requests.get(url, headers=COMMON_HEADERS, timeout=12)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                text = clean_text(a.get_text())
                href = a["href"].strip()
                if len(text) < 12 or not href.startswith("http"):
                    continue
                if any(kw in href.lower() or kw in text.lower() for kw in ["recruitment", "online", "admit", "result", "post"]):
                    items.append({
                        "raw_title": text,
                        "url": href,
                        "source": "RojgarResult"
                    })
    except Exception as e:
        print(f"[WARN] RojgarResult scrape error: {e}", file=sys.stderr)
    return items

def scrape_jagran_josh():
    items = []
    url = "https://www.jagranjosh.com/jobs"
    try:
        resp = requests.get(url, headers=COMMON_HEADERS, timeout=12)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                text = clean_text(a.get_text())
                href = a["href"].strip()
                if len(text) < 15:
                    continue
                full_href = href if href.startswith("http") else f"https://www.jagranjosh.com{href}"
                if any(kw in full_href.lower() or kw in text.lower() for kw in ["recruitment", "jobs", "vacancy", "admit", "result"]):
                    items.append({
                        "raw_title": text,
                        "url": full_href,
                        "source": "JagranJosh"
                    })
    except Exception as e:
        print(f"[WARN] JagranJosh scrape error: {e}", file=sys.stderr)
    return items

# -------------------------------------------------------------
# Normalizer & Builder
# -------------------------------------------------------------
def build_aggregated_entry(raw_entry):
    title = clean_text(raw_entry["raw_title"])
    url = raw_entry["url"]
    source = raw_entry.get("source", "Aggregator")

    category = infer_category(title, url)
    qualification, qual_code = infer_qualification(title)
    organization = infer_organization(title)
    scope, state, is_central = infer_scope_and_state(title, organization)
    posts = extract_posts_count(title)

    today = datetime.now()
    start_date = (today - timedelta(days=10)).strftime("%Y-%m-%d")
    last_date = (today + timedelta(days=20)).strftime("%Y-%m-%d")
    cutoff_date = f"{today.year}-07-01"

    item_id = slugify(f"{organization}_{title}") + f"_{today.year}"

    # Standard internal category slug for UI
    cat_slug = "jobs"
    if category == "Admit Cards":
        cat_slug = "admit-card"
    elif category in ["Results & Keys", "Answer Key"]:
        cat_slug = "results"
    elif category == "Admission":
        cat_slug = "schemes-admissions"

    preset_key = "BSSC_PHOTO" if state == "Bihar" else ("SSC_PHOTO" if "SSC" in organization else "GEN_PHOTO")

    return {
        # Strict user-specified schema fields
        "id": item_id,
        "title": title,
        "organization": organization,
        "category": category,
        "qualification": qualification,
        "posts": posts,
        "last_date": last_date,
        "apply_link": url,
        "source": source,

        # Frontend-compatible dual fields (preserving 100% existing UI stability)
        "org": organization,
        "org_hi": organization,
        "org_hinglish": organization,
        "title_hi": title,
        "title_hinglish": title,
        "categoryTag": qualification.lower().replace(" ", ""),
        "minEducation": qual_code,
        "minEduLabel": f"{qualification} from recognized board/university",
        "minEduLabel_hi": f"मान्यता प्राप्त संस्थान से {qualification}",
        "minEduLabel_hinglish": f"{qualification} pass",
        "posts_count": posts,
        "vacancies": posts,
        "vacancies_hi": posts,
        "vacancies_hinglish": posts,
        "start_date": start_date,
        "startDate": start_date,
        "lastDate": last_date,
        "cutoff_date": cutoff_date,
        "cutoffDate": cutoff_date,
        "officialApplyUrl": url,
        "scope": scope,
        "state": state,
        "isCentral": is_central,
        "preset_key": preset_key,
        "presetKey": preset_key,
        "status": "Active" if cat_slug == "jobs" else ("Available" if cat_slug == "admit-card" else "Declared"),
        "fee": "₹100–₹500 (As per notification)",
        "fee_hi": "₹100–₹500 (विज्ञप्ति अनुसार)",
        "fee_hinglish": "₹100–₹500 (Notice ke hisaab se)",
        "min_age": 18,
        "minAge": 18,
        "max_age": {
            "GENERAL_MALE": 35, "GENERAL_FEMALE": 35,
            "EWS_MALE": 35, "EWS_FEMALE": 35,
            "BC_OBC2_MALE": 38, "BC_OBC2_FEMALE": 38,
            "EBC_OBC1_MALE": 38, "EBC_OBC1_FEMALE": 38,
            "SC_MALE": 40, "SC_FEMALE": 40,
            "ST_MALE": 40, "ST_FEMALE": 40
        },
        "maxAge": {
            "GENERAL_MALE": 35, "GENERAL_FEMALE": 35,
            "EWS_MALE": 35, "EWS_FEMALE": 35,
            "BC_OBC2_MALE": 38, "BC_OBC2_FEMALE": 38,
            "EBC_OBC1_MALE": 38, "EBC_OBC1_FEMALE": 38,
            "SC_MALE": 40, "SC_FEMALE": 40,
            "ST_MALE": 40, "ST_FEMALE": 40
        },
        "required_docs": [
            {"key": "m10", "name": "10th Marksheet", "name_hi": "10वीं अंकतालिका", "name_hinglish": "10th Marksheet", "mandatory": True},
            {"key": "id", "name": "Aadhaar Card", "name_hi": "आधार कार्ड", "name_hinglish": "Aadhaar Card", "mandatory": True},
            {"key": "dom", "name": f"{state} Domicile" if state != "All-India" else "Domicile Certificate", "name_hi": "निवास प्रमाण पत्र", "name_hinglish": "Domicile", "mandatory": True}
        ],
        "requiredDocs": [
            {"key": "m10", "name": "10th Marksheet", "name_hi": "10वीं अंकतालिका", "name_hinglish": "10th Marksheet", "mandatory": True},
            {"key": "id", "name": "Aadhaar Card", "name_hi": "आधार कार्ड", "name_hinglish": "Aadhaar Card", "mandatory": True},
            {"key": "dom", "name": f"{state} Domicile" if state != "All-India" else "Domicile Certificate", "name_hi": "निवास प्रमाण पत्र", "name_hinglish": "Domicile", "mandatory": True}
        ],
        "lifecycle": [
            {"stage": "apply", "status": "active" if cat_slug == "jobs" else "completed", "titleEn": "Application Window", "titleHi": "आवेदन प्रक्रिया", "titleHinglish": "Application Window", "dateEn": "Active" if cat_slug == "jobs" else "Closed", "dateHi": "सक्रिय" if cat_slug == "jobs" else "सम्पन्न", "dateHinglish": "Active" if cat_slug == "jobs" else "Closed"},
            {"stage": "admit", "status": "active" if cat_slug == "admit-card" else ("upcoming" if cat_slug == "jobs" else "completed"), "titleEn": "Admit Card", "titleHi": "प्रवेश पत्र जारी", "titleHinglish": "Admit Card", "dateEn": "Live Now" if cat_slug == "admit-card" else "Upcoming", "dateHi": "जारी हो चुका" if cat_slug == "admit-card" else "आगामी", "dateHinglish": "Live Now" if cat_slug == "admit-card" else "Upcoming"},
            {"stage": "exam", "status": "upcoming" if cat_slug != "results" else "completed", "titleEn": "Written Examination", "titleHi": "लिखित परीक्षा", "titleHinglish": "Written Exam", "dateEn": "See Notice", "dateHi": "विज्ञप्ति देखें", "dateHinglish": "See Notice"},
            {"stage": "anskey", "status": "pending" if cat_slug != "results" else "completed", "titleEn": "Answer Key", "titleHi": "उत्तर कुंजी", "titleHinglish": "Answer Key", "dateEn": "Pending", "dateHi": "प्रतीक्षित", "dateHinglish": "Pending"},
            {"stage": "result", "status": "active" if cat_slug == "results" else "pending", "titleEn": "Final Result & Cutoff", "titleHi": "अंतिम परिणाम व कट-ऑफ", "titleHinglish": "Final Result", "dateEn": "Declared" if cat_slug == "results" else "Pending", "dateHi": "घोषित" if cat_slug == "results" else "प्रतीक्षित", "dateHinglish": "Declared" if cat_slug == "results" else "Pending"}
        ]
    }

# -------------------------------------------------------------
# Main Aggregator & Deduplication Pipeline
# -------------------------------------------------------------
def load_existing():
    target = DATA_FILE if os.path.exists(DATA_FILE) else ROOT_FILE
    if os.path.exists(target):
        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []

def deduplicate_and_merge(existing_list, incoming_entries):
    merged = list(existing_list)
    index_by_id = {item.get("id"): item for item in merged if item.get("id")}
    index_by_norm = {re.sub(r'[^A-Z0-9]', '', item.get("title", "").upper())[:24]: item for item in merged if item.get("title")}

    added = 0
    updated = 0

    for inc in incoming_entries:
        i_id = inc["id"]
        i_norm = re.sub(r'[^A-Z0-9]', '', inc["title"].upper())[:24]

        target = None
        if i_id in index_by_id:
            target = index_by_id[i_id]
        elif i_norm in index_by_norm:
            target = index_by_norm[i_norm]

        if target:
            # Combine/Merge duplicate sources
            sources = target.get("source", "")
            if inc["source"] not in sources:
                target["source"] = f"{sources}, {inc['source']}".strip(", ")
            # Update dynamic links or dates if missing
            if not target.get("apply_link") and inc.get("apply_link"):
                target["apply_link"] = inc["apply_link"]
                target["officialApplyUrl"] = inc["apply_link"]
            updated += 1
        else:
            merged.append(inc)
            index_by_id[i_id] = inc
            index_by_norm[i_norm] = inc
            added += 1

    return merged, added, updated

def atomic_save(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    json_str = json.dumps(data, ensure_ascii=False, indent=2)

    # 1. Primary: data/vacancies.json
    tmp1 = DATA_FILE + ".tmp"
    with open(tmp1, "w", encoding="utf-8") as f:
        f.write(json_str)
    os.replace(tmp1, DATA_FILE)

    # 2. Sync alias: vacancies.json
    tmp2 = ROOT_FILE + ".tmp"
    with open(tmp2, "w", encoding="utf-8") as f:
        f.write(json_str)
    os.replace(tmp2, ROOT_FILE)

    # 3. Sync embedded fallback in index.html
    index_html = os.path.join(REPO_ROOT, "index.html")
    if os.path.exists(index_html):
        try:
            with open(index_html, "r", encoding="utf-8") as f:
                content = f.read()
            s_token = "let VACANCIES_DATA = ["
            s_idx = content.find(s_token)
            if s_idx != -1:
                e_token = "];"
                e_idx = content.find(e_token, s_idx)
                if e_idx != -1:
                    min_json = json.dumps(data, ensure_ascii=False)
                    new_content = content[:s_idx] + f"let VACANCIES_DATA = {min_json};" + content[e_idx + len(e_token):]
                    with open(index_html, "w", encoding="utf-8") as f:
                        f.write(new_content)
        except Exception as e:
            print(f"[AGGREGATOR] Note: index.html fallback update skipped: {e}")

def main():
    print("=" * 70)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Rozgar Multi-Source Aggregator Pipeline Starting...")
    print("=" * 70)

    existing_data = load_existing()
    print(f"[AGGREGATOR] Existing dataset loaded: {len(existing_data)} vacancies.")

    scrapers = [
        ("SarkariResult", scrape_sarkari_result),
        ("FreeJobAlert", scrape_free_job_alert),
        ("ResultBharat", scrape_result_bharat),
        ("SarkariExam", scrape_sarkari_exam),
        ("RojgarResult", scrape_rojgar_result),
        ("JagranJosh", scrape_jagran_josh)
    ]

    all_raw_items = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_source = {executor.submit(func): name for name, func in scrapers}
        for future in as_completed(future_to_source):
            src_name = future_to_source[future]
            try:
                items = future.result()
                print(f"[SOURCE] {src_name}: Extracted {len(items)} items")
                all_raw_items.extend(items)
            except Exception as e:
                print(f"[SOURCE] {src_name} failed: {e}", file=sys.stderr)

    print(f"[AGGREGATOR] Total raw extracted listings across 6 portals: {len(all_raw_items)}")

    # Standardize & build schema objects
    structured_entries = []
    for raw in all_raw_items:
        entry = build_aggregated_entry(raw)
        structured_entries.append(entry)

    # Cross-portal deduplication & merge
    merged_data, added_count, updated_count = deduplicate_and_merge(existing_data, structured_entries)

    atomic_save(merged_data)

    # Category and source breakdown
    sources_count = {}
    categories_count = {}
    quals_count = {}
    for item in merged_data:
        s = item.get("source", "Official")
        for sub_s in s.split(", "):
            sources_count[sub_s] = sources_count.get(sub_s, 0) + 1
        cat = item.get("category", "Latest Jobs")
        categories_count[cat] = categories_count.get(cat, 0) + 1
        q = item.get("qualification", "Other")
        quals_count[q] = quals_count.get(q, 0) + 1

    print("-" * 70)
    print(f"[SUCCESS] Multi-Source Aggregation Completed!")
    print(f" • Total Clean Vacancies in Dataset: {len(merged_data)}")
    print(f" • New Unique Entries Added: {added_count}")
    print(f" • Duplicate Entries Merged/Updated: {updated_count}")
    print(f" • Category Breakdown: {dict(categories_count)}")
    print(f" • Qualification Breakdown: {dict(quals_count)}")
    print(f" • Source Contributions: {dict(sources_count)}")
    print(f" • Saved File Paths: {DATA_FILE} and {ROOT_FILE}")
    print("=" * 70)

if __name__ == "__main__":
    main()
