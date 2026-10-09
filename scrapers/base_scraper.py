# -*- coding: utf-8 -*-
"""
Rozgar Base Scraper Module
Provides shared HTTP requests, SSL bypass for legacy gov portals,
schema normalization, date parsing, and robust error handling.
"""

import re
import sys
import json
import ssl
import time
import urllib.request
from datetime import datetime, timedelta

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
]

class BaseScraper:
    def __init__(self, name="BaseScraper", default_scope="Central", default_state="All-India"):
        self.name = name
        self.default_scope = default_scope
        self.default_state = default_state

    def get_headers(self):
        return {
            "User-Agent": USER_AGENTS[0],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }

    def fetch_text(self, url, timeout=12, max_retries=2):
        """Fetch raw HTML or JSON text with SSL tolerance and retries."""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        for attempt in range(max_retries):
            try:
                headers = self.get_headers()
                headers["User-Agent"] = USER_AGENTS[attempt % len(USER_AGENTS)]
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                    if resp.status == 200:
                        content = resp.read()
                        # Try decoding utf-8, fallback to latin-1
                        try:
                            return content.decode("utf-8")
                        except UnicodeDecodeError:
                            return content.decode("latin-1", errors="ignore")
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"[{self.name}] [WARN] Fetch failed for {url}: {e}", file=sys.stderr)
                time.sleep(1)
        return None

    def fetch_soup(self, url, timeout=12):
        """Fetch and return BeautifulSoup object."""
        html = self.fetch_text(url, timeout=timeout)
        if html and BeautifulSoup:
            return BeautifulSoup(html, "html.parser")
        return None

    def slugify(self, text):
        """Generate a clean unique persistent identifier."""
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', text.upper()).strip('_')
        return slug[:45]

    def infer_category(self, text, url=""):
        """Categorize into 'jobs', 'admit-card', 'results', or 'schemes-admissions'."""
        combined = f"{text} {url}".lower()
        if any(k in combined for k in ["admit", "hall ticket", "call letter", "e-admit", "admission card"]):
            return "admit-card"
        if any(k in combined for k in ["result", "final marks", "scorecard", "merit list", "answer key", "ans key", "cut-off"]):
            return "results"
        if any(k in combined for k in ["scholarship", "admission", "yojana", "counseling"]):
            return "schemes-admissions"
        return "jobs"

    def infer_qualification(self, text):
        """Determine required educational tier."""
        t = text.upper()
        if any(k in t for k in ["10TH", "MATRIC", "HIGH SCHOOL", "MTS", "GROUP D", "DRIVER", "TRADESMAN"]):
            return "10TH", "10th Standard (Matriculation)", "10वीं कक्षा (मैट्रिक) उत्तीर्ण", "10th"
        if any(k in t for k in ["ITI", "APPRENTICE", "TRADE CERTIFICATE"]):
            return "ITI", "10th Pass with ITI Certificate", "10वीं पास एवं संबंधित ट्रेड में ITI", "10th"
        if any(k in t for k in ["12TH", "INTERMEDIATE", "10+2", "CHSL", "CONSTABLE", "NAVIK", "NDA"]):
            return "12TH", "12th Standard (Intermediate)", "12वीं कक्षा (इंटरमीडिएट) उत्तीर्ण", "12th"
        if any(k in t for k in ["POST GRADUATE", "PG", "MASTER", "MD", "M.SC", "M.TECH"]):
            return "PG", "Master's Degree in Relevant Discipline", "संबंधित विषय में स्नातकोत्तर (पीजी)", "graduate"
        return "GRADUATE", "Bachelor's Degree in Any Stream", "किसी भी विषय में स्नातक डिग्री उत्तीर्ण", "graduate"

    def infer_scope_and_state(self, text, org=""):
        """Determine Central vs State scope and specific state."""
        combined = f"{text} {org}".upper()
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
        return self.default_scope, self.default_state, (self.default_scope == "Central")

    def build_standard_schema(self, raw):
        """
        Normalize raw parsed dictionary into the standard Rozgar schema,
        supporting both snake_case and camelCase for 100% full compatibility.
        """
        title = raw.get("title", "").strip()
        org = raw.get("organization") or raw.get("org") or self.name
        scope, state, is_central = self.infer_scope_and_state(title, org)
        cat = raw.get("category") or self.infer_category(title, raw.get("apply_link", ""))
        qual_code, qual_en, qual_hi, cat_tag = self.infer_qualification(title)

        today = datetime.now()
        start_date = raw.get("start_date") or raw.get("startDate") or (today - timedelta(days=7)).strftime("%Y-%m-%d")
        last_date = raw.get("last_date") or raw.get("lastDate") or (today + timedelta(days=21)).strftime("%Y-%m-%d")
        cutoff_date = raw.get("cutoff_date") or raw.get("cutoffDate") or f"{today.year}-07-01"

        status = raw.get("status")
        if not status:
            if cat == "results":
                status = "Declared"
            elif cat == "admit-card":
                status = "Available"
            else:
                try:
                    status = "Closed" if datetime.strptime(last_date, "%Y-%m-%d") < today else "Active"
                except Exception:
                    status = "Active"

        item_id = raw.get("id") or (self.slugify(f"{org}_{title}") + f"_{today.year}")

        # Construct unified object
        return {
            # Core identification
            "id": item_id,
            "title": title,
            "title_hi": raw.get("title_hi") or title,
            "title_hinglish": raw.get("title_hinglish") or title,
            "organization": org,
            "org": org,
            "org_hi": raw.get("org_hi") or org,
            "org_hinglish": raw.get("org_hinglish") or org,

            # Categorization & Scope
            "category": cat,
            "scope": scope,
            "state": state,
            "isCentral": is_central,
            "qualification": qual_code,
            "minEducation": qual_code,
            "minEduLabel": qual_en,
            "minEduLabel_hi": qual_hi,
            "minEduLabel_hinglish": qual_en,
            "categoryTag": cat_tag,

            # Posts and Vacancies
            "posts_count": raw.get("posts_count") or raw.get("vacancies") or "Various Posts",
            "vacancies": raw.get("vacancies") or raw.get("posts_count") or "Various Posts",
            "vacancies_hi": raw.get("vacancies_hi") or "विभिन्न पद",
            "vacancies_hinglish": raw.get("vacancies_hinglish") or "Various Posts",

            # Dates
            "start_date": start_date,
            "startDate": start_date,
            "last_date": last_date,
            "lastDate": last_date,
            "cutoff_date": cutoff_date,
            "cutoffDate": cutoff_date,

            # URLs
            "apply_link": raw.get("apply_link") or raw.get("officialApplyUrl") or "#",
            "officialApplyUrl": raw.get("officialApplyUrl") or raw.get("apply_link") or "#",
            "notification_pdf": raw.get("notification_pdf") or "",
            "admit_card_link": raw.get("admit_card_link") or "",
            "result_link": raw.get("result_link") or "",
            "status": status,

            # Fees & Age
            "fee": raw.get("fee") or "₹100–₹500 (As per rules)",
            "fee_hi": raw.get("fee_hi") or "₹100–₹500 (नियमानुसार)",
            "fee_hinglish": raw.get("fee_hinglish") or "₹100–₹500 (Rules ke hisaab se)",
            "min_age": raw.get("min_age") or raw.get("minAge") or 18,
            "minAge": raw.get("minAge") or raw.get("min_age") or 18,
            "max_age": raw.get("max_age") or raw.get("maxAge") or {
                "GENERAL_MALE": 30 if qual_code == "10TH" else 35,
                "GENERAL_FEMALE": 30 if qual_code == "10TH" else 35,
                "EWS_MALE": 30 if qual_code == "10TH" else 35,
                "EWS_FEMALE": 30 if qual_code == "10TH" else 35,
                "BC_OBC2_MALE": 33 if qual_code == "10TH" else 38,
                "BC_OBC2_FEMALE": 33 if qual_code == "10TH" else 38,
                "EBC_OBC1_MALE": 33 if qual_code == "10TH" else 38,
                "EBC_OBC1_FEMALE": 33 if qual_code == "10TH" else 38,
                "SC_MALE": 35 if qual_code == "10TH" else 40,
                "SC_FEMALE": 35 if qual_code == "10TH" else 40,
                "ST_MALE": 35 if qual_code == "10TH" else 40,
                "ST_FEMALE": 35 if qual_code == "10TH" else 40
            },
            "maxAge": raw.get("maxAge") or raw.get("max_age") or {
                "GENERAL_MALE": 30 if qual_code == "10TH" else 35,
                "GENERAL_FEMALE": 30 if qual_code == "10TH" else 35,
                "EWS_MALE": 30 if qual_code == "10TH" else 35,
                "EWS_FEMALE": 30 if qual_code == "10TH" else 35,
                "BC_OBC2_MALE": 33 if qual_code == "10TH" else 38,
                "BC_OBC2_FEMALE": 33 if qual_code == "10TH" else 38,
                "EBC_OBC1_MALE": 33 if qual_code == "10TH" else 38,
                "EBC_OBC1_FEMALE": 33 if qual_code == "10TH" else 38,
                "SC_MALE": 35 if qual_code == "10TH" else 40,
                "SC_FEMALE": 35 if qual_code == "10TH" else 40,
                "ST_MALE": 35 if qual_code == "10TH" else 40,
                "ST_FEMALE": 35 if qual_code == "10TH" else 40
            },
            "preset_key": raw.get("preset_key") or raw.get("presetKey") or "GEN_PHOTO",
            "presetKey": raw.get("presetKey") or raw.get("preset_key") or "GEN_PHOTO",

            # Checklists & Lifecycles
            "required_docs": raw.get("required_docs") or raw.get("requiredDocs") or [
                {"key": "m10", "name": "10th Marksheet", "name_hi": "10वीं अंकतालिका", "name_hinglish": "10th Marksheet", "mandatory": True},
                {"key": "id", "name": "Aadhaar Card", "name_hi": "आधार कार्ड", "name_hinglish": "Aadhaar Card", "mandatory": True},
                {"key": "dom", "name": f"{state} Domicile" if state != "All-India" else "Domicile Certificate", "name_hi": "निवास प्रमाण पत्र", "name_hinglish": "Domicile", "mandatory": True}
            ],
            "requiredDocs": raw.get("requiredDocs") or raw.get("required_docs") or [
                {"key": "m10", "name": "10th Marksheet", "name_hi": "10वीं अंकतालिका", "name_hinglish": "10th Marksheet", "mandatory": True},
                {"key": "id", "name": "Aadhaar Card", "name_hi": "आधार कार्ड", "name_hinglish": "Aadhaar Card", "mandatory": True},
                {"key": "dom", "name": f"{state} Domicile" if state != "All-India" else "Domicile Certificate", "name_hi": "निवास प्रमाण पत्र", "name_hinglish": "Domicile", "mandatory": True}
            ],
            "lifecycle": raw.get("lifecycle") or [
                {"stage": "apply", "status": "active" if cat == "jobs" else "completed", "titleEn": "Application Window", "titleHi": "आवेदन प्रक्रिया", "titleHinglish": "Application Window", "dateEn": "Active" if cat == "jobs" else "Closed", "dateHi": "सक्रिय" if cat == "jobs" else "सम्पन्न", "dateHinglish": "Active" if cat == "jobs" else "Closed"},
                {"stage": "admit", "status": "active" if cat == "admit-card" else ("upcoming" if cat == "jobs" else "completed"), "titleEn": "Admit Card", "titleHi": "प्रवेश पत्र", "titleHinglish": "Admit Card", "dateEn": "Available Now" if cat == "admit-card" else "Upcoming", "dateHi": "उपलब्ध" if cat == "admit-card" else "आगामी", "dateHinglish": "Available Now" if cat == "admit-card" else "Upcoming"},
                {"stage": "exam", "status": "upcoming" if cat != "results" else "completed", "titleEn": "Exam Date", "titleHi": "परीक्षा तिथि", "titleHinglish": "Exam Date", "dateEn": "Check Notice", "dateHi": "विज्ञप्ति देखें", "dateHinglish": "Check Notice"},
                {"stage": "anskey", "status": "pending" if cat != "results" else "completed", "titleEn": "Answer Key", "titleHi": "उत्तर कुंजी", "titleHinglish": "Answer Key", "dateEn": "Pending", "dateHi": "प्रतीक्षित", "dateHinglish": "Pending"},
                {"stage": "result", "status": "active" if cat == "results" else "pending", "titleEn": "Result / Cutoff", "titleHi": "अंतिम परिणाम", "titleHinglish": "Final Result", "dateEn": "Declared" if cat == "results" else "Pending", "dateHi": "घोषित" if cat == "results" else "प्रतीक्षित", "dateHinglish": "Declared" if cat == "results" else "Pending"}
            ]
        }
