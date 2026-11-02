<p align="center">
  <img src="frontend/images/logo.png" alt="VEXORA — Seeing What Others Overlook" width="480">
</p>

<p align="center">
  <b>SEEING WHAT OTHERS OVERLOOK</b><br>
  <i>AI-Powered Document Forensics & Contextual Intelligence System</i>
</p>

VEXORA is an AI-powered document analysis and forensic investigation platform designed to help users examine digital documents, extract meaningful information, identify potential inconsistencies, and connect findings across multiple documents.

The system combines document processing, OCR, entity extraction, contextual analysis, and evidence mapping into one centralized investigation workspace.

---

## 🎯 Project Overview

Investigating multiple documents manually can be time-consuming, especially when information is scattered across different files.

VEXORA aims to simplify this process by providing a structured environment where users can upload documents, extract information, examine potential anomalies, compare records, and generate investigation reports.

The platform focuses on making document analysis more organized, explainable, and traceable.

## ✨ Key Features

The following features represent the planned project scope. Their implementation status will be updated as development progresses.

| Feature | Description | Status |
|---|---|---|
| Investigation Dashboard | Centralized overview of investigation activities. | Completed (UI) |
| Case Management | Create and manage investigation cases. | Completed (UI) |
| Document Upload | Upload PDF, JPG and PNG documents. | Completed (UI) |
| Document Library | Organize and access uploaded documents. | Completed (UI) |
| OCR Processing | Extract text from scanned documents and images. | Completed (Phase 5) |
| Information Extraction | Identify names, dates and organizations. | Completed (Phase 5) |
| Document Analysis | Examine unusual formatting and contextual inconsistencies. | Completed (Phase 6) |
| Cross-Document Comparison | Compare information across multiple documents. | Completed (Phase 7) |
| Evidence Mapping | Connect findings to their original documents and pages. | Completed (Phase 7) |
| Investigation Dossier | Generate structured investigation reports. | Completed (Phase 8) |
| Audit Trail | Maintain records of important investigation activities, export logs to CSV/JSON, and run diagnostic self-tests. | Completed (Phase 9) |

## ⚙️ Technology Stack

VEXORA uses a beginner-friendly technology stack.

### Frontend
- **HTML5** – Structures the application pages.
- **CSS3** – Handles styling, layouts and responsiveness.
- **JavaScript** – Provides interactive functionality.

### Backend
- **Python** – Implements document processing and analysis.
- **Flask** – Connects frontend requests with backend functionality.
- **SQLite** – Stores investigation records and application data.

### Document Processing & Analysis
- **PyMuPDF (`pymupdf`)** – Extracts text, character glyph coordinates, font matrices, and renders page bitmaps from PDF documents.
- **Tesseract OCR (`pytesseract`)** – Recognizes text from scanned documents with word-level confidence extraction.
- **Pure Regex & Deterministic NER (`backend/ner.py`)** – Identifies entities (identifiers, dates, monetary values, organizations, tax IDs) without heavy external NLP runtime dependencies.

### Development Tools
- **Visual Studio Code / Antigravity** – Development environment.
- **Git & GitHub** – Version control and project management.

## 🔍 How VEXORA Works

The investigation workflow:

1. **Create an Investigation:** Start a new case and organize its details.
2. **Upload Documents:** Add PDF files and supported images.
3. **Extract Information:** Process documents using text extraction and OCR.
4. **Identify Entities:** Extract relevant names, dates and organizations.
5. **Analyze Documents:** Examine potential formatting and contextual inconsistencies.
6. **Compare Documents:** Identify matching, repeated and conflicting information.
7. **Map Evidence:** Connect findings with their original document pages.
8. **Generate Reports:** Create an investigation dossier containing findings and supporting evidence.
9. **Audit & Diagnostics:** Maintain full evidentiary audit logs with CSV/JSON exports and diagnostic health checks.

## 🗺️ Development Roadmap

VEXORA has been systematically developed and verified through nine structured phases.

| Phase | Development Area | Status |
|---|---|---|
| 01 | Project Setup & UI Foundation | **Completed** |
| 02 | Core Pages & User Interface | **Completed** |
| 03 | Backend & Database Integration | **Completed** |
| 04 | Document Upload & Classification | **Completed** |
| 05 | OCR & Information Extraction | **Completed** |
| 06 | Forensic & Contextual Analysis | **Completed** |
| 07 | Cross-Document Comparison & Evidence Mapping | **Completed** |
| 08 | Investigation Dossier & Report Generation | **Completed** |
| 09 | Audit Trail, Testing & Finalization | **Completed** |

Each phase includes implementation, testing, documentation and a beginner-friendly learning report.

See [`VEXORA_DEVELOPMENT_ROADMAP.md`](VEXORA_DEVELOPMENT_ROADMAP.md) for the complete development instructions.

See [`VEXORA_DEVELOPMENT_LOG.md`](VEXORA_DEVELOPMENT_LOG.md) for phase progress and implementation records.

## 📁 Implemented Project Structure

```text
VEXORA/
│
├── frontend/
│   ├── index.html
│   ├── pages/
│   │   ├── cases.html
│   │   ├── upload.html
│   │   ├── library.html
│   │   ├── analysis.html
│   │   ├── comparison.html
│   │   ├── report.html
│   │   └── settings.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
│
├── backend/
│   ├── analyzer.py
│   ├── app.py
│   ├── comparator.py
│   ├── config.py
│   ├── database.py
│   ├── extractor.py
│   ├── models.py
│   ├── ner.py
│   ├── reporter.py
│   ├── schema.sql
│   └── vexora.db
│
├── uploads/
│   └── .gitkeep
│
├── reports/
│   └── .gitkeep
│
├── tests/
│   └── test_backend.py
│
├── requirements.txt
├── README.md
├── VEXORA_DEVELOPMENT_ROADMAP.md
└── VEXORA_DEVELOPMENT_LOG.md
```

## 🚀 How to Run VEXORA

### Prerequisites

- Python 3.10+
- A modern web browser

### Running with Flask & SQLite (Full-Stack Mode)

To run the complete application with SQLite persistence and REST API endpoints:

```bash
# 1. Activate the dedicated virtual environment:
.\.venv\Scripts\activate

# 2. Start the Flask application server:
python backend/app.py

# 3. Open in your web browser:
http://127.0.0.1:5000
```

### Running Automated Test Suite

To run the automated backend test suite (isolated SQLite test database):

```bash
.\.venv\Scripts\python -m unittest tests/test_backend.py
```

## 🧪 Testing

The comprehensive automated test suite covers:

- Frontend navigation, interactive UI components, and theme switching.
- Backend REST API routes and SQLite database transactions.
- Secure document uploads, extension validation, SHA-256 cryptographic integrity hashing, and metadata tracking.
- PyMuPDF digital text extraction, bounding-box layout parsing, and OCR fallback.
- Named entity recognition (names, dates, financial sums, organizations).
- Forensic heuristics (unusual dates, round amounts, duplicate references, layout anomalies).
- Multi-document comparison (pairwise cross-checking, discrepancies, matching anchors).
- Case dossier & PDF report generation with visual integrity scoring.
- Audit trail logging with parameterized filtering, RFC 4180 CSV / JSON exports, and system diagnostics self-test.
- Complete end-to-end investigation lifecycle verification.

All 114 automated tests execute cleanly against isolated test databases:

```bash
.\.venv\Scripts\python -m unittest tests/test_backend.py tests/test_v2_contract.py tests/test_v2_phase_a.py tests/test_v2_phase_b.py tests/test_v2_phase_c.py tests/test_v2_phase_d.py tests/test_v2_phase_e.py tests/test_v2_phase_f.py
```

## ⚡ V2 Forensic Extensions & Additions

The platform has been significantly deepened through seven additive phases (Phases A through G), introducing advanced forensic capabilities:

- **Phase A — Visual Evidence Overlays:** Interactive modal viewer highlighting physical document bounding boxes in red via `/api/findings/<id>/evidence-image` with 2D zoom/pan controls.
- **Phase B — Deeper PDF Forensics:** Extends analysis beyond OCR with rules `PDF-001` through `PDF-005` (incremental update / timestamp divergence, embedded font subset anomalies, editing software metadata signatures like Photoshop/GIMP, optional content hidden layers `/OCProperties`, and multi-source page geometry variance). Findings are classified into `Observation`, `Inconsistency`, and `Potential Manipulation`.
- **Phase C — Grounded AI Reasoning Layer:** Pure HTTPS LLM integration (`backend/llm.py`) supporting Google Gemini, Anthropic Claude, and OpenAI. Built with mandatory anti-hallucination source quote verification (claims failing verbatim substring checks are dropped) and automated PII redaction.
- **Phase D — Image Forensics for Scans & Photos:** Rules `IMG-001` through `IMG-004` implementing Error Level Analysis (ELA at 90% quality), Laplacian sharpness variance tiling, OpenCV ORB keypoint descriptor matching for copy-move cloned stamps/signatures, and contour aspect ratio analysis.
- **Phase E — Real Field-Level Confidence:** Extracts per-word confidences from `pytesseract.image_to_data` and mathematically computes averages for extracted entities. Digital text is explicitly labeled `"n/a (digital text)"`. UI and dossiers display heuristic weights as **"Rule Weight"** to prevent confusing rule thresholds with statistical probabilities.
- **Phase F — Cross-Document Correlation & Relationship Graph:** Multi-document correlation engine (`backend/correlator.py`) connecting shared invoice numbers, matching financial totals, fuzzy counterparties (via corporate suffix normalization), and chronological conflicts. Visualized via an interactive vanilla SVG relationship graph with zero external JavaScript charting libraries. Includes content-based semantic classification fallback (`backend/classifier_content.py`).
- **Phase G — Benchmark Evaluation & Proof:** Programmatic generator (`tools/make_samples.py`) creating a 20-file benchmark dataset (`demo_dataset/`) with ground-truth `labels.csv`, evaluated via `tools/evaluate.py` to produce unvarnished precision, recall, and false alarm performance metrics.

## 🔬 Technical Corrections & Honesty Notes

To maintain forensic and scientific accuracy, the following technical facts are explicitly clarified:

1. **Entity Extraction (NER):** VEXORA utilizes deterministic, high-efficiency regular expressions and pattern extractors in `backend/ner.py`, rather than spaCy or heavy statistical NLP language models.
2. **File Validation:** Document ingestion validates file extensions against an allowed list and computes SHA-256 cryptographic hashes for tamper resistance; it does not invoke binary MIME `libmagic` sniffing.
3. **PDF Libraries:** Text extraction, glyph coordinates, and page bitmap rasterization are performed via PyMuPDF (`pymupdf`). Vector PDF dossiers are constructed via PyMuPDF and ReportLab primitives.
4. **Honesty in Forensics:** The system never declares "confirmed fraud." Every automated finding is classified as a heuristic observation or potential anomaly requiring qualified human investigator review.

## ⚠️ Important Disclaimer

VEXORA is intended as a document analysis and investigation-support prototype.

Automated findings indicate potential anomalies or inconsistencies and must not be treated as definitive proof of document manipulation, fraud, or wrongdoing.

All findings require appropriate human verification and interpretation.

## 🎓 Project Objectives

- Explore practical applications of AI-assisted document analysis.
- Understand PDF processing and OCR technologies.
- Apply Python programming to real-world problems.
- Learn frontend and backend integration.
- Develop contextual comparison and evidence-mapping logic.
- Build a complete, demonstrable software application.
- Gain practical experience with software development and GitHub.

## 🔮 Future Improvements

Potential future enhancements include:

- Advanced document similarity analysis.
- Improved visual anomaly detection.
- More sophisticated entity relationship mapping.
- Additional document formats.
- Advanced investigation analytics.
- Enhanced evidence visualization.

## 👩‍💻 Development

VEXORA is being developed as a learning-focused software project with an emphasis on understanding the technologies, implementation logic, and complete application workflow.

**Development Philosophy:** Build it. Understand it. Test it. Improve it.

---

<p align="center">
  <img src="frontend/images/logo-icon.png" alt="VEXORA Emblem" width="64"><br><br>
  <b>VEXORA</b><br>
  <i>Seeing What Others Overlook</i>
</p>
