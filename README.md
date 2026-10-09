# Rozgar — रोज़गार 🇮🇳 

> **A privacy-first, tri-lingual mobile web companion & form studio for Bihar and Central Government Job Aspirants.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Platform](https://img.shields.io/badge/Platform-Mobile%20%7C%20Tablet%20%7C%20Desktop-blue)
![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline%20%7C%20Zero%20Upload-green)
![Languages](https://img.shields.io/badge/Languages-Hindi%20%7C%20English%20%7C%20Hinglish-orange)

---

## 🎯 Overview & Vision

Filling government job application forms (BSSC, BPSC, Bihar Police, SSC GD, Railway RRB, Defence, Coast Guard) often forces students in Tier-2/3 towns to travel to cyber cafés and pay ₹100–₹150 per form just for basic photo resizing, document verification, and eligibility checks.

**Rozgar (रोज़गार)** brings the entire form-filling workbench directly onto the student's mobile phone:
- **100% Client-Side Processing**: Photos, signatures, and document details never leave the user's device.
- **Zero Language Mixing**: Full tri-lingual switch between English, हिन्दी, and Hinglish.
- **Smart Form Preparation**: Accurate dimensions, background replacement, date/name stamping, and precise KB compression.

---

## ✨ Key Features & Modules

### 1. 💼 Active 2026 Vacancy Feed & SarkariResult-Style Hub
- **Categorized Feed**: Toggle between **Latest Jobs**, **Admit Cards**, and **Exam Results**.
- **Compact Accordion Cards**:
  - **Collapsed View**: Exam title, recruiting organization, vacancy count badge, application start & last date, days left countdown timer, and personalized eligibility match pill.
  - **Expanded View**: Educational qualifications, category-wise application fees (UR/EBC/SC/ST/Female), age criteria with cutoff dates, and direct links to official notification portals.
- **5-Stage Application Lifecycle Tracker**:
  - Real-time milestone tracker for: `Application Active` ➔ `Admit Card Release` ➔ `Answer Key Release` ➔ `Result Declaration` ➔ `Scorecard / Cutoff`.
- **Dynamic Required Documents Checklist**:
  - Each job automatically cross-checks required certificates (10th/12th Marksheet, Domicile, Caste/EWS, ID Proof) against the user's local Document Vault.

### 2. 📸 Advanced Photo, Signature & Thumb Resizer Studio
- **3 Specialized Workflows**:
  - **Passport Photo**: Official presets for SSC, Railway RRB, BSSC/BPSC, UPSC, and State PSCs.
  - **Candidate Signature**: Auto-contrast filter converting notebook paper signatures into pure white backgrounds with crisp black/blue ink.
  - **Left Thumb Impression (LTI)**: High-clarity ridge enhancement for biometric uploads.
- **Custom Background Color Picker**: Replace cluttered photo backgrounds with standard official colors (Pure White, Light Sky Blue, Off-White, Studio Grey).
- **Candidate Name & Date Stamp (DOB / DOP)**:
  - Add standard black strip overlays at the bottom of photos with candidate's full name and Date of Photo (DOP) as mandated by SSC/BSSC.
- **Binary Search KB Compressor**:
  - Live target file size slider (e.g., 20 KB – 50 KB, 10 KB – 20 KB).
  - Iterative HTML5 Canvas binary search compression guarantees the downloaded JPEG file falls strictly within the prescribed boundary.

### 3. 🗄️ Local Document Vault & Custom Documents
- Store essential exam credentials locally: Aadhaar, PAN, Matriculation roll numbers, Domicile, Caste/Category Certificate numbers.
- **Add Custom Document**: Create and persist user-defined documents (e.g., Driving License, NCC Certificate, Computer Diploma).
- One-tap copy to clipboard for rapid form filling.

### 4. 🌐 Tri-Lingual Localization (100% Strict Zero-Leak)
- Seamless switching between:
  - **English**: Pure English interface with standard terminology.
  - **हिन्दी (Devanagari)**: High-quality, respectful Devanagari Hindi text.
  - **Hinglish (Roman Hindi)**: Conversational, student-friendly colloquial phrasing.
- Zero string leakage across modals, status badges, accordion drawers, and tooltips.

### 5. 🌓 Adaptive Theme & Mobile Viewport
- **Light Mode**: Crisp, high-contrast clean slate for daylight studying.
- **Dark Mode**: Rich midnight navy/slate (#0B1120 / #1E293B) designed for long night library study sessions.
- **Mobile-First Container**: Centered mobile smartphone frame on laptop/desktop screens with responsive full-width view on mobile devices.

### 6. 📝 Community Discussion & Daily Practice Hub
- Integrated exam discussions and daily practice quiz module with instant scoring.

---

## 🔒 Privacy & Security Architecture

| Security Feature | Implementation |
|---|---|
| **Zero Server Transmission** | Image compression and canvas manipulation run entirely on-device via HTML5 Canvas. |
| **No Third-Party Analytics** | No trackers, advertising SDKs, or external monitoring scripts. |
| **Local Storage Persistence** | Profile and vault data are stored strictly in the user's browser `localStorage`. |
| **Open Source** | Fully auditable and transparent code. |

---

## 🚀 Getting Started

Rozgar is built with **zero external build tools or node dependencies** — pure vanilla HTML5, Tailwind CSS CDN, and modern ES6 JavaScript.

### Option 1: Open Directly
Simply double-click `index.html` to run in any modern web browser.

### Option 2: Run with Local Server
```bash
# Clone the repository
git clone https://github.com/Ashutosh705/Rozgar.git
cd Rozgar

# Run with Python
python -m http.server 8000

# Open in browser
http://localhost:8000
```

### Option 3: Access from Mobile Phone (Same Wi-Fi)
```bash
# Find your computer's local IP address
ipconfig    # Windows
ifconfig    # macOS / Linux

# Open on your phone's browser:
http://192.168.X.X:8000
```

---

## 📁 Repository Structure

```
Rozgar/
├── index.html          # Core Rozgar App (Feed, Studio, Vault, Hub & Tri-lingual UI)
├── vacancies.json      # Active 2026 Recruitment Feed Data
├── eligibility.html    # Navigation redirect helper
├── .gitignore          # Git exclusion rules
└── README.md           # Documentation & Project Guide
```

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

*Made with ❤️ for Government Job Aspirants.*
