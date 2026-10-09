# Rozgar — रोज़गार 🇮🇳

> **All-India Smart Exam Eligibility Tracker & Mobile Document Prep Companion**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Platform](https://img.shields.io/badge/Platform-Mobile%20%7C%20Tablet%20%7C%20Desktop-blue)
![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline%20%7C%20Zero%20Upload-green)
![Coverage](https://img.shields.io/badge/Coverage-All--India%20%2B%20State%20Exams-orange)
![Auto Sync](https://img.shields.io/badge/Sync-GitHub%20Actions%20Cron-purple)

---

## 🎯 Purpose & Real Value Proposition

Government job application forms (SSC, Railway RRB, UPSC, State PSCs, Police, Defence) must **always be submitted on official government portals**. There are no shortcuts or third-party gateways for direct form submission.

However, millions of aspirants across India encounter two major bottlenecks when applying on mobile devices:

1. **Strict Photo & Document Specifications**: Portals mandate exact pixel dimensions (e.g. 350×450px, 250×100px), precise file size windows (20KB–50KB, 10KB–20KB), pure white backgrounds, and Date of Photo (DOP) / Name stamps. Unofficial online compressors often compromise privacy by uploading sensitive identity photos to third-party cloud servers.
2. **Dense 50+ Page Official Notifications**: Aspirants often spend hours decoding eligibility criteria, cutoff dates, category relaxations, and domicile quotas.

**Rozgar** serves as an on-device preparation workbench:
- **Instant Eligibility Calculation**: Evaluates candidate age (Years · Months · Days) against exact cutoff dates, category reservation matrices, and qualifications in real-time.
- **Client-Side Photo & Signature Studio**: Center-crop, contrast enhancement, background replacement, name/date stamps, and iterative binary search KB compression — 100% inside your browser with zero cloud uploads.
- **Local Document Vault**: Stores roll numbers, registration IDs, and certificate numbers for 1-tap clipboard copying while filling forms in mobile browsers.

---

## ✨ Features & Architecture

### 1. 🇮🇳 All-India & State-Specific Coverage
- **State / Domicile Selector**: Candidate profile supports selection across all states (All-India, Bihar, Uttar Pradesh, Jharkhand, Madhya Pradesh, Rajasthan, Delhi, Haryana, Odisha, West Bengal, etc.).
- **Smart Scope Tagging**:
  - **Central / All-India Exams**: Visible to all aspirants nationwide with central reservation quotas.
  - **State-Level Exams**: Automatically filtered according to candidate domicile. Non-resident aspirants are transparently evaluated under General / Unreserved (UR) criteria per official state service commission rules.
- **Accordion Preview Cards**: Clean collapsed cards displaying essentials (Title, Org, Scope badge, Vacancies, Start & Last Apply Date, Days Left countdown, and Match Chip) that smoothly expand to show qualifications, category fees, and syllabus cutoff dates.
- **5-Stage Application Lifecycle**: Live milestone tracking:
  $$\text{Application Window} \longrightarrow \text{Admit Card} \longrightarrow \text{Exam Date} \longrightarrow \text{Answer Key} \longrightarrow \text{Final Result}$$

### 2. 📸 Advanced Photo, Signature & Thumb Studio
- **3 Dedicated Workflows**:
  - **Passport Photo**: Official presets for SSC, Railway RRB, UPSC, State PSCs, and Defence.
  - **Signature**: Real-time canvas filter converting notebook lined paper into crisp white background with bold black/blue ink.
  - **Left Thumb Impression (LTI)**: Ridge contrast enhancement for biometric uploads.
- **Custom Background Color Replacement**: Pure White, Studio Sky Blue, Off-White, and Light Grey.
- **Name & Date of Photo (DOP) Stamp**: Standard black band with candidate name and photo date mandated by SSC/BSSC.
- **Iterative Binary Search Compressor**: Guarantees the exported JPEG falls strictly within target file boundaries (e.g. 20–50 KB) without quality distortion.

### 3. 🌐 Strict Zero-Leak Tri-Lingual Localization
- 100% strict language separation across:
  - **English**: Pure English terminology and clean placeholders (`Age: 22`, `e.g. Rahul Kumar`).
  - **हिन्दी (Devanagari)**: High-quality Hindi without awkward mixed English (`उम्र: 22`, `उदा. राहुल कुमार`).
  - **Hinglish (Roman Hindi)**: Natural, conversational phrasing (`Umar: 22`, `jaise Rahul Kumar`).
- All input placeholders, modal dialogs, status badges, and profile pills react instantly without string leakage.

### 4. 🔄 Free & Zero-Cost Auto-Sync (GitHub Actions + Python)
- **Problem**: Static hosting on GitHub Pages cannot make direct scraping requests to external portals due to browser CORS policies.
- **Solution**:
  - `scraper.py`: A Python automation script that parses public exam feeds, validates schemas, and updates `vacancies.json`.
  - `.github/workflows/sync-jobs.yml`: A scheduled GitHub Actions workflow running every 6 hours (`0 */6 * * *`) that executes the scraper, checks for changes, and commits updates directly to the repository.
  - The live web application automatically reflects new vacancies and results on reload with zero hosting bills.

---

## 🔒 Privacy & Device Sandbox

| Principle | Implementation |
|---|---|
| **Zero Server Transmission** | All image processing runs via HTML5 Canvas API — files never leave the device |
| **Local Storage Only** | Candidate profile and vault details persist in `localStorage` |
| **No Third-Party Trackers** | Zero analytics SDKs, advertising scripts, or fingerprinting cookies |
| **Auditable Open Source** | 100% client-side code visible in repository |

---

## 🚀 Running Locally

Rozgar is a zero-build application that runs directly in any browser:

```bash
# Clone the repository
git clone https://github.com/Ashutosh705/Rozgar.git
cd Rozgar

# Option A: Run lightweight Python server
python -m http.server 8000

# Option B: Run the scraper manually
python scraper.py
```

Open `http://localhost:8000` in your web browser.

---

## 📁 Repository Structure

```
Rozgar/
├── .github/
│   └── workflows/
│       └── sync_jobs.yml        # GitHub Actions cron workflow (every 6 hours)
├── data/
│   └── vacancies.json           # Central normalized JSON vacancy feed
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py          # Base scraper with HTTP, SSL, retries & schema normalizer
│   ├── ssc_scraper.py           # SSC Board scraper (CGL, CHSL, GD, MTS, CPO)
│   ├── upsc_scraper.py          # UPSC Portal scraper (Civil Services, NDA, CDS)
│   ├── rrb_scraper.py           # Railway RRB scraper (NTPC, ALP, Tech, RPF)
│   ├── ibps_scraper.py          # Banking & IBPS scraper (PO, Clerk, SO, RRB)
│   └── state_psc_scraper.py     # State PSCs & Police scraper (BPSC, UPPSC, DSSSB, etc.)
├── scripts/
│   └── fetch_all.py             # Master orchestrator & deduplication engine
├── fetch_all.py                 # Root CLI runner delegating to scripts/fetch_all.py
├── requirements.txt             # Pipeline Python dependencies
├── index.html                   # Main Web Application (Studio, Vault, Hub, i18n, Feed)
├── vacancies.json               # Root alias dataset (synced with data/vacancies.json)
├── eligibility.html             # Route redirect helper
├── .gitignore                   # Staging exclusions
└── README.md                    # Project documentation & architecture guide
```

---

## 📜 License

Licensed under the MIT License — free for students and developers.
