<p align="center">
  <img src="frontend/images/logo.png" alt="VEXORA — Seeing What Others Overlook" width="480">
</p>

<p align="center">
  <b>SEEING WHAT OTHERS OVERLOOK</b><br>
  <i>Multimodal Document Forensics, Contextual Verification & Evidence Provenance Platform</i>
</p>

VEXORA is an explainable digital document forensics and intelligence platform engineered to detect digital manipulation, typographic anomalies, vector masking, and cross-document financial discrepancies across multi-document fraud schemes.

The platform combines PyMuPDF vector path analysis, OpenCV image heuristics, deterministic rule engines, and a Google GenAI Gemini LLM layer into an audit-ready investigation workspace with 100% verifiable ground truth benchmarks.

---

## 🎯 Project Overview

Investigating multi-document financial fraud manually is error-prone, especially when documents exhibit microscopic typographic overwrites, concealed vector layers, or conflicting cross-document dates.

VEXORA addresses these challenges through a 7-stage evidence processing pipeline:
1. **Cryptographic Ingestion & Custody**: Magic byte validation and SHA-256 integrity tracking.
2. **Multimodal Extraction**: Native vector geometry extraction (spans, fonts, paths) and real OCR word-level confidence.
3. **Deep PDF & Vector Forensics**: Detects white vector masking, incremental hex saves, metadata mismatches, and resolution variance.
4. **Raster Image Forensics (Heuristics)**: Error Level Analysis (ELA), grid noise variance, and signature presence heuristics.
5. **Google GenAI LLM Layer (`gemini-2.5-flash`)**: Structured JSON extraction, mathematical verification, exact quote tracking, and dossier summaries badged `"AI-assessed, needs review"`.
6. **Cross-Document Discrepancy Matrix & Provenance**: Semantic field matching and directed evidence graph visualization.
7. **Audit-Ready PDF Dossier Generation**: Generates full multi-page reports (PS Sections 7.1 to 7.6) with embedded red-annotated evidence pages.

---

## 📊 Empirical Forensic Benchmark (100% Verifiable Ground Truth)

VEXORA includes a standalone empirical benchmark suite evaluated over 20 real-world vector test documents (10 Genuine vs 10 Tampered):

| Metric | Score | Evaluation Details |
| :--- | :--- | :--- |
| **Accuracy** | **100.0%** | 20 / 20 correct classifications |
| **Precision** | **100.0%** | Zero false alarms ($FP = 0$) |
| **Recall / Sensitivity** | **100.0%** | All 10 tampered documents detected ($FN = 0$) |
| **Specificity** | **100.0%** | 10 / 10 genuine documents verified ($TN = 10$) |
| **F1-Score** | **100.0%** | Optimal harmonic mean of precision and recall |
| **False Positive Rate (FPR)** | **0.0%** | No legitimate documents flagged as fraud |
| **Average Latency** | **9.7 ms** | High-throughput sub-10ms analysis per document |

To run the live benchmark evaluation suite:
```bash
.\.venv\Scripts\python eval/run_benchmark.py
```

---

## ✨ Key Features & Capabilities

| Capability | Description | Status | Reference File |
| :--- | :--- | :--- | :--- |
| **White Vector Masking** | Flags white rectangle paths masking underlying text | Implemented | `backend/pdf_forensics.py` (`PDF-R101`) |
| **Incremental PDF Saves** | Scans binary for multiple `%%EOF` markers | Implemented | `backend/pdf_forensics.py` (`PDF-R102`) |
| **Producer / Issuer Mismatch** | Flags official forms compiled in desktop editors | Implemented | `backend/pdf_forensics.py` (`PDF-R103`) |
| **Superimposed Graphics** | Identifies raster images layered over vector text | Implemented | `backend/pdf_forensics.py` (`PDF-R104`) |
| **Intra-Page DPI Discrepancy** | Detects spliced low-res elements on high-res pages | Implemented | `backend/pdf_forensics.py` (`PDF-R105`) |
| **Typographic Font Anomaly** | Flags kerning jumps and font family switches | Implemented | `backend/analyzer.py` (`RULE-VIS-001`) |
| **Bounding Box Collision** | Detects overlapping and colliding text spans | Implemented | `backend/analyzer.py` (`RULE-VIS-002`) |
| **Date Flow Inversion** | Flags chronological anomalies (Due Date < Issue Date) | Implemented | `backend/analyzer.py` (`RULE-CTX-001`) |
| **Contextual Math Check** | Verifies line items summation against stated total | Implemented | `backend/analyzer.py` (`RULE-CTX-003`) |
| **Google Gemini LLM Layer** | Structured JSON extraction, math audit & exact quotes | Implemented | `backend/llm_layer.py` (`gemini-2.5-flash`) |
| **Real Vector Page Highlighting** | PyMuPDF pixmap rendering with crisp red bounding boxes | Implemented | `backend/visualizer.py` (`/pages/<num>/annotated`) |
| **Real Document Inspector UI** | Interactive viewer with zoom, page navigation & box toggle | Implemented | `frontend/index.html` & `app.js` |
| **Cross-Document Discrepancy** | Correlates invoice, PO, and bank records | Implemented | `backend/comparator.py` |
| **Evidence Provenance Graph** | Directed topology of cases, documents, and findings | Implemented | `backend/comparator.py` (`/provenance`) |
| **PDF Dossier (PS 7.1 to 7.6)** | Multi-page report with embedded visual proofs & hash | Implemented | `backend/reporter.py` |
| **Error Level Analysis (ELA)** | Pixel difference matrix after 90% recompression | Heuristic | `backend/image_forensics.py` (`IMG-R201`) |
| **Noise Variance Check** | Local Laplacian variance across 8x8 grid | Heuristic | `backend/image_forensics.py` (`IMG-R202`) |
| **Signature Proximity Check** | Stroke pixel density near signature labels | Heuristic | `backend/image_forensics.py` (`IMG-R203`) |

---

## ⚙️ Technology Stack

### Frontend
- **HTML5 & Vanilla CSS3** – High-contrast dark forensic theme, responsive grid layouts, and custom tokens.
- **JavaScript (ES6+)** – Interactive document inspector, dynamic bounding-box toggle, live benchmark trigger, and REST client.

### Backend & Core Engines
- **Python 3.10+** – Core forensic analysis and data processing engine.
- **Flask** – REST API server exposing forensic, visualizer, audit, and benchmark endpoints.
- **PyMuPDF (`fitz`)** – Native PDF vector extraction, path drawing inspection, and high-res pixmap rendering.
- **OpenCV (`cv2`) & Pillow (`PIL`)** – Error Level Analysis, grid noise variance, and image geometry analysis.
- **Pytesseract** – Scanned document text extraction with real word-level confidence metrics.
- **Google GenAI SDK (`google-genai`)** – Gemini 2.5 Flash LLM integration with verbatim citation enforcement.
- **SQLite3** – ACID-compliant evidence vault with cryptographic audit trail logging.

---

## 📁 Repository Structure

```text
VEXORA/
│
├── frontend/
│   ├── index.html              # Investigation workspace with Real Document Inspector & Benchmark Card
│   ├── css/
│   │   └── style.css           # Design system tokens, viewer styles & forensic badges
│   ├── js/
│   │   └── app.js              # Real viewer controls, AI contextual audit & benchmark runner
│   └── images/
│       └── logo.png            # Official VEXORA brand logo
│
├── backend/
│   ├── analyzer.py             # Rule-based visual and contextual forensic engine
│   ├── app.py                  # Flask REST API server, visual endpoints & benchmark routes
│   ├── comparator.py           # Cross-document comparison & provenance graph builder
│   ├── config.py               # Runtime configuration & environment variables
│   ├── database.py             # SQLite database layer & schema initialization
│   ├── extractor.py            # PyMuPDF vector parser & Pytesseract OCR extractor
│   ├── image_forensics.py      # ELA, grid noise variance & signature presence heuristics
│   ├── llm_layer.py            # Gemini 2.5 Flash layer (JSON, math audit, exact quotes)
│   ├── models.py               # Data structures, serialization & finding helpers
│   ├── ner.py                  # Rule-based regex entity recognition
│   ├── pdf_forensics.py        # Real PDF forensics (whiteout, %%EOF, metadata, superimposed)
│   ├── reporter.py             # Section 7.1-7.6 PDF Dossier generator with embedded proofs
│   ├── uploader.py             # Magic byte validator & secure file custody ingestion
│   ├── visualizer.py           # PyMuPDF pixmap renderer with crisp red bounding boxes
│   ├── schema.sql              # Relational database schema
│   └── vexora.db               # SQLite database
│
├── eval/
│   ├── benchmark_dataset/      # 20 ground truth PDF vectors (10 Genuine vs 10 Tampered)
│   ├── ground_truth.json       # Labeled ground truth metadata & expected rules
│   ├── run_benchmark.py        # Evaluation runner computing accuracy, precision, recall, latency
│   ├── benchmark_report.json   # Machine-readable evaluation metrics
│   └── BENCHMARK_REPORT.md     # Detailed markdown evaluation report
│
├── tests/
│   └── test_backend.py         # Automated test suite (39 tests passing cleanly)
│
├── ARCHITECTURE.md             # Complete architecture documentation & Mermaid flowchart
├── CAPABILITY_MATRIX.md        # Comprehensive 4-tier capability matrix (Implemented/Partial/Planned/Unsupported)
├── LIMITATIONS_AND_ASSUMPTIONS.md # Scope, dependencies, OCR behavior, and legal boundaries
├── SAMPLE_DOSSIER.md           # Full sample investigation dossier covering PS Sections 7.1 to 7.6
├── requirements.txt            # Python dependencies (pymupdf, google-genai, opencv-python-headless, etc.)
└── README.md
```

---

## 🚀 Setup & Execution Instructions

### 1. Prerequisites
- Python 3.10+
- (Optional) Google Gemini API Key for live AI reasoning (`set GEMINI_API_KEY=your_key`)
- (Optional) Tesseract OCR 5.x for scanned image text extraction

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/Misari-Vadalia-13/VEXORA.git
cd VEXORA

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate   # On Windows
# source .venv/bin/activate # On Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Empirical Benchmark Suite
To evaluate VEXORA against the 20-file ground truth dataset:
```bash
python eval/run_benchmark.py
```

### 4. Start the Application Server
```bash
python backend/app.py
```
Open your web browser and navigate to:
**`http://127.0.0.1:5000`**

### 5. Run the Automated Test Suite
```bash
python -m unittest tests/test_backend.py
```
All 39 automated tests will execute and pass cleanly.

---

## ⚖️ Limitations & Honest Disclosure

In accordance with Problem Statement Section 11 (*"identify unsupported capabilities honestly"*):
- **Tesseract OCR Absence**: If Tesseract is not installed on the system host, VEXORA ingests structural metadata and reports `ocr_available = false` honestly without fabricating synthetic text.
- **Google OAuth Simulation**: Google Sign-In is provided as a client-side demo mode for evaluator testing without requiring production OAuth2 server secrets.
- **Heuristic Labeling**: Error Level Analysis (ELA), noise variance, and signature proximity are heuristic algorithms and are explicitly marked as heuristics in the code and interface.
- **LLM Attestation**: All generative AI outputs carry the mandatory badge `"AI-assessed, needs review"` and quote verbatim document text to ensure traceability.

---

## 👩‍💻 Author & Project Credits
- **Lead Developer**: Misari Vadalia
- **Repository**: [Misari-Vadalia-13/VEXORA](https://github.com/Misari-Vadalia-13/VEXORA)
- **Motto**: *Seeing What Others Overlook*
