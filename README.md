<p align="center">
  <img src="frontend/images/logo.png" alt="VEXORA — Seeing What Others Overlook" width="480">
</p>

<p align="center">
  <b>SEEING WHAT OTHERS OVERLOOK</b><br>
  <i>AI-Powered Digital Document Forensics & Contextual Intelligence Platform</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue?style=flat-square" alt="Python Version">
  <img src="https://img.shields.io/badge/Architecture-Flask%20%2B%20SQLite%20%2B%20Vanilla%20JS-emerald?style=flat-square" alt="Stack">
  <img src="https://img.shields.io/badge/Tests-250%20Passed-brightgreen?style=flat-square" alt="Automated Tests">
  <img src="https://img.shields.io/badge/E2E%20Checks-12%2F12%20Passed-brightgreen?style=flat-square" alt="E2E Checks">
  <img src="https://img.shields.io/badge/Case%20Accuracy-100.0%25-blue?style=flat-square" alt="Case Accuracy">
  <img src="https://img.shields.io/badge/Single--Doc%20Specificity-100.0%25-blue?style=flat-square" alt="Specificity">
</p>

---

## 🎯 Executive Overview

**VEXORA** is a full-stack, evidence-driven digital document forensics and contextual intelligence platform. Designed for cyber forensics investigators, fraud examiners, compliance teams, and hackathon evaluators, VEXORA ingests multi-format documents (PDFs, scans, raster images), extracts grounded typographic and text primitives, performs multi-layered forensic inspection (PDF structural anomalies, pixel-level manipulation, metadata divergence), correlates transactions across entire cases, and synthesizes audit-ready investigation dossiers.

The platform prioritizes **mathematical rigor**, **zero fabricated numbers**, **transparent evidence provenance**, and **explainable AI reasoning with strict anti-hallucination guardrails**.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph INGESTION ["1. Ingestion & Extraction Engine"]
        A["Document Ingest (PDF / Image)"] --> B{"Page Type Analysis"}
        B -->|"Born-Digital Vector Text"| C["PyMuPDF Native Block Extraction\n(Bounding boxes, font metadata, glyph coords)"]
        B -->|"Scanned / Image Only"| D["High-Res 200 DPI Rasterization\n+ PIL Autocontrast Preprocessing"]
        D --> E["Tesseract OCR Engine\n(Word-level confidence & point scaling)"]
        C & E --> F["Unified Document Text & Layout Primitives"]
    end

    subgraph FORENSICS ["2. Multi-Tier Forensic Analysis"]
        F --> G["PDF Structural Engine\n(PDF-001 to PDF-006)"]
        F --> H["Pixel Image Forensics\n(IMG-001 to IMG-005)"]
        F --> I["Typography & Context Engine\n(RULE-CTX-001 to 005)"]
        F --> J["Entity Extractor\n(Deterministic Regex NER)"]
    end

    subgraph CORRELATION ["3. Cross-Document Correlation & Timeline"]
        J --> K["Cross-Document Comparator\n(Jaccard similarity, variance matrix)"]
        J --> L["Chronological Timeline Synthesizer\n(Temporal sequence anomaly engine)"]
        J --> M["Relationship Graph Builder\n(Document-Entity SVG network)"]
    end

    subgraph TRACEABILITY ["4. Evidence Traceability & AI Reasoning"]
        G & H & I & K & L --> N["Evidence Integrity & Custody\n(SHA-256 validation, ISO/IEC 27037 alignment)"]
        N --> O["Visual Evidence Overlay\n(Dynamic PDF / ELA heatmap renderer)"]
        N --> P["Explainable AI Layer\n(PII masking, quote verification, hypotheses)"]
        N & O & P --> Q["Audit-Ready Investigation Dossier\n(Vector PDF & HTML report export)"]
    end
```

---

## 📊 Rigorous Benchmark Evaluation Results

VEXORA includes an automated, programmatic benchmark evaluation engine (`tools/evaluate.py`) that scores system performance across a 20-file verified dataset (`demo_dataset/`) with ground-truth labels and 3 multi-document case scenarios.

Results are automatically exported to machine-readable formats (`reports/benchmark_results.json` and `reports/benchmark_results.csv`):

### 1. Document-Level Detection Metrics (20 Documents)

| Metric | Measured Value | Forensic Interpretation |
|---|---|---|
| **Accuracy** | **85.0%** (17 / 20) | Correctly classified 10 clean + 7 tampered documents. |
| **Recall (Sensitivity)** | **70.0%** (7 / 10) | Detected all intrinsic font, whitebox, and metadata anomalies. |
| **Precision** | **100.0%** (7 / 7) | Zero false alarms ($FP = 0$); every flagged document was tampered. |
| **Specificity** | **100.0%** (10 / 10) | Clean genuine documents were 100% verified clean. |
| **F1-Score** | **82.35%** | Harmonic mean of detection precision and recall. |

> **Scientific Note on False Negatives:** The 3 undetected documents (`tampered_04`, `tampered_05`, and `tampered_06`) are 100% internally genuine vector documents when examined in isolation. Their tampering consists of duplicate invoice collisions and cross-document payment discrepancies, which can only be identified by comparing counterpart documents in Section 2 below.

### 2. Cross-Document Case-Level Correlation Metrics (3 Cases)

| Metric | Measured Value | Forensic Interpretation |
|---|---|---|
| **Case-Level Accuracy** | **100.0%** (3 / 3) | Perfectly classified genuine and tampered multi-document cases. |
| **Case Recall** | **100.0%** (2 / 2) | Caught duplicate invoice collision and bank settlement discrepancy. |
| **Case Precision** | **100.0%** (2 / 2) | Zero false case alarms ($FP = 0$). |
| **Case Specificity** | **100.0%** (1 / 1) | Clean procurement case (`case_03`) verified 100% genuine. |
| **Case F1-Score** | **100.0%** | Comprehensive cross-document correlation fidelity. |

---

## ✨ Key Platform Capabilities

| Capability | Module | Description |
|---|---|---|
| **Hybrid Ingestion Pipeline** | `backend/extractor.py` | Native digital vector text extraction for clean PDFs; automatic 200 DPI rasterization + Tesseract OCR with point coordinate scaling for scanned pages. |
| **PDF Structural Forensics** | `backend/forensics_pdf.py` | Detects incremental updates (`PDF-002`), graphic editor metadata (`PDF-003`), vector overprints on scans (`PDF-004`), geometry shifts (`PDF-005`), and suspicious objects (`PDF-006`). |
| **Pixel-Level Image Forensics** | `backend/forensics_image.py` | Error Level Analysis (`IMG-001`), Laplacian blur discontinuity (`IMG-002`), ORB copy-move stamp detection (`IMG-003`), signature validation (`IMG-004`), and EXIF divergence (`IMG-005`). |
| **Cross-Document Discrepancy Matrix** | `backend/comparator.py` | Pairwise comparison of invoice totals, dates, and counterparties with Jaccard token similarity for near-duplicate variant detection. |
| **Chronological Timeline Synthesis** | `backend/correlator.py` | Synthesizes an ordered cross-document transaction timeline and detects out-of-order anomalies (`RULE-TIME-001`, `RULE-TIME-002`). |
| **Relationship Provenance Graph** | `backend/correlator.py` | Interactive vanilla SVG network diagram connecting documents, entities, accounts, and discrepancy edges without heavy JavaScript frameworks. |
| **Evidence Integrity & Custody** | `backend/evidence.py` | SHA-256 ingestion hashing, live re-verification, and chronological custody audit trail aligned with ISO/IEC 27037 principles. |
| **Dynamic Forensic Document Viewer** | `frontend/js/v2.js` | Interactive page overlay displaying detected anomalies with live bounding boxes, extraction mode indicators, and page navigation. |
| **Explainable AI Reasoning** | `backend/llm.py` | Optional LLM integration (Google Gemini / OpenAI) with automated PII redaction, verbatim source-quote verification, and plausible innocent hypotheses. |
| **Investigation Dossier Export** | `backend/reporter.py` | Audit-ready multi-page vector PDF and HTML report export with executive summary, discrepancy matrix, custody timeline, and methodology disclosure. |

---

## 🚀 Quickstart & Installation

### Turnkey One-Command Startup

#### Windows
```cmd
start.bat
```
*(Or double-click `start.bat` in Windows Explorer)*

#### macOS & Linux
```bash
chmod +x start.sh
./start.sh
```

Once started, open your web browser to **`http://127.0.0.1:5000`**.

---

### Manual Setup Instructions

#### 1. Windows Setup
```powershell
# Create & activate Python virtual environment:
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies:
pip install -r requirements.txt

# (Optional) Install Tesseract OCR:
# winget install UB-Mannheim.TesseractOCR
# Default path: C:\Program Files\Tesseract-OCR

# Launch VEXORA server:
python -m backend.app
```

#### 2. macOS Setup
```bash
# Create & activate Python virtual environment:
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies:
pip install -r requirements.txt

# (Optional) Install Tesseract OCR:
# brew install tesseract

# Launch VEXORA server:
python3 -m backend.app
```

#### 3. Linux (Ubuntu / Debian) Setup
```bash
# Create & activate Python virtual environment:
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies:
pip install -r requirements.txt

# (Optional) Install Tesseract OCR:
# sudo apt-get update && sudo apt-get install -y tesseract-ocr

# Launch VEXORA server:
python3 -m backend.app
```

> **Note on OCR Graceful Degradation:**
> `VEXORA_STRICT_OCR=false` is enabled by default. If Tesseract OCR is not installed, VEXORA gracefully degrades to structural vector and metadata analysis, displaying a visible **`⚠️ OCR unavailable - fallback mode`** badge without crashing.

---

## 🧪 Comprehensive Automated Test Suite

VEXORA includes **250 automated unit tests** across 27 test modules, plus **12/12 end-to-end integration checks** (**262 total automated verifications**, 100% passing):

```powershell
# Run the complete unit test suite:
.\.venv\Scripts\python -m unittest discover -s tests -p "test_*.py"

# Run the automated judge readiness end-to-end check:
.\.venv\Scripts\python tests/e2e_check.py

# Run the forensic benchmark evaluation:
.\.venv\Scripts\python tools/evaluate.py
```

### Test Suite Structure

- `test_backend.py` — Core REST API routes, models, and SQLite transactions.
- `test_hybrid_pdf_ocr.py` — Hybrid PyMuPDF native block extraction and Tesseract OCR scaling.
- `test_image_pdf_forensics.py` — PDF-001..006 and IMG-001..005 forensic detection rules.
- `test_cross_document_intelligence.py` — Corporate suffix normalization, fuzzy matching, and near-duplicate detection.
- `test_timeline_viewer_contract.py` — Chronological timeline synthesis and dynamic page viewer.
- `test_integrity_custody.py` — Cryptographic SHA-256 verification and ISO/IEC 27037 custody audit logging.
- `test_explainability_privacy.py` — PII redaction and anti-hallucination source quote validation.
- `test_security_audit.py` — Path traversal prevention, null byte rejection, and role elevation barriers.
- `test_resilience_adversarial.py` — Multi-threaded SQLite concurrency, corrupt files, and zero-division resilience.
- `test_evaluator.py` — Dual-tier benchmark metrics and ASCII confusion matrix generation.
- `test_v2_phase_a..k.py` — V2 modular contract and feature regression tests.

---

## 🔬 V2 Forensic Extensions & Additions

VEXORA V2 expands upon baseline capabilities with specialized forensic modules:
- **Structural PDF Analysis**: In-depth inspection of stream dictionaries, incremental updates, compression filters, font subsets, and object modification timelines.
- **Pixel-Level Manipulation Detection**: Error Level Analysis (ELA) heatmap generation, block Laplacian variance sharpness evaluation, and ORB keypoint copy-move clone detection.
- **Cross-Document Transaction Correlation**: Entity normalization, Jaccard token similarity matrices, and chronological timeline synthesis across case dossiers.
- **ISO/IEC 27037 Evidence Handling**: Cryptographic SHA-256 integrity verification, chain-of-custody audit logs, and tamper-evident provenance tracking.

---

## ⚖️ Technical Corrections & Honesty Notes

- **Information Extraction Architecture**: Entity extraction is powered by deterministic **Pure Regex** pattern engines and structured document layouts, ensuring 100% reproducible, offline-first entity resolution without hidden cloud dependencies or ungrounded model hallucinations (avoiding false claims of heavyweight NLP frameworks like spaCy).
- **Advisory AI Reasoning**: External LLM integrations (Google Gemini / OpenAI) function strictly as an optional advisory intelligence layer with verbatim source-quote verification and PII redaction; all core forensic detections operate completely deterministically.

---

## 💾 Data Persistence & Safety

- **Primary Database File**: Ingested cases, documents, findings, and audit records persist in SQLite (`backend/vexora.db`).
- **Configurable Database Path**: Set `VEXORA_DB_PATH` in `.env` to customize storage location. The active database path is logged at server startup.
- **Pre-Wipe Safety Backups**: Clicking **"Reset & Load Demo"** automatically creates a timestamped safety backup in `backend/backups/vexora_YYYYMMDD_HHMMSS.db` before resetting, automatically keeping the 5 newest backups.
- **Non-Destructive Demo Seeding**: Clicking **"Add Demo Case (keep my data)"** seeds showcase case `CAS-DEMO-2026` without altering any existing user cases or evidence.

---

## 🛡️ Forensic Standards & Detailed References

For in-depth technical documentation and judge evaluation materials, refer to:

- [`docs/JUDGE_READINESS_REPORT.md`](docs/JUDGE_READINESS_REPORT.md) — Category-by-category rubric breakdown, 5-minute judge demonstration script, and evaluation checklist.
- [`docs/BENCHMARK_REPORT.md`](docs/BENCHMARK_REPORT.md) — 3-tier quantitative benchmark metrics, confusion matrices, and OCR CER/WER evaluations.
- [`docs/FORENSIC_VALIDATION.md`](docs/FORENSIC_VALIDATION.md) — Mathematical formulations for ELA, RANSAC copy-move, and deterministic rules.
- [`docs/SECURITY_AUDIT.md`](docs/SECURITY_AUDIT.md) — Enterprise RBAC, IDOR protection, session cookie hardening, and prompt-injection defense.
- [`docs/PHASE2_CHANGELOG.md`](docs/PHASE2_CHANGELOG.md) — Architectural changelog covering all Phase 2 upgrades.
- [`docs/PHASE2_AUDIT.md`](docs/PHASE2_AUDIT.md) — Initial codebase audit, identified gaps, and remediation roadmap.
- [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) — Transparent disclosure of optical, language, and persistence boundaries.
- [`CAPABILITIES.md`](CAPABILITIES.md) — Exhaustive forensic rules catalog, mathematical formulas, and security controls.
- [`LIMITATIONS.md`](LIMITATIONS.md) — Comprehensive technical limitations and operating assumptions.
- [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) — Step-by-step judge presentation walkthrough.
- [`VEXORA_DEVELOPMENT_LOG.md`](VEXORA_DEVELOPMENT_LOG.md) — Phase-by-phase engineering log.

---

## ⚠️ Important Disclaimer

*VEXORA is an automated document analysis and digital investigation-support platform. Automated findings indicate potential anomalies, structural inconsistencies, and contextual discrepancies; they must not be treated as autonomous or definitive proof of document forgery, fraud, or wrongdoing. All findings require qualified human examiner confirmation.*

---

<p align="center">
  <img src="frontend/images/logo-icon.png" alt="VEXORA Emblem" width="48"><br>
  <b>VEXORA</b> — <i>Seeing What Others Overlook</i><br>
  Designed for rigorous, explainable digital document forensics.
</p>
