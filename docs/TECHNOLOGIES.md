# VEXORA — Technology Stack & Engineering Rationale

This document provides a comprehensive catalogue of every library, database engine, frontend component, and external tool employed in the VEXORA Document Forensics and Contextual Intelligence System, documenting why each was selected and how it is configured.

---

## 1. Backend Core & Web Framework

| Technology | Version / Spec | Purpose in VEXORA | Why Chosen Over Alternatives | Configuration & Runtime |
|---|---|---|---|---|
| **Python** | 3.11 / 3.12 / 3.15 | Primary runtime for all backend services, forensic pipelines, and test suites. | Rich ecosystem for document analysis, native C-binding interfaces for computer vision and PDF rendering, robust standard library (`hashlib`, `difflib`, `re`, `sqlite3`). | Runs in virtual environment (`.venv`). |
| **Flask** | 3.0+ | Lightweight REST API server and static asset host. | Minimal overhead, zero boilerplate, transparent routing, instant cold starts (<500ms), and seamless single-command demo launch. Avoids heavy ORM or async event loop complexities of Django/FastAPI. | Configured via `backend/config.py` with 16MB file upload limit (`MAX_CONTENT_LENGTH = 16 * 1024 * 1024`). Runs on `127.0.0.1:5000`. |
| **Werkzeug** | 3.0+ | WSGI utility library, secure file uploads, HTTP exception handlers. | Industry-standard security utilities: `secure_filename` prevents path traversal attacks (`../../`) on user uploads. | Included with Flask; handles multipart form data parsing. |

---

## 2. Persistence & Storage Layer

| Technology | Purpose in VEXORA | Why Chosen Over Alternatives | Configuration & Runtime |
|---|---|---|---|
| **SQLite3** | Primary relational database (`vexora.db`) storing cases, documents, findings, extracted entities, discrepancy matrices, reports, and audit logs. | Zero-configuration, zero external service dependency (crucial for hackathon / live offline judging), deterministic single-file portability, ACID compliance, sub-millisecond local query latencies. | Managed via `backend/database.py` with foreign key enforcement (`PRAGMA foreign_keys = ON`), row factory (`sqlite3.Row`), and safe dynamic migrations. |
| **Local File System** | Storage of uploaded original documents and cached evidence crops (`uploads/`). | Direct filesystem access for PyMuPDF and OpenCV without blob storage overhead or cloud latency. | File paths recorded in `documents.file_path`; files sanitized and hashed before saving. |

---

## 3. Document Parsing & PDF Vector Forensics

| Technology | Purpose in VEXORA | Why Chosen Over Alternatives | Configuration & Runtime |
|---|---|---|---|
| **PyMuPDF (`pymupdf` / `fitz`)** | Digital text extraction with character-level bounding boxes, PDF metadata inspection, xref update detection, embedded raster image extraction, and vector PDF dossier rendering. | Up to 10x faster than `pdfplumber` or `pypdf`; provides direct access to MuPDF's low-level font descriptor tables, stream dictionaries, and vector graphics pipelines. Never requires headless Chromium. | Imported via guarded try/except block (`import pymupdf as fitz`). Used for both PDF analysis (`forensics_pdf.py`, `extractor.py`) and PDF dossier generation (`reporter.py`). |
| **ReportLab** | Programmatic PDF report and dossier generation utility. | Industry standard for structured vector PDF documents with flowable layouts, page number templates, and precise typography. | Used alongside PyMuPDF in `backend/reporter.py` for audit-ready dossier synthesis. |

---

## 4. Computer Vision & Raster Forensics

| Technology | Purpose in VEXORA | Why Chosen Over Alternatives | Configuration & Runtime |
|---|---|---|---|
| **OpenCV (`opencv-python-headless`)** | Laplacian variance sharpness tiling (`IMG-002`), ORB keypoint descriptor extraction and matching for copy-move cloned stamps (`IMG-003`), adaptive thresholding and stroke analysis for signature regions (`IMG-004`). | Headless distribution eliminates GUI library dependencies (X11/Wayland/GDI) ensuring frictionless installation across Windows, Linux, and macOS containers. Highly optimized C++ implementations of spatial convolution algorithms. | Imported conditionally in `backend/forensics_image.py`. Bypassed automatically when processing born-digital vector pages. |
| **Pillow (`PIL`)** | Error Level Analysis (ELA) recompression surface calculation (`IMG-001`), raster image format conversion, evidence crop generation. | Native Python imaging library with fine-grained control over JPEG quantization tables and pixel-level image difference mathematics (`ImageChops.difference`). | Used for image manipulation, ELA recompression at quality 90, and drawing visual finding bounding boxes. |
| **NumPy** | High-performance multidimensional array manipulations, block statistical distributions, median/standard-deviation outlier detection. | Vectorized array operations allow real-time image tiling and error distribution calculations in milliseconds without Python loop overhead. | Applied across `forensics_image.py` for block variance computation and threshold gating. |

---

## 5. Optical Character Recognition (OCR)

| Technology | Purpose in VEXORA | Why Chosen Over Alternatives | Configuration & Runtime |
|---|---|---|---|
| **Tesseract OCR (`pytesseract`)** | Optical character recognition on scanned image uploads (`png`, `jpg`, `tiff`) and raster PDF attachments; extracts per-word bounding boxes and token confidences (`image_to_data`). | Open-source, offline, privacy-preserving OCR engine with zero cloud subscription cost. Word-level confidence output enables objective entity confidence scoring. | Controlled via `VEXORA_STRICT_OCR` in `.env`. When Tesseract binary is absent on host PATH, safely degrades to fallback mode with UI status warning. |

---

## 6. AI & Large Language Model Tier

| Technology | Purpose in VEXORA | Why Chosen Over Alternatives | Configuration & Runtime |
|---|---|---|---|
| **Direct HTTPS (`requests`)** | Communicates with Google Gemini and OpenAI REST endpoints for contextual explanations and AI entity extraction. | Using pure standard HTTP `requests` eliminates massive vendor SDK dependency trees (`google-generativeai`, `openai`), reducing install footprint and avoiding breaking upstream API changes. | Configured via `backend/llm.py` with 30-second timeout, 1 automatic retry on network errors, and model configuration via `VEXORA_LLM_MODEL`. |
| **Google Gemini API (`gemini-2.5-flash`)** | Default AI reasoning model for document explanation and cross-checking. | High-speed inference, strong reasoning capabilities on structured tabular data, cost-effective for enterprise processing. | Activated when `ENABLE_LLM=true` and `VEXORA_LLM_API_KEY` is provided in `.env`. |
| **OpenAI API (`gpt-4o-mini`)** | Alternative AI reasoning model provider. | Fallback or enterprise option for environments standardized on Azure / OpenAI infrastructure. | Selectable via `VEXORA_LLM_PROVIDER=openai` in `.env`. |

---

## 7. Frontend User Interface

| Technology | Purpose in VEXORA | Why Chosen Over Alternatives | Configuration & Runtime |
|---|---|---|---|
| **Vanilla JavaScript (ES6+)** | Dynamic UI interactions, live backend synchronization (`refreshAll`), view routing, file upload handling, evidence modal controls, and API communication. | Zero compilation, zero build toolchain (`npm run build`, Webpack, Vite), zero bundle weight, instant load time, zero framework obsolescence risk. Modifiable and testable in real-time. | Packaged in `frontend/js/app.js` and `frontend/js/v2.js`. Synchronizes against `resolveApiBase()` automatically. |
| **Pure HTML5 & CSS3** | Application layout, dark forensic theme, responsive grid systems, animated badges, and print-optimized report styling. | Native CSS custom variables (`--bg-primary`, `--status-verified`, `--status-danger`) allow instant, consistent design system styling with zero CSS framework bloat (no Tailwind or Bootstrap runtime overhead). | Embedded in `frontend/index.html` and `frontend/css/style.css`. |
| **Vanilla SVG Graph Engine** | Interactive relationship and entity correlation graph in Cross-Document Comparison view. | Native SVG DOM manipulation renders force-directed multi-document relationship networks without importing heavy external visualization libraries (e.g. D3.js or Cytoscape.js). | Built directly in `frontend/js/v2.js` (`window.v2LoadRelationshipGraph`). |

---

## 8. Verification & Benchmarking Harness

| Technology | Purpose in VEXORA | Why Chosen Over Alternatives | Configuration & Runtime |
|---|---|---|---|
| **Python `unittest`** | Automated test suite covering ingestion, classification, visual forensics, image heuristics, cross-document comparison, dossier generation, and AI fallbacks. | Built into standard library, executes in <10 seconds, zero external test runner requirements. | Run via `python -m unittest discover tests`. |
| **Benchmark Evaluator (`tools/evaluate.py`)** | Objective precision, recall, specificity, and accuracy measurement across 20 synthetic benchmark documents and 3 cross-document case scenarios. | Generates transparent, verifiable empirical metrics. | Run via `python tools/evaluate.py`. |
| **Synthetic Sample Generator (`tools/make_samples.py`)** | Deterministic generation of genuine and tampered synthetic documents with ground truth labels. | Enables reproducible automated evaluation without exposing real-world proprietary documents. | Run via `python tools/make_samples.py`. |

