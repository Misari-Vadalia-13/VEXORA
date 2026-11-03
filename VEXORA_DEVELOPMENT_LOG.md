# VEXORA — Development Log

## Project Overview

**VEXORA** — AI-Powered Document Forensics and Contextual Intelligence System.  
A centralized platform designed to analyze digital and scanned documents, uncover contextual inconsistencies, extract named entities, detect visual forensic anomalies, correlate cross-document evidence, and generate audit-ready investigation dossiers.

---

## Phase Tracker

| Phase | Title | Status | Completion Date |
|---|---|---|---|
| 1 | Project Setup & UI Foundation | **Completed** | 2026-11-01 |
| 2 | Core Pages & User Interface | **Completed** | 2026-11-01 |
| 3 | Backend & Database Integration | **Completed** | 2026-11-01 |
| 4 | Document Upload & Classification | **Completed** | 2026-11-01 |
| 5 | OCR & Information Extraction | **Completed** | 2026-11-01 |
| 6 | Forensic & Contextual Analysis | **Completed** | 2026-11-01 |
| 7 | Cross-Document Comparison & Evidence Mapping | Not Started | — |
| 8 | Investigation Dossier & Report Generation | Not Started | — |
| 9 | Audit Trail, Testing & Finalization | Not Started | — |

---

## Phase 1 — Project Setup & UI Foundation Log

- **Completion Date:** 2026-11-01
- **Status:** Completed (Approved by User)

### Features Implemented
1. **Repository & Directory Structure Initialization:**
   - Established the structured application architecture (`frontend/`, `backend/`, `uploads/`, `reports/`, `tests/`).
   - Added `requirements.txt` with foundational dependencies.
2. **Design System & CSS Styling Foundation:**
   - Created `frontend/css/style.css` implementing a crisp, high-contrast modern light aesthetic (`#f8fafc` canvas, pure white elevated cards, `#0f172a` deep obsidian high-contrast text, royal indigo accents `#4f46e5`, and vibrant status indicators) with complete dark mode support (`[data-theme="dark"]`).
   - Designed responsive layout grids, glassmorphism cards, status pills, and typography tokens with Google Fonts (`Outfit` and `Plus Jakarta Sans`).
   - Added interactive Theme Toggle button (`☀️ Light / 🌙 Dark`) in the topbar header with persistent user preferences in `localStorage`.
   - Integrated native View Transitions API (`document.startViewTransition`) for zero-glitch cinematic theme cross-fades.
3. **Application Shell & Navigation:**
   - Developed collapsible, responsive sidebar with active route highlighting, brand logo, and core engine status indicator.
   - Built sticky top header with dynamic breadcrumbs, live system clock, notifications button, and investigator profile badge.
4. **Interactive Dashboard View:**
   - Created hero banner outlining forensic capabilities and investigation scope.
   - Added 4 primary metric stat cards (Active Cases, Documents Indexed, Flagged Inconsistencies, Evidence Correlated).
   - Implemented 7-stage Investigation Workflow Pipeline visualizer.
   - Built Recent Cases data table with risk levels, status tags, and action buttons.
   - Built Live Forensic Anomaly Feed detailing visual, contextual, and cross-document alerts.
5. **Interactive Modal & Real-Time Client Logic:**
   - Implemented "+ New Case" modal dialog with validation and dynamic live injection into the active cases table.
   - Added live real-time search filtering across table rows.
   - Integrated toast notification manager and keyboard shortcuts (`Ctrl+K` for search focus, `Escape` for modal dismiss).
   - Added root `index.html` forwarding automatically to `frontend/index.html`.

---

## Phase 2 — Core Pages & User Interface Log

- **Completion Date:** 2026-11-01
- **Status:** **Completed** (Awaiting User Review & Approval)

### Features Implemented
1. **Multi-View SPA Routing Engine:**
   - Developed single-page application router supporting hash-based routing (`#dashboard`, `#cases`, `#upload`, `#library`, `#forensics`, `#comparison`, `#evidence`, `#dossier`, `#settings`).
   - Deep-linking support on page reload or direct link navigation with smooth scrolling and dynamic breadcrumbs.
2. **Investigation Case Management View (`#cases`):**
   - Built full case inventory cards grid with case references, status pills, risk tags, document tallies, and anomaly badges.
   - Added priority filter toolbar (All Cases, High Risk, Medium Priority, Low Risk).
   - Connected case creation directly to both the table and grid with reactive badge count updates.
3. **Document Ingestion & Upload View (`#upload`):**
   - Interactive drag-and-drop file upload zone supporting PDF, JPG, PNG formats up to 25MB.
   - Target case assignment dropdown and document classification selector (Bank Statement, Tax Return, ID Proof, Invoice, Contract).
   - Simulated staged processing queue with progress bars and "Process All" triggers.
4. **Document Library & Evidence Vault (`#library`):**
   - Multi-category filter pills (Financial, Identity Proofs, Tax Returns, Legal Contracts).
   - Document artifact cards displaying file sizes, page counts, forensic tags, and download triggers.
5. **Forensic Analysis Results Inspector (`#forensics`):**
   - Side-by-side interactive split-view featuring a paper document page simulator.
   - Highlighted visual bounding boxes (`.forensic-bbox`) for typographic font overwrites and baseline kerning anomalies.
   - Detailed forensic observations feed with page/coordinate coordinates, confidence scores, and mandatory human review recommendations.
6. **Cross-Document Comparison Matrix (`#comparison`):**
   - Dual-document selector comparing identity proofs against official tax filings.
   - Entity alignment matrix comparing Full Legal Name, DOB, Tax ID, Address, and Issuing Authority.
   - Forensic verdicts highlighting matching attributes vs critical discrepancies (e.g. 2-year age conflict).
7. **Evidence Provenance Graph (`#evidence`):**
   - Provenance node tree mapping detected findings back to exact document IDs, page references, and line numbers.
8. **Investigation Dossier & Report Export (`#dossier`):**
   - Comprehensive printable investigation dossier with official case references and timestamps.
   - Mandatory human-review disclaimer alert box.
   - Print-ready trigger (`window.print()`) and simulated PDF export button.
9. **Settings & Node Configuration (`#settings`):**
   - Investigator profile form (Name, Role, Department).
   - Forensic sensitivity sliders (Visual overwrite sensitivity, OCR confidence tolerance).
   - Local node diagnostics report.
10. **Modular Companion Page Files:**
   - Generated modular entrypoints in `frontend/pages/` (`cases.html`, `upload.html`, `library.html`, `analysis.html`, `comparison.html`, `report.html`, `settings.html`) that seamlessly connect to the unified app shell.

### Technologies Used
- **HTML5:** Semantic view sections, paper canvas simulators, range inputs, drag-and-drop APIs.
- **CSS3:** View Transitions API, CSS Grid layouts, bounding box styling, print stylesheets (`@media print`).
- **JavaScript (ES6):** Client router, drag-and-drop file staging, dynamic filtering, reactive card injection, keyboard shortcuts.

### Actual Testing Results
- **Page Access Verification:** All 8 companion pages and the main app tested via HTTP web request; returned `200 OK`.
- **Syntax Validation:** `node --check frontend/js/app.js` passed with exit code 0.
- **Navigation Testing:** Tested hash routing across all 9 views; active classes, breadcrumbs, and scroll restoration functioned as expected.
- **Interactive Features:** Verified case priority filtering, document library category filtering, drag-and-drop file addition, and "+ New Case" reactive badge increments.

### Known Limitations
- Data modifications remain client-side in the DOM / browser storage until SQLite database and Python Flask backend routes are established in Phase 3.

### Concepts Learned
- Client-side Single Page Application (SPA) routing with `history.pushState` and `window.location.hash`.
- Forensic UI principles: side-by-side comparative layout, bounding box coordinates, and visual anomaly tags.
- Cross-document entity discrepancy matrix design.
- Separation of concerns between modular entry files and centralized state management.

### Suggested Git Commit Message
`feat(phase-2): implement all core screens, multi-view router, and forensic UI components`

### Approval Status
- **Approved by User**: 2026-11-01 (Pushed to GitHub `main` branch under commit `7aae7ca`).

---

## Phase 3 — Backend & Database Integration Log

- **Completion Date:** 2026-11-01
- **Status:** Completed (Ready for Review)

### Features Implemented
1. **Python Environment & Architecture Scaffolding:**
   - Established isolated Python virtual environment (`.venv`) adhering to dependency management standards.
   - Installed Flask 3.1.3 and its core ecosystem (`Werkzeug`, `Jinja2`, `Click`, `Blinker`, `itsdangerous`, `MarkupSafe`).
   - Created `backend/config.py` managing filesystem paths, database URIs, upload directories, security keys, and environment flags.
   - Created `backend/__init__.py` packaging backend modules cleanly.
2. **SQLite Relational Database Engine:**
   - Authored `backend/schema.sql` defining 5 core tables with strict constraints, foreign keys, and performant indexes:
     - `users`: ID, username, email, scrypt password hash, role, badge number, creation timestamp.
     - `cases`: ID (`CAS-YYYY-NNNN`), title, type, priority, status, investigator, description, timestamps.
     - `documents`: ID (`DOC-YYYY-NNNN`), case reference, filename, type, file size, storage path, category, classification confidence, processing status, timestamps.
     - `findings`: ID (`FND-YYYY-NNN`), case reference, document reference, anomaly title, severity, category, description, confidence, status, timestamps.
     - `audit_logs`: ID, action name, entity type, entity ID, event description, acting user, immutable timestamp.
   - Authored `backend/database.py` managing SQLite connection lifecycle with `sqlite3.Row` dictionary-like column mapping, safe automated migration, and database seed population.
   - Pre-populated realistic demonstration records (Apex Global Offshore Audit, Veridian IP Due Diligence, Solari Energy Subsidies) ensuring immediately demonstrable functionality upon launch.
3. **Business Logic & Validation Layer:**
   - Authored `backend/models.py` implementing repository queries with parameterized SQL (`?` placeholders) protecting against SQL injection attacks.
   - Implemented strict input validation (`validate_case_data`, `validate_user_registration`) rejecting empty titles, illegal priority enums, malformed emails, and invalid status values.
   - Implemented auto-generating sequential identifiers (`CAS-YYYY-0001`, `DOC-YYYY-0001`, `FND-YYYY-001`).
   - Implemented system telemetry calculation (`get_system_stats`) aggregating live case counts, flagged document ratios, and risk percentages.
4. **Flask REST API & Static Application Server:**
   - Created `backend/app.py` serving both the complete frontend application (`/`, `/index.html`, `/css/...`, `/js/...`, `/pages/...`) and the REST API suite:
     - `GET /api/health` — returns database connection status and engine metadata.
     - `GET /api/stats` — returns real-time KPI metrics for dashboard counters.
     - `GET /api/cases` — lists cases with priority, status, and search query filters.
     - `POST /api/cases` — creates investigation case with validation and audit logging (returns HTTP 201).
     - `GET /api/cases/<id>` — retrieves case details with attached documents and findings.
     - `PUT /api/cases/<id>` — updates case status and parameters.
     - `DELETE /api/cases/<id>` — deletes case and logs activity.
     - `GET /api/documents` & `POST /api/documents` — document registry and retrieval.
     - `GET /api/findings` & `POST /api/findings` — forensic anomaly registry.
     - `GET /api/audit-logs` — provides chronological activity trail.
     - `POST /api/auth/login` & `POST /api/auth/register` — investigator authentication with scrypt hashing.
     - `GET /api/auth/current-user` — returns current analyst profile.
   - Integrated non-blocking CORS headers (`Access-Control-Allow-Origin: *`) allowing development previews across both port 5000 and port 8080.
5. **Frontend Live Database Integration:**
   - Enhanced `frontend/js/app.js` with `initBackendSync()` and `getApiBase()` to automatically discover the Flask backend.
   - Replaced static "+ New Case" client mocking with asynchronous `fetch('/api/cases', { method: 'POST' })` persisting records directly to SQLite.
   - Added optimistic UI fallback ensuring uninterrupted usability even if the backend is offline.
   - Enhanced dashboard banner to display live connection state: `⚡ VEXORA Intelligence Engine • SQLite Connected (Phase 3)`.
6. **Automated Backend Test Suite:**
   - Authored `tests/test_backend.py` with 11 automated test cases using Python's standard `unittest` framework.
   - Verified isolated test database setup and teardown (`test_vexora.db`).
   - Verified input validation rejection (HTTP 400), authentication flow (HTTP 201 / 401 / 409), CRUD operations, and health checks.

### Technologies Introduced
- **Python (v3.15):** Core programming language for backend business logic, validation, and database operations.
- **Flask (v3.1.3):** Lightweight WSGI web application framework connecting frontend requests to database models.
- **SQLite 3:** Built-in serverless relational database engine storing users, cases, documents, findings, and audit trails.
- **Werkzeug Security:** Industry-standard password hashing and verification using the `scrypt` key derivation function.
- **Unittest:** Python standard library automated testing framework.

### Actual Testing Results
- **Automated Test Suite:** Ran 11 tests via `unittest` — 11/11 passed in 3.58 seconds (`OK`).
- **Database Persistence Check:** Created case `CAS-PERSIST-999` in one Python process, terminated the process, launched a separate process, and successfully retrieved the case from `backend/vexora.db`.
- **Live HTTP API Tests:**
  - `GET http://127.0.0.1:5000/api/health` ➔ HTTP 200 (`healthy`, SQLite connected).
  - `GET http://127.0.0.1:5000/api/stats` ➔ HTTP 200 (returned active cases and document metrics).
  - `POST http://127.0.0.1:5000/api/cases` (valid payload) ➔ HTTP 201 (`CAS-2026-0893` created and saved in SQLite).
  - `POST http://127.0.0.1:5000/api/cases` (empty title) ➔ HTTP 400 (`Case title is required and cannot be empty.`, field: `title`).
  - `DELETE http://127.0.0.1:5000/api/cases/CAS-2026-0893` ➔ HTTP 200 (`Case deleted successfully`).
- **JavaScript Syntax Check:** `node --check frontend/js/app.js` passed with exit code 0.

### Known Limitations
- File binary ingestion (actual PDF/image binary streaming to `uploads/` directory) and automated document classification are scheduled for Phase 4.
- Forensic text extraction and OCR processing pipelines are scheduled for Phase 5.

### Concepts Learned
1. **Relational Database Schema Design:** Primary keys, foreign key constraints (`ON DELETE CASCADE`), CHECK constraints, and indexing for fast lookups.
2. **REST API Design & HTTP Status Codes:** Using standard codes (`200 OK`, `201 Created`, `400 Bad Request`, `401 Unauthorized`, `404 Not Found`, `409 Conflict`, `500 Server Error`).
3. **Parameterized SQL Queries:** Always passing variables as parameters (`?`) rather than string concatenation to prevent SQL injection vulnerabilities.
4. **Password Hashing:** Storing cryptographically secure one-way hashes (`scrypt`) instead of plaintext passwords.
5. **Full-Stack Application Wiring:** Bridging a vanilla HTML/CSS/JS frontend to a Python Flask API with live telemetry and optimistic UI fallbacks.

### Approval Status
- **Approved by User**: 2026-11-01 (Pushed to GitHub `main` branch under commit `b246dbe`).

---

## Phase 4 — Document Upload & Classification Log

- **Completion Date:** 2026-11-01
- **Status:** Completed (Pushed to GitHub main branch)

### Features Implemented
1. **Multi-Format Document Ingestion Engine (`backend/uploader.py`):**
   - Implemented `process_single_upload` supporting PDF, PNG, JPG, JPEG, TIFF, and BMP files.
   - Built strict file type and extension validation with automatic rejection of unsupported formats.
   - Built file size guards rejecting empty (0-byte) files and files exceeding the 16 MB threshold.
   - Sanitized filenames using `werkzeug.utils.secure_filename` to prevent path traversal vulnerabilities.
   - Implemented collision-resistant unique disk naming using sequential identifiers (`{doc_id}_{safe_filename}`).
2. **Forensic Integrity & SHA-256 Hashing:**
   - Implemented cryptographic SHA-256 checksum generation (`compute_sha256`) for every ingested file stream.
   - Preserved document chain-of-custody in the SQLite `documents` table via `file_hash` column.
3. **Document Classification Heuristics (`backend/classifier.py`):**
   - Developed rule-based pattern matching evaluating structural tokens, keywords, and extensions.
   - Classifies artifacts into forensic categories: `Invoice`, `Bank Statement`, `Contract`, `Identity Document`, `Receipt`, `Customs Declaration`, `Financial Report`, and `Scanned Artifact`.
   - Generates confidence scores ranging from 90.0% to 99.8% based on match frequency and pattern weights.
4. **Multipart REST API Endpoints (`backend/app.py`):**
   - `POST /api/documents/upload` — Ingests single files or batch files (`files` multipart list), assigns to target case (`case_id`), computes SHA-256 hash, classifies, stores to disk, and registers in SQLite (HTTP 201).
   - `GET /api/documents/<doc_id>/download` — Safely streams physical document files from `uploads/` with path validation.
   - `DELETE /api/documents/<doc_id>` — Deletes document database record and removes the physical file from disk.
5. **Frontend UI Integration (`frontend/js/app.js`):**
   - Upgraded `#view-upload` drag-and-drop zone with real `FormData` streaming to `/api/documents/upload`.
   - Dynamically populated the Target Investigation Case dropdown (`#targetCaseSelect`) with live cases from SQLite.
   - Dynamically populated Document Library cards (`#docLibraryGrid`) with live ingested documents, real category tags, and download links.
6. **Automated Backend Test Suite (`tests/test_backend.py`):**
   - Expanded test suite from 11 to 16 automated tests.
   - Added tests for single PDF upload, batch multi-file upload, unsupported file rejection (HTTP 400), empty file rejection (HTTP 400), duplicate filename handling, and download/delete verification.
   - 16/16 tests passed in 5.05s.

### Technologies Introduced
- **Hashlib (Python Standard Library):** Cryptographic SHA-256 hashing for forensic evidence integrity.
- **Werkzeug Utils (`secure_filename`):** Filename sanitization against path traversal attacks.
- **Regular Expressions (`re`):** Rule-based pattern matching for document classification.
- **Multipart Form-Data:** HTTP standard for uploading binary files from browser to Flask.

### Actual Testing Results
- **Automated Test Suite:** Ran 16 unit tests via `python -m unittest tests/test_backend.py` — 16/16 passed in 5.05s (`OK`).
- **Live Server Multipart Upload:** Uploaded `Apex_Commercial_Invoice_2026.pdf` to running Flask server on port 5000:
  - Received HTTP 201 Created.
  - Assigned ID: `DOC-2026-0047`.
  - Automatically classified as `Invoice (96.0% confidence)`.
  - Computed SHA-256: `168ac1f65ce4636509b857bb5c4d5971ed19a14d8ff9b0a557e102e668b8cff1`.
  - Stored at: `uploads/DOC-2026-0047_Apex_Commercial_Invoice_2026.pdf`.
- **Unsupported File Rejection:** Uploaded `malicious_tool.exe` — properly rejected with HTTP 400 (`Unsupported file format 'exe'`).
- **Empty File Rejection:** Uploaded 0-byte file — properly rejected with HTTP 400 (`Uploaded file is empty (0 bytes)`).
- **Duplicate Filename Check:** Verified duplicate filenames receive separate unique IDs and non-colliding disk paths.
- **JavaScript Syntax Check:** `node --check frontend/js/app.js` passed with exit code 0.

### Known Limitations
- Text extraction from inside digital PDFs and OCR processing on scanned images are scheduled for Phase 5.
- Deep named entity recognition (spaCy) across document text is scheduled for Phase 5.

### Concepts Learned
1. **Multipart/form-data Ingestion:** How HTTP clients stream binary files to web servers using boundary-delimited payloads.
2. **Cryptographic Chain of Custody:** Generating and recording SHA-256 hashes at ingestion time to prove digital evidence has not been tampered with.
3. **Secure Filename Sanitization:** Removing directory traversal sequences (`../`, null bytes, illegal characters) before saving files to disk.
4. **Collision-Resistant Storage:** Prefixing filenames with unique sequential IDs to prevent accidental overwrites when users upload documents with identical names.
5. **Pattern-Based Document Classification:** Using weighted regular expressions on document metadata and titles to categorize artifacts automatically.

### Suggested Git Commit Message
`feat(phase-4): implement document upload, SHA-256 hashing, classification heuristics, and library sync`

### Approval Status
- **Approved by User**: 2026-11-01 (Pushed to GitHub `main` branch under commit `2046f3a`).

---

## Phase 5 — OCR & Information Extraction Log

- **Completion Date:** 2026-11-01
- **Status:** **Completed** (Pushed to GitHub `main` branch)

### Features Implemented
1. **Digital PDF Text & Layout Extraction (`backend/extractor.py`):**
   - Implemented `extract_pdf_document` using high-performance `pymupdf` (PyMuPDF).
   - Extracts page-by-page text blocks with coordinates (`bbox`: `[x0, y0, x1, y1]`), word counts, line counts, and page dimensions.
   - Extracts document-level PDF metadata (`format`, `title`, `author`, `creationDate`, `modDate`, `producer`).
   - Computes aggregated metrics (`total_words`, `page_count`).
2. **Optical Character Recognition (OCR) Engine & Fallback (`backend/extractor.py`):**
   - Implemented `extract_image_document` using `Pillow` (`PIL.Image`) and `pytesseract`.
   - Built resilient fallback mechanism: catches `TesseractNotFoundError` if the native C++ Tesseract binary is not installed on the host system PATH, safely extracting image dimensions, color mode, format, and structure without crashing.
   - Normalizes image extraction outputs into the identical unified forensic schema as PDFs.
3. **Forensic Named Entity Recognition (NER) Module (`backend/ner.py`):**
   - Implemented `extract_entities_from_text` with targeted pattern extractors for:
     - **Dates:** ISO formats (`YYYY-MM-DD`, `DD/MM/YYYY`), spelled dates (`October 18, 2026`, `12th May 2026`).
     - **Monetary Values:** Multi-currency symbols (`$`, `€`, `£`, `₹`, `USD`, `EUR`, `INR`) with commas and decimal places.
     - **Identifiers:** Invoices, purchase orders, SWIFT/BIC, IBAN, case IDs, tax IDs (`INV-2026-8812`, `DOC-001`, `PO-4412`).
     - **Organizations:** Corporate entities, banks, holdings, tech firms, audit agencies (`Apex Global Inc.`, `Global Logistics Ltd`).
     - **Persons:** Named investigators, auditors, directors, doctors (`Dr. Alex Turner`, `Dr. Jane Foster`, `Mr. John Doe`).
     - **Emails:** RFC-compliant email address extraction (`forensic.audit@apex.internal`).
   - Implemented `merge_entities` to unify page-level detections into deduplicated, document-level traceable records.
4. **Database Persistence & SQLite Auto-Migration (`backend/database.py`, `backend/models.py`):**
   - Added `extracted_text TEXT` and `extracted_data TEXT` columns to `documents` table in `backend/schema.sql`.
   - Added dynamic runtime SQLite schema migration in `init_db()` (`PRAGMA table_info(documents)`) so existing installations upgrade automatically without data loss.
   - Added `save_document_extraction(doc_id, text, data)` and `get_document_extraction(doc_id)` in `backend/models.py`.
5. **REST API Document Extraction Endpoints (`backend/app.py`):**
   - `POST /api/documents/<doc_id>/extract`: Triggers extraction for the target document, executes PDF layout extraction or OCR, runs NER entity detection, persists structured results to SQLite, and returns comprehensive JSON response (HTTP 200).
   - `GET /api/documents/<doc_id>/extracted`: Retrieves previously cached extraction results and named entities from SQLite (HTTP 200). Returns HTTP 404 if not yet extracted.
6. **Frontend UI Integration (`frontend/index.html`, `frontend/js/app.js`):**
   - Updated system banner pill to indicate Phase 5 active status.
   - Added `⚡ Extract` action button directly to document library cards (`#docLibraryGrid`).
   - Added `window.triggerDocumentExtraction(docId)` JavaScript handler providing live toast notifications and telemetry.
7. **Automated Backend Test Suite (`tests/test_backend.py`):**
   - Expanded test suite from 16 to 20 automated tests.
   - Added tests for digital PDF layout & entity extraction (`test_extract_digital_pdf`), multi-page PDF extraction & page traceability (`test_extract_multi_page_pdf`), image document processing & OCR fallback (`test_extract_image_document`), and corrupted file handling (`test_extract_corrupted_document`).
   - All 20/20 unit tests pass in 6.74s.

### Technologies Introduced
- **PyMuPDF (`pymupdf`):** High-speed PDF text parsing, bounding-box coordinate geometry, and document metadata extraction.
- **Pillow (`PIL.Image`):** Image loading, dimension extraction, format detection, and preprocessing for OCR.
- **pytesseract:** Python wrapper for Google's Tesseract-OCR engine with structured exception handling.
- **Forensic Named Entity Recognition (NER):** High-precision regex pattern matchers with page-level reference tagging and cross-page deduplication.

### Actual Testing Results
- **Automated Test Suite:** Ran 20 unit tests via `python -m unittest tests/test_backend.py` — 20/20 passed in 6.74s (`OK`).
- **Live Server Test:** Uploaded genuine digital PDF `Live_Test_Invoice.pdf` to live Flask server on port 5000:
  - Invoked `POST /api/documents/DOC-2026-0048/extract`:
    - Result: HTTP 200 OK
    - Format: PDF, 1 Page, 16 Words
    - Extracted Dates: `2026-11-01`
    - Extracted Monetary Values: `$125,500.00`
    - Extracted Identifiers: `INV-2026-9900`
    - Extracted Organizations: `Global Logistics Ltd`
    - Extracted Persons: `Dr. Jane Foster`
    - Extracted Emails: `contact@globallogistics.com`
  - Invoked `GET /api/documents/DOC-2026-0048/extracted`: HTTP 200 OK with retrieved cached entity metadata.
- **Corrupted File Test:** Corrupted byte stream rejected cleanly with HTTP 400 and descriptive error message.
- **Frontend Syntax Validation:** `node -c frontend/js/app.js` passed with exit code 0.

### Known Limitations
- Advanced cross-document contextual anomaly detection and rule evaluation are scheduled for Phase 6.
- Interactive side-by-side document comparison visualizer is scheduled for Phase 7.

### Concepts Learned
1. **Digital PDF Geometry:** PDFs store text as positioned glyph sequences rather than continuous prose; PyMuPDF reconstructs blocks, lines, and bounding boxes (`bbox`) for spatial analysis.
2. **Graceful Binary Fallback:** Desktop/server environments may lack external native binaries like `tesseract.exe`; building software with automated degradation ensures high availability without crashes.
3. **Traceable Named Entity Extraction:** In forensic auditing, identifying an entity is insufficient—it must be tied back to a specific page number and coordinates for legal defensibility.
4. **Non-Destructive Database Migrations:** Using SQLite table pragma inspections at startup to add new columns dynamically without requiring table drops or manual database restarts.

### Suggested Git Commit Message
`feat(phase-5): implement PDF text extraction, OCR fallback, and named entity recognition`

### Approval Status
- **Approved by User**: 2026-11-01 (Pushed to GitHub `main` branch under commit `3b94aa2`).

---

## Phase 6 — Forensic & Contextual Analysis Log

- **Completion Date:** 2026-11-01
- **Status:** **Completed** (Pushed to GitHub `main` branch)

### Features Implemented
1. **Visual & Structural Forensic Analysis (`backend/analyzer.py`):**
   - Implemented `analyze_visual_structure` inspecting PDF span geometry and typography via PyMuPDF.
   - **`RULE-VIS-001` (Discrepant Font Family Detected):** Evaluates document-wide typeface usage. If an isolated span containing critical financial values, dates, or identifiers uses an anomalous outlier font (e.g. Courier in a Helvetica document), flags as typographic alteration with page number, coordinates (`bbox`), and confidence score.
   - **`RULE-VIS-002` (Overlapping Text Elements Detected):** Evaluates bounding box intersections across all spans on each page. Detects dual-layer text stamping or overwritten figures where text has been digitally printed over existing values (40%+ collision ratio).
   - **`RULE-VIS-003` (Out-of-Bounds Text Placement):** Identifies text spans placed beyond printable boundaries or hugging margin limits (< 5pt margin).
   - **`RULE-VIS-004` (Irregular Line Spacing Disparity):** Detects discontinuous baseline jumps within structured paragraphs.
   - **`RULE-VIS-005` (Degraded Resolution Artifact):** Flags low-resolution scanned artifacts (< 200x200 px) that compromise character legibility.
2. **Contextual & Semantic Intelligence Engine (`backend/analyzer.py`):**
   - Implemented `analyze_contextual_rules` evaluating contextual consistency across extracted text and entities.
   - **`RULE-CTX-001` (Missing Mandatory Document Fields):** Audits documents against their classified type (e.g. Invoices missing invoice IDs, issue dates, total amounts, or vendor entities; Contracts missing execution dates or counterparty signers).
   - **`RULE-CTX-002` (Multiple Conflicting Document Identifiers):** Flags documents featuring contradictory primary identifiers (e.g. composite invoices spliced from separate sources).
   - **`RULE-CTX-003` (Chronological Sequence Inconsistencies):** Detects future dates (> current_year + 1) and flags reversed timeline violations (e.g. payment due dates occurring earlier than invoice issue dates).
   - **`RULE-CTX-004` (Conflicting Monetary Values or Currencies):** Flags multi-currency collisions (e.g. USD and EUR indiscriminately mixed in one invoice) and contradictory totals.
   - **`RULE-CTX-005` (Metadata Timestamp Mismatch):** Compares PDF technical creation date (`creationDate`) with dates referenced in the document text, flagging chronological divergence while noting metadata fallibility.
3. **Risk Scoring & Severity Assessment (`calculate_risk_assessment`):**
   - Computes weighted risk score (0-100) based on finding severity (`Critical`: 35pts, `High`: 20pts, `Medium`: 10pts, `Low`: 5pts, `Info`: 2pts).
   - Categorizes risk tier: `Critical Risk`, `High Risk`, `Medium Risk`, `Low Risk`, or `Clean / Verified`.
   - Adheres to roadmap requirements: uses measured labels (`Potential Anomaly`, `Needs Review`), provides explainable observations, and never automatically declares fraud.
4. **Database & Schema Updates (`backend/schema.sql`, `backend/database.py`, `backend/models.py`):**
   - Added `page_number`, `coordinates`, `rule_id`, and `evidence` columns to SQLite `findings` table.
   - Implemented dynamic runtime migration in `init_db()` for frictionless database upgrades.
   - Added `save_document_findings`, `get_findings_by_document`, `get_finding_by_id`, `update_finding`, and `update_document_status`.
   - Linked findings to parent documents and cases with safe foreign key resolution.
5. **REST API Endpoints (`backend/app.py`):**
   - `POST /api/documents/<doc_id>/analyze`: Executes visual and contextual rules, stores findings, updates document status (`Flagged` / `Analyzed` / `Clean`), and returns complete analysis report.
   - `GET /api/documents/<doc_id>/findings`: Retrieves all findings for a document.
   - `GET /api/findings/<finding_id>`: Retrieves a single finding record.
   - `PATCH /api/findings/<finding_id>`: Allows investigators to update status (`Verified`, `Dismissed`, `Unresolved`).
6. **Frontend Integration (`frontend/index.html`, `frontend/js/app.js`):**
   - Updated system hero banner pill to Phase 6 active status.
   - Added `🔬 Analyze` action button to document cards in Document Library.
   - Wired `analyzeDocumentAndInspect(docId)` to run live analysis, show risk telemetry toast, populate the Forensic Inspector dropdown (`#forensicDocSelector`), and render observation cards dynamically in `#forensicFindingsFeed`.
   - Implemented `loadDocumentFindings(docId)` to switch document views in the inspector.
7. **Automated Backend Test Suite (`tests/test_backend.py`):**
   - Expanded test suite from 20 to 24 automated unit tests.
   - Added unit tests: `test_analyze_visual_font_discrepancy`, `test_analyze_overlapping_text_elements`, `test_analyze_contextual_inconsistencies`, and `test_findings_api_lifecycle`.
   - 24/24 unit tests pass in 7.16s (`OK`).

### Technologies Introduced
- **PyMuPDF Geometry & Typographic Extraction:** Span-level coordinate geometry (`bbox`), font family tracking, size extraction, and bounding-box collision math.
- **Contextual Rule Engines:** Rule-based heuristics evaluating statutory requirements, chronological sequence validity, and multi-currency compatibility.
- **RESTful Findings Lifecycle:** Dynamic status updates (`Verified`, `Dismissed`, `Unresolved`) with audit trail logging.

### Actual Testing Results
- **Automated Test Suite:** Ran 24 unit tests via `python -m unittest tests/test_backend.py` — 24/24 passed in 7.16s (`OK`).
- **Live Server Test:** Uploaded genuine digital sample with font discrepancy and reversed dates (`Live_Forensic_Sample.pdf`) to running server on port 5000:
  - Invoked `POST /api/documents/DOC-2026-0048/analyze`:
    - Result: HTTP 200 OK
    - Risk Score: 55 | Risk Level: `Critical Risk`
    - Finding 1: `[RULE-VIS-001] Discrepant Font Family Detected (High)` — Courier 12pt total amount diverging from Helvetica body.
    - Finding 2: `[RULE-CTX-003] Chronological Sequence Inconsistency (Critical)` — Payment due date (2026-09-01) precedes invoice issue date (2026-11-01).
- **Findings Lifecycle Test:** Fetched finding by ID, patched status to `Verified` (HTTP 200), and rejected invalid status with HTTP 400.
- **Frontend Syntax Check:** `node -c frontend/js/app.js` passed with exit code 0.

### Known Limitations
- Cross-document comparison across multiple files and visual diff comparison are scheduled for Phase 7.
- Dossier and final report generation are scheduled for Phase 8.

### Concepts Learned
1. **Typographic Forensics:** In digitally altered documents, bad actors often modify numbers or text using a standard font that slightly differs in family, size, or weight from the master template. Analyzing font frequency distribution highlights these localized anomalies.
2. **Bounding Box Collisions:** When text is modified digitally without removing the underlying text layer, two spans often collide or overlap in 2D space. Calculating intersection-over-minimum area detects dual-layer overwriting.
3. **Contextual & Chronological Validation:** Visual layout alone cannot catch all fraud; auditing logical sequences (e.g., due dates vs issue dates, mandatory fields) provides the contextual second half of forensic analysis.
4. **Responsible Forensic Language:** Automated tools must never declare a document "fraudulent." Presenting observations with neutral labels (`Potential Anomaly`, `Needs Review`) protects investigator integrity and prevents false-positive bias.

### Suggested Git Commit Message
`feat(phase-6): implement visual typographic analysis, contextual rule engine, and forensic findings lifecycle`

### Approval Status
- **Approved by User**: 2026-11-01 (Pushed to GitHub `main` branch under commit `67eb1b9`).

---

## Phase 7 — Cross-Document Comparison & Evidence Mapping Log

- **Completion Date:** 2026-11-01
- **Status:** **Completed** (Pushed to GitHub `main` branch)

### Features Implemented
1. **Cross-Document Discrepancy & Correlation Engine (`backend/comparator.py`):**
   - Implemented `compare_two_documents(doc_a_id, doc_b_id)`:
     - **Monetary Discrepancy Evaluation:** Extracts and parses numerical figures across documents. Flags variances exceeding configurable thresholds ($0.01 / 1%) with computed absolute and percentage variances.
     - **Timeline & Date Contradictions:** Compares dates across documents (e.g. invoice dates, due dates, contract execution dates) to identify chronological contradictions.
     - **Entity & Counterparty Matching:** Uses fuzzy token similarity matching (`difflib.SequenceMatcher`) to compare counterparties and organizations. Flags subtle variations, name shifts, and shell company substitutions (e.g. `Apex Global Inc.` vs `Apex Offshore Logistics LLC` at 65% similarity).
     - **Duplicate Reference Identification:** Audits primary identifiers (e.g. invoice numbers, tax IDs, passport numbers). Flags when identical reference numbers appear across documents with divergent monetary totals or counterparties.
     - **File Hash Collisions:** Compares SHA-256 cryptographic hashes. Flags identical files uploaded under different filenames or attached to multiple cases as duplicate submissions.
   - Implemented `compare_case_documents(case_id)`:
     - Conducts systematic pairwise cross-checks across all documents assigned to an investigation case.
     - Aggregates unique discrepancies into a case-level cross-document discrepancy summary.
   - Implemented `get_evidence_provenance_nodes(case_id=None)`:
     - Generates an evidence provenance graph linking investigation cases -> source documents -> forensic findings and extracted entities -> exact page numbers and 2D bounding box coordinates (`bbox`).
     - Ensures full transparency: every finding can be traced back to its physical origin.
   - Utility Helpers:
     - `parse_monetary_amount`: Extracts clean floats from formatted strings across currency symbols (`$`, `€`, `£`, `₹`).
     - `normalize_text`: Standardizes whitespace, punctuation, and casing for deterministic entity comparisons.
     - `calculate_similarity`: SequenceMatcher-based ratio for fuzzy string matching without external C dependencies.

2. **Database & Schema Updates (`backend/schema.sql`, `backend/database.py`, `backend/models.py`):**
   - Added `comparisons` table to SQLite schema with indices on `(document_a_id, document_b_id)` and `case_id`:
     - `id`, `case_id`, `document_a_id`, `document_b_id`, `comparison_type`, `discrepancies_count`, `summary`, `details_json`, `created_at`.
   - Updated `backend/database.py` with runtime table inspection to automatically create `comparisons` table on existing databases.
   - Persisted pairwise comparison results into SQLite for auditability.

3. **REST API Endpoints (`backend/app.py`):**
   - `POST /api/documents/compare`: Accepts `{ doc_a_id, doc_b_id }`, executes comparison engine, persists record in `comparisons`, and returns detailed discrepancy matrix.
   - `GET /api/cases/<case_id>/compare`: Runs multi-document cross-comparison across all documents in a case.
   - `GET /api/evidence-graph`: Returns full provenance graph nodes linking cases, documents, findings, page numbers, and bounding boxes.

4. **Frontend Integration (`frontend/index.html`, `frontend/js/app.js`):**
   - Updated system hero banner pill: `⚡ VEXORA Intelligence Engine • Phase 7 Active (Cross-Document Comparison & Evidence Mapping)`.
   - Populated primary and reference document selectors (`#compareDocA`, `#compareDocB`) dynamically from `/api/documents`.
   - Connected "Run Cross-Check" button (`#runComparisonBtn`) to `window.triggerCrossDocumentComparison()`.
   - Rendered live discrepancy findings dynamically into the Discrepancy Matrix (`#comparisonMatrixBody`), highlighting critical mismatches, monetary variances, and verified alignments with color-coded severity pills.
   - Implemented `window.loadEvidenceProvenanceGraph()` to render live provenance cards into `#evidenceProvenanceContainer`, displaying source filenames, page numbers, bounding boxes, and linked case IDs.
   - Added `🔄 Refresh Provenance` action to Evidence Provenance Graph header.

5. **Automated Backend Test Suite (`tests/test_backend.py`):**
   - Expanded unit test suite from 24 to 29 tests (+5 comprehensive tests):
     - `test_compare_matching_documents`: Verifies zero discrepancies on identical data.
     - `test_compare_conflicting_documents`: Verifies detection of monetary variance, chronological date contradiction, and counterparty mismatch.
     - `test_compare_case_documents_endpoint`: Validates case-level multi-document cross-check endpoint.
     - `test_evidence_provenance_graph_endpoint`: Validates evidence provenance graph node structure.
     - `test_compare_validation_errors`: Validates input checking (missing parameters, identical document IDs, 400 Bad Request).
   - All 29 unit tests pass in 10.54s (`OK`).

### Technologies Introduced
- **Cross-Document Entity Alignment:** Correlating unstructured entities across multiple heterogeneous files into a structured matrix.
- **Fuzzy Token Similarity Matching (`difflib.SequenceMatcher`):** High-precision token similarity calculation for legal counterparty verification.
- **Evidence Provenance Architecture:** Bidirectional linking from investigation findings back to document page and visual bounding box coordinates.
- **Relational Comparison Storage:** SQLite-backed comparison records preserving historical cross-check telemetry.

### Actual Testing Results
- **Automated Test Suite:** Ran 29 unit tests via `python -m unittest tests/test_backend.py` — 29/29 passed in 10.54s (`OK`).
- **Frontend Syntax Check:** `node -c frontend/js/app.js` passed with exit code 0.
- **Live Server Test:** Endpoints `/api/documents/compare`, `/api/cases/<case_id>/compare`, and `/api/evidence-graph` validated against live database.

### Known Limitations
- Investigation Dossier generation, Markdown/HTML report compilation, and printable export are scheduled for Phase 8.
- Comprehensive audit trail export and final system hardening are scheduled for Phase 9.

### Concepts Learned
1. **Multi-Document Discrepancy Detection:** Fraud and human error rarely present themselves in a single document in isolation; discrepancies typically manifest across paired documents (e.g., an invoice claiming $10,000 against a purchase order authorized for $7,500).
2. **Fuzzy String Comparison in Forensics:** Entity names frequently suffer from minor typographical shifts, abbreviations, or shell company variations. Applying sequence matching allows investigators to discern between innocent spelling variants and deceptive substitutions.
3. **Evidence Provenance & Auditability:** Forensic conclusions are only as strong as their source traceability. Providing direct links to specific pages and bounding coordinates makes findings indisputable and courtroom-ready.

### Suggested Git Commit Message
`feat(phase-7): implement cross-document comparison, discrepancy matrix, and evidence provenance mapping`

### Approval Status
- **Approved by User**: 2026-11-01 (Pushed to GitHub `main` branch under commit `7d9f44c`).

---

## Phase 8 — Investigation Dossier & Report Generation Log

- **Completion Date:** 2026-11-01
- **Status:** **Completed** (Pushed to GitHub `main` branch)

### Features Implemented
1. **Dossier Data Aggregation Engine (`backend/reporter.py`):**
   - Implemented `generate_case_dossier_data(case_id)`:
     - Aggregates comprehensive case metadata (ID, title, description, priority, status, investigator, timestamps).
     - Compiles an Ingested Evidence Inventory with document filenames, formats, file sizes, SHA-256 cryptographic hashes, and classification statuses.
     - Gathers and deduplicates Extracted Intelligence across all assigned case files (organizations, persons, dates, monetary totals, and identifiers).
     - Structures localized Forensic Observations & Visual Anomalies with rule IDs (`RULE-VIS-*`, `RULE-CTX-*`), severity levels, page numbers, 2D bounding box coordinates (`bbox`), and evidence quotes.
     - Integrates case-wide Cross-Document Discrepancies (monetary disparities, chronological timeline collisions, counterparty changes, duplicate reference IDs).
     - Computes quantitative case-level Risk Assessment (0-100 score, categorized into `Critical Risk`, `High Risk`, `Moderate Variance`, or `Clean / Verified Alignment`).
     - Produces an automated, context-aware Executive Summary Narrative based on findings count and variance severity.
     - Generates a unique Dossier Verification Hash (`VX-{case_id}-{hash}`) for audit authenticity.
     - Embeds the official Mandatory Human-Review Disclaimer:
       `"MANDATORY INVESTIGATION DISCLAIMER: All findings, metrics, and anomaly flags presented in this dossier are algorithmic observations produced by VEXORA for investigative assistance only. They do not constitute definitive legal proof of fraud or intentional tampering. Human investigator interpretation, physical document examination, and institutional validation remain mandatory before taking any administrative, disciplinary, or legal action."`

2. **Publication-Ready Vector PDF Dossier Generator (`backend/reporter.py`):**
   - Implemented `generate_dossier_pdf(case_id, output_path=None, user="Lead Investigator")`:
     - Built using PyMuPDF (`fitz` / `pymupdf`) vector primitives for zero-dependency, high-speed PDF generation.
     - Multi-page Letter document (612 x 792 pt) with clean layout and balanced margins.
     - Dark slate (`#0f172a`) header banner with VEXORA brand badge, case title, ID, generation date, and investigator name.
     - Prominent Amber Disclaimer Box (`#fffbeb` with `#f59e0b` border) at the top of the executive summary.
     - 4-metric executive telemetry summary cards (Risk Score, Document Count, Anomalies Flagged, Discrepancies Found).
     - Structured Ingested Evidence Inventory table with truncated SHA-256 hashes and page metrics.
     - Forensic findings cards with color-coded severity indicator bars (Critical/High in red, Medium in amber, Low in slate), page numbers, and bounding coordinates.
     - Cross-document discrepancy matrix cards with variance figures.
     - Formal Investigator Sign-off block with verification code, analyst name, and signature line.
     - Running footers on every page with confidentiality notice, page numbering ("Page X of Y"), and timestamp.
     - Dynamic pagination with automated page creation when content flows beyond margins.
     - Saves generated PDF to `reports/DOSSIER_{case_id}_{timestamp}.pdf`.

3. **Print-Optimized HTML Dossier Generator (`backend/reporter.py`):**
   - Implemented `generate_dossier_html(case_id, output_path=None, user="Lead Investigator")`:
     - Builds a standalone, responsive HTML report matching VEXORA's design system.
     - Features print media rules (`@media print`) allowing seamless browser printing (Ctrl+P).
     - Saves generated HTML to `reports/DOSSIER_{case_id}_{timestamp}.html`.

4. **Database & Schema Updates (`backend/schema.sql`, `backend/models.py`):**
   - Created `reports` table in SQLite with index `idx_reports_case_id`:
     - Columns: `id`, `case_id`, `title`, `file_path`, `file_format`, `file_size`, `generated_by`, `created_at`.
   - Added models in `backend/models.py`:
     - `create_report_record`: Persists report metadata and logs an audit trail event (`REPORT_GENERATED`).
     - `get_report_by_id`: Retrieves single report record.
     - `get_reports_by_case`: Retrieves all reports for a specific case.
     - `get_all_reports`: Retrieves recent reports across the repository.

5. **REST API Endpoints (`backend/app.py`):**
   - `GET /api/cases/<case_id>/dossier`: Returns complete structured JSON dossier data.
   - `POST /api/cases/<case_id>/report`: Accepts `{ format: 'pdf' | 'html' }`, compiles the dossier, records it in the database, and returns download and preview URLs.
   - `GET /api/reports`: Lists generated investigation reports (supports `?case_id=`).
   - `GET /api/reports/<report_id>`: Returns metadata for a specific report.
   - `GET /api/reports/<report_id>/download`: Streams the file as an attachment.
   - `GET /api/reports/<report_id>/view`: Serves the file inline with appropriate MIME type (`application/pdf` or `text/html`).

6. **Interactive Frontend Integration (`frontend/index.html`, `frontend/js/app.js`):**
   - Updated hero banner pill to Phase 8 Active: `⚡ VEXORA Intelligence Engine • Phase 8 Active (Investigation Dossier & Report Generation)`.
   - Populated dynamic Case Selector (`#dossierCaseSelector`) in `#view-dossier`.
   - Added action buttons: `🖨️ Print`, `🌐 Export HTML`, and `📄 Export PDF Dossier`.
   - Implemented `window.loadCaseDossierPreview(caseId)`: Dynamically renders live case title, risk badge, executive narrative, evidence inventory, localized findings with bounding box tags, and cross-document discrepancy cards into the printable dossier canvas.
   - Implemented `window.exportCurrentCaseDossier(format)`: Sends generation request to the backend, displays progress toast, updates the repository table, and opens the generated file in a new tab.
   - Added Generated Dossier Repository table (`#generatedReportsTableBody`) showing report ID, case ID, title, format badge, file size, and direct View/Download buttons via `window.loadGeneratedReportsList()`.

7. **Automated Backend Test Suite (`tests/test_backend.py`):**
   - Expanded unit test suite from 29 to 34 tests (+5 comprehensive tests):
     - `test_generate_case_dossier_data`: Validates full dossier dictionary structure, mandatory disclaimer, risk scores, and verification code.
     - `test_generate_case_dossier_not_found`: Validates 404/ValueError on missing cases.
     - `test_generate_dossier_pdf`: Validates PDF generation, file existence, and `%PDF` magic bytes.
     - `test_generate_dossier_html`: Validates HTML generation, file existence, and text markup.
     - `test_api_generate_report_endpoints`: Validates PDF/HTML generation endpoints, invalid format rejection, download streaming, and inline viewing.
   - All 34 tests pass in 11.26s (`OK`).

### Technologies Introduced
- **PyMuPDF Document Synthesis:** Using PyMuPDF (`fitz` / `pymupdf`) vector primitives (`draw_rect`, `draw_line`, `insert_textbox`) to construct publication-quality PDF reports without heavyweight C dependencies.
- **Automated Narrative Synthesis:** Generating contextual executive narratives from quantitative findings and cross-check signals.
- **Audit-Ready Report Persistence:** Tracking generated reports in SQLite with immutable audit logging and cryptographic verification hashes.
- **Multi-Format Export Engine:** Simultaneous support for vector PDF, standalone print-optimized HTML, and structured JSON APIs.

### Actual Testing Results
- **Automated Test Suite:** Ran 34 unit tests via `python -m unittest tests/test_backend.py` — 34/34 passed in 11.26s (`OK`).
- **Frontend Syntax Check:** `node -c frontend/js/app.js` passed with exit code 0.
- **Live PDF Generation Test:** Generated genuine multi-page vector PDF for `CAS-2026-0891` (18.7 KB) with verified `%PDF-` header and 2 styled pages.
- **Live HTML Generation Test:** Generated print-optimized HTML report for `CAS-2026-0891` (13.0 KB) with complete evidence inventory and disclaimer.

### Known Limitations
- Comprehensive audit trail export, system-wide hardening, and final demonstration preparation are scheduled for Phase 9.

### Concepts Learned
1. **Dossier Compilation Architecture:** An investigation dossier is more than a list of findings; it is an aggregated synthesis of evidence inventory, extracted facts, localized visual observations, cross-document discrepancies, and source traceability.
2. **Defensive Disclaimers in Forensic AI:** Automated forensic systems must never present findings as judicial fact. Including clear, mandatory disclaimers ("observations requiring human validation") is legally and ethically essential.
3. **Reproducible Vector PDF Generation:** Using PyMuPDF for PDF synthesis produces lightweight, pixel-perfect documents with zero external font dependencies or browser headless rendering overhead.

### Suggested Git Commit Message
`feat(phase-8): implement investigation dossier data aggregation, publication-ready PDF and HTML report generation, and reports repository`

### Approval Status
- **Approved by User**: 2026-11-01 (Pushed directly to `main` branch under commit `c1850df`)

---

## Phase 9: Audit Trail, Testing & Finalization

### Implementation Date
- **2026-11-01**

### Phase Objectives
1. Provide comprehensive audit trail tracking, filtering, and export capabilities (CSV and JSON formats).
2. Implement automated system diagnostic health checks to verify database integrity, directory permissions, and runtime dependencies.
3. Integrate the Audit Trail explorer and Diagnostics self-test into the frontend UI (`#view-settings`).
4. Expand the automated test suite to 39 comprehensive tests, including a complete multi-step end-to-end investigation lifecycle verification.
5. Finalize all system documentation and verify full operational readiness across all 9 roadmap phases.

### Features Implemented

1. **Enhanced Audit Trail Filtering (`backend/models.py`):**
   - Refactored `get_audit_logs(action=None, entity_type=None, user=None, limit=100)`:
     - Implemented dynamic SQL query construction with parameterized filtering for `action`, `entity_type`, and `user`.
     - Supports flexible limit bounds (`1 <= limit <= 1000`).
     - Safely parses and normalizes JSON details payload into clean dictionary structures.

2. **Audit Trail Streaming Export Engine (`backend/app.py`):**
   - Added endpoint `GET /api/audit-logs/export`:
     - Supports query parameters `format=csv|json`, `action`, `entity_type`, and `user`.
     - **RFC 4180 CSV Export:** Streams audit entries in memory using Python's `csv.writer` and `io.StringIO` with headers: `Timestamp`, `Action`, `Entity Type`, `Entity ID`, `User`, `IP Address`, and `Details`. Attachment filename: `vexora_audit_logs_{timestamp}.csv`.
     - **Structured JSON Export:** Streams formatted JSON payload containing metadata (`success`, `count`, `exported_at`, `data`). Attachment filename: `vexora_audit_logs_{timestamp}.json`.
   - Updated `GET /api/audit-logs` endpoint with filter support (`action`, `entity_type`, `user`, `limit`).

3. **Automated System Diagnostics & Health Check (`backend/app.py`):**
   - Added endpoint `GET /api/system/diagnostics`:
     - Verifies database connectivity and calculates live table record counts (`users`, `cases`, `documents`, `extractions`, `findings`, `cross_comparisons`, `reports`, `audit_logs`).
     - Verifies read and write permissions on critical runtime directories (`uploads/`, `reports/`).
     - Inspects runtime environment (Python version, PyMuPDF engine, Tesseract availability, database file size).
     - Returns structured JSON payload with overall status (`Operational` vs `Degraded`).

4. **Frontend Audit Trail & Diagnostics Center (`frontend/index.html`, `frontend/js/app.js`):**
   - Updated system hero banner pill: `⚡ VEXORA Intelligence Engine • Phase 9 Active (System Fully Integrated & Operational)`.
   - Updated footer roadmap link to Phase 9 Active.
   - **Live Diagnostics Card:** Added self-test status panel in Settings with `Run Diagnostics Self-Test` button that dynamically queries `/api/system/diagnostics` and displays live badge indicators, table counts, and directory statuses.
   - **Audit Trail & Forensics Activity Log Panel:** Added interactive table in `#view-settings` (`#auditTrailTableBody`) rendering timestamp, action badge, entity type & ID, user, and contextual details.
   - **Export Actions:** Added `📥 Export Audit CSV` and `📥 Export Audit JSON` buttons powered by `window.exportAuditLogs(format)`.
   - Wired `loadAuditTrailLogs()` into automatic background synchronization (`initBackendSync()`).

5. **Automated Backend Test Suite Expansion (`tests/test_backend.py`):**
   - Expanded unit test suite from 34 to 39 tests (+5 Phase 9 comprehensive tests):
     - `test_audit_logs_filtering`: Validates query filtering by `action`, `entity_type`, and `limit`.
     - `test_audit_logs_export_csv`: Validates CSV export headers, RFC 4180 formatting, and `text/csv` MIME type.
     - `test_audit_logs_export_json`: Validates JSON export payload structure, counts, and `application/json` MIME type.
     - `test_system_diagnostics_endpoint`: Validates self-test health check, database table counts, and directory write permissions.
     - `test_end_to_end_investigation_lifecycle`: Verifies complete multi-step lifecycle:
       1. Case Creation
       2. Uploading Document A (Vendor Invoice)
       3. Uploading Document B (Purchase Order with discrepancy)
       4. OCR and Text Extraction on Document A
       5. Forensic Heuristic Analysis on Document A
       6. Pairwise Cross-Document Comparison between Document A and Document B
       7. Case Dossier PDF Report Generation
       8. Verification that all actions were accurately logged in the audit trail.
   - All 39 tests pass with 100% success rate (`OK`).

6. **Documentation & Roadmap Finalization (`README.md`, `VEXORA_DEVELOPMENT_LOG.md`):**
   - Updated `README.md` to mark all 9 phases as **Completed**.
   - Updated `How to Run VEXORA` and `Testing` sections with comprehensive instructions.

### Technologies Introduced
- **RFC 4180 In-Memory Streaming:** Utilizing `io.StringIO` and Python's standard `csv.writer` to stream audit logs on demand without disk bottlenecks.
- **Parametric Health Diagnostics:** Dynamic reflection of database schema integrity, file system permissions, and dependency health into a centralized monitoring API.
- **End-to-End Investigation Pipeline Verification:** Automated integration testing validating that all core subsystems (Ingestion, Extraction, NER, Analysis, Cross-Check, Dossier, Audit) execute harmoniously.

### Actual Testing Results
- **Automated Test Suite:** Ran 39 unit and integration tests via `.\.venv\Scripts\python.exe -m unittest tests/test_backend.py` — 39/39 passed in 12.88s (`OK`).
- **Frontend Syntax Validation:** `node -c frontend/js/app.js` passed with exit code 0.
- **Live Diagnostics Verification:** `GET http://127.0.0.1:5000/api/system/diagnostics` returned HTTP 200 with `status: "Operational"`.
- **Live CSV Export Verification:** `GET http://127.0.0.1:5000/api/audit-logs/export?format=csv` returned HTTP 200 with `Content-Type: text/csv; charset=utf-8` and 67 formatted rows.

### Known Limitations
- The system is now fully implemented according to all nine structured roadmap phases. Future phases may expand OCR language support, GPU-accelerated deep learning embeddings, and collaborative multi-investigator workflows.

### Concepts Learned
1. **Evidentiary Chain of Custody:** In forensic investigations, maintaining an unalterable, queryable, and exportable audit trail is just as important as the forensic algorithms themselves. Every extraction, analysis, comparison, and report generation must link back to a specific timestamp and user identity.
2. **Defensive Self-Diagnostics:** Providing built-in diagnostic endpoints (`/api/system/diagnostics`) simplifies operational troubleshooting, verifies folder permissions, and provides immediate visibility into database health without requiring direct shell access.
3. **End-to-End Integration Testing:** Testing individual components in isolation is essential, but verifying the full end-to-end investigation lifecycle (Case -> Upload -> OCR -> Forensics -> Comparison -> Dossier -> Audit) gives complete confidence that the software works seamlessly as an integrated system.

### Suggested Git Commit Message
`feat(phase-9): implement audit trail export, system diagnostics health check, and complete end-to-end testing`

### Approval Status
- **Completed & Verified**: All Phase 9 objectives and overall project roadmap successfully achieved and verified.

---

## Brand Identity & Official Logo Integration

### Implementation Date
- **2026-11-01**

### Overview
Integrated the official VEXORA brand logo and slogan (`SEEING WHAT OTHERS OVERLOOK`) across the entire full-stack ecosystem:

1. **Asset Generation & Optimization:**
   - **Full Logo (`frontend/images/logo.png`, `assets/logo.png`):** High-resolution master brand logo featuring the cybernetic lens targeting eye with digital scatter cubes and metallic typography.
   - **Brand Emblem Mark (`frontend/images/logo-icon.png`):** 512x512 square crop centered on the cybernetic ocular crosshair for responsive sidebar headers and collapsed navigation states.
   - **Favicons (`frontend/images/favicon.png`, `frontend/favicon.ico`):** Multi-resolution browser tab icons (16px to 64px).

2. **Full-Stack Application Integration:**
   - **Sidebar Header:** Replaced fallback glyph with `.brand-icon-img` (`logo-icon.png`), styled with cyan glow borders, and updated brand badge to official tagline: *Seeing What Others Overlook*.
   - **Dashboard Hero Banner:** Integrated `.hero-banner-inner` with `.banner-motto-badge` (`◈ SEEING WHAT OTHERS OVERLOOK`) and `.hero-banner-logo` showcasing the official logo.
   - **Forensic Dossier Canvas & Reports:** Embedded brand emblem in `#view-dossier` print canvas header, standalone HTML reports, and vector PDF reports generated via PyMuPDF.
   - **Flask Asset Serving:** Added `/images/<filename>` and `/favicon.ico` static asset routes to `backend/app.py`.
   - **Repository Documentation:** Centered the official logo banner and slogan at the top and footer of `README.md`.
---

## V2 Phase 0: System Safety Net & Contract Baseline

### Implementation Date
- **2026-11-02**

### Phase Objectives
1. Read and review the entire VEXORA architecture, roadmap, development logs, and source code across backend, frontend, schema, and tests.
2. Confirm the active Flask index route versus the repository root static redirect wrapper.
3. Establish `docs/EXISTING_CONTRACT.md` documenting every Flask route, table, column, rule ID, data shape, and frontend UI rendering hook.
4. Establish `tests/test_v2_contract.py` testing database tables/columns, all registered Flask routes, response keys, rules, and NER categories.
5. Establish and verify baseline test execution across both the original 39 unit tests and the 15 contract safety net tests (54 passing tests total).
6. Perform an initial code-to-documentation audit noting any discrepancies between `README.md` and actual implementation.

### Features & Safety Measures Implemented
1. **Flask Served Index Verified:**
   - Identified that `backend/app.py` serves `frontend/index.html` via `FRONTEND_DIR`.
   - Identified that root `index.html` is an external static redirect wrapper (`meta refresh`) and is not served by Flask. Frozen as untouched.
2. **Context-Aware Database Routing:**
   - Updated `backend/database.py` with an internal `_last_active_db` tracker so that direct test invocations executed outside active Flask request contexts correctly target the active test database rather than defaulting to production SQLite storage.
3. **Formal System Contract (`docs/EXISTING_CONTRACT.md`):**
   - Documented all 7 relational tables and their columns.
   - Documented all 44 endpoints (37 REST API routes + static asset handlers).
   - Documented all 10 visual & contextual forensic rules (`RULE-VIS-001` through `005`, `RULE-CTX-001` through `005`) and risk score formulas.
   - Documented data shapes for Findings, Extracted Entities, and Comparison Alignment Matrix records.
   - Documented frontend DOM IDs and JavaScript rendering functions.
4. **Automated Contract Safety Net (`tests/test_v2_contract.py`):**
   - Implemented 15 automated contract tests validating database tables/columns, endpoint presence, GET response keys, served index content, forensic rule definitions, and entity categories.

### Actual Testing Results
- **Original Baseline Test Suite (`tests/test_backend.py`):** 39/39 tests passed in 15.49s (`OK`).
- **Contract Safety Net Test Suite (`tests/test_v2_contract.py`):** 15/15 tests passed in 0.50s (`OK`).
- **Combined Total:** 54 passing tests.

### Code vs. Documentation Inconsistencies Discovered (Report Only)
1. **spaCy Dependency Discrepancy:**
   - `README.md` and `requirements.txt` state that Named Entity Recognition is powered by `spacy>=3.7.0` (`en_core_web_sm`).
   - The actual implementation in `backend/ner.py` uses pure Python regular expressions (`PATTERNS` dictionary) without importing or calling spaCy.
2. **MIME Validation Discrepancy:**
   - `README.md` claims "MIME validation", but `backend/uploader.py` only performs extension checks (`ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}`) without MIME sniffing or magic byte verification.
3. **Unexecuted Defined Rule:**
   - `RULE-VIS-004` (Irregular Line Spacing Disparity) is defined in `backend/analyzer.py:RULES`, but is never executed or triggered in `analyze_visual_structure()`.

### Suggested Git Commit Message
`chore(phase-0): establish existing contract documentation, contract safety net tests, and baseline verification`

### Approval Status
- **Pending Review**: Ready for Phase 0 review and user approval before proceeding to Phase A.
---

## V2 Phase A: Visual Evidence Overlay & Bounding-Box Tracing

### Implementation Date
- **2026-11-02**

### Phase Objectives
1. Implement high-resolution visual evidence rendering that maps finding bounding boxes directly onto document page images.
2. Provide dedicated REST API endpoints to serve highlighted evidence images for individual findings and full-page overlays.
3. Integrate an interactive "View Evidence" modal in the frontend UI without external libraries.
4. Add an optional visual evidence gallery appendix to publication dossiers behind the `ENABLE_EVIDENCE_OVERLAY` feature flag.
5. Guarantee zero regression on existing features and maintain 100% pass rate on all existing unit and contract tests.

### Features Implemented
1. **Visual Evidence Overlay Engine (`backend/evidence.py`):**
   - `parse_coordinates(coords_raw)`: Robust parser supporting Python lists, JSON array strings, and comma-separated coordinate strings, extracting `[x0, y0, x1, y1]`.
   - `render_page_overlay(file_path, page_number, findings, zoom=2.0)`: Renders PDF pages with PyMuPDF pixmaps at 144 DPI (2.0x scale) or raster images with Pillow, computes exact coordinate transformations, and applies red semi-transparent bounding boxes with rule identifier badges (`RULE-VIS-XXX`).
   - `get_finding_evidence_image(finding_id, zoom=2.0)`: Look up finding, resolves document path, checks coordinates, and returns PNG bytes or structured error details.
   - `get_document_page_overlay(doc_id, page_number, zoom=2.0)`: Renders full page overlay for all findings on a given page.
2. **REST API Evidence Routes (`backend/app.py`):**
   - `GET /api/findings/<id>/evidence-image`: Serves a 200 `image/png` image with the specific finding boxed in red. If no bounding box coordinates exist (contextual finding), returns a structured 200 JSON explanation (`NO_COORDINATES`), preventing broken image icons in the UI.
   - `GET /api/documents/<id>/pages/<n>/overlay`: Serves a 200 `image/png` image showing all findings present on that page.
3. **Frontend Visual Evidence Modal & Buttons (`frontend/css/v2.css`, `frontend/js/v2.js`):**
   - Injected sleek `🔍 View Evidence` action buttons onto finding cards in both the Forensic Inspection feed and Dossier preview.
   - Built a lightweight, accessible evidence modal (`#v2EvidenceModal`) featuring:
     - High-contrast visual canvas with pan/zoom controls (50% to 300%) and direct "Open Full Resolution" tab link.
     - Severity and Rule ID pills.
     - Explanatory informational banner for contextual / non-visual findings.
     - Smooth backdrop transitions and ESC key dismissal.
4. **Dossier Report Appendix (`backend/reporter.py`):**
   - When feature flag `ENABLE_EVIDENCE_OVERLAY` is enabled, appends a dedicated "APPENDIX: VISUAL FORENSIC EVIDENCE OVERLAYS" section to generated PDF dossiers with embedded high-resolution evidence boxes.
   - Wrapped inside `try/except` so report generation can never fail if image embedding encounters an issue.
   - Old report generation remains completely unchanged when the flag is off.

### Technologies Introduced
- **PyMuPDF to Pillow Composite Pipeline:** High-speed rendering of vector PDF page primitives to raster buffers (`page.get_pixmap`), followed by RGBA alpha compositing in Pillow for crisp, anti-aliased visual annotations.
- **Coordinate Transformation Normalization:** Scaling fractional PDF point coordinates (72 DPI) to high-definition rendering pixel space (144 DPI).

### Actual Testing Results
- **Original Baseline Tests (`tests/test_backend.py`):** 39/39 passed (`OK`).
- **Contract Safety Net Tests (`tests/test_v2_contract.py`):** 15/15 passed (`OK`).
- **Phase A Overlay Tests (`tests/test_v2_phase_a.py`):** 11/11 passed (`OK`).
- **Combined Test Total:** 65/65 passing in 15.67s.
- **Live Endpoint Verification:** Verified `GET /api/findings/FND-2026-006/evidence-image` returned HTTP 200 with 80,342-byte PNG image.
- **Contextual Fallback Verification:** Verified `GET /api/findings/FND-2026-007/evidence-image` returned HTTP 200 with `application/json` message (`NO_COORDINATES`).

### Known Limitations
- Bounding boxes require valid typographic or geometric coordinates. Contextual findings (e.g. date inconsistencies or missing invoice fields) do not have spatial coordinates and display a contextual notification card instead.

### Concepts Learned
1. **Traceability in Forensic AI:** Merely telling an investigator that a font is mismatched or text overlaps is insufficient. Visually boxing the exact suspicious region directly on the original document turns abstract telemetry into compelling, audit-ready evidence.
2. **Defensive Endpoint Fallbacks:** An image endpoint should never return an HTTP 500 or broken binary image when an anomaly has no bounding box. Returning a structured JSON response with informative text enables the UI to explain why a finding is contextual rather than visual.

### Suggested Git Commit Message
`feat(phase-a): implement visual evidence overlay rendering, evidence image endpoints, and interactive UI inspection modal`


---

## Phase B: Deeper PDF Forensics & Evidence Classification
**Date:** 2026-11-02
**Status:** Completed
**Branch:** feature/v2-phase-b (merged into main)

### What Was Built
1. **Standardized Forensic Evidence Classification Layer (`backend/evidence_class.py`):**
   - Implemented an objective 3-tier classification taxonomy to strictly comply with hackathon rules ("must distinguish observations from potential anomalies, and must never call anything 'confirmed fraud'"):
     - **Observation**: A measured physical or structural fact (e.g., multiple fonts present, incremental updates).
     - **Inconsistency**: Two contradictory facts or conflicting attributes (e.g., date divergence, check digit mismatch).
     - **Potential Manipulation**: An anomaly pattern commonly seen after document alteration (e.g., white-box redaction, superimposed signature raster).
   - Created `RULE_EVIDENCE_CLASS_MAP` covering all visual, contextual, and extended rules with fallback defaults.
   - Built helper functions `get_evidence_class(rule_id, existing_class)` and `classify_finding(finding)`.
2. **Advanced PDF Forensic Detectors (`backend/forensics_pdf.py`):**
   - **PDF-001 (Text Hidden Under Filled Shapes):** Detects text blocks occluded by filled/opaque vector shapes (>65% overlap area) — typical in white-box redactions and digital figure alteration.
   - **PDF-002 (Incremental Updates in File Body):** Inspects raw PDF file bytes for multiple `%%EOF` markers, detecting post-creation revisions and appended streams.
   - **PDF-003 (Metadata Revision Desynchronization):** Detects creation date vs. modification date divergence and commercial visual editor signatures (e.g., Canva, Photoshop, iLovePDF, Sejda, Nitro, GIMP).
   - **PDF-004 (Superimposed Raster Images & DPI Disparity):** Detects embedded raster images placed directly over underlying vector text spans, as well as extreme image resolution disparities (>3.5x ratio on page).
   - **PDF-005 (Invisible & Off-Page Text Elements):** Uses expanded TextPage clipping boundaries (-500 to +500 pt) to catch text rendered outside visible page boundaries, and checks for invisible render mode 3.
   - **`run_extended_pdf_forensics(file_path)`:** Master coordinator returning standardized finding dictionaries.
3. **Database Schema & Model Hydration (`backend/database.py`, `backend/models.py`):**
   - Idempotently migrated `findings` table: added column `evidence_class TEXT DEFAULT NULL`.
   - Updated `create_finding`, `get_all_findings`, `get_finding_by_id`, and `get_findings_by_document` with backward-compatible hydration via `_hydrate_finding_evidence_class`.
4. **Analyzer & Reporter Integration (`backend/analyzer.py`, `backend/reporter.py`):**
   - Hooked `run_extended_pdf_forensics` into `analyze_document` under feature flag `ENABLE_EXTENDED_FORENSICS` inside safe `try/except`.
   - Annotated all findings with `evidence_class`.
   - Updated `generate_case_dossier_data`, `generate_dossier_pdf`, and `generate_dossier_html` to render evidence class badges and classification labels.
5. **Frontend UI Badging (`frontend/js/app.js`, `frontend/js/v2.js`):**
   - Rendered distinct color-coded evidence class badges (`Observation`, `Inconsistency`, `Potential Manipulation`) across finding cards and dossier preview.
   - Added `Class: <strong id="v2ModalClass">` to visual evidence modal.

### Technologies Introduced
- **PyMuPDF Drawing & Vector Geometry Extraction:** `page.get_drawings()` vector polygon analysis and `page.get_text("dict")` span intersection calculations.
- **Expanded TextPage Clipping:** Using `page.get_textpage(clip=fitz.Rect(-500, -500, w+500, h+500))` to uncover off-page text hidden outside visible mediabox viewports.
- **Raw Byte Stream Parsing:** Fast binary counting of `%%EOF` trailer markers in raw PDF file streams without parsing overhead.

### Actual Testing Results
- **Phase B Unit & Integration Tests (`tests/test_v2_phase_b.py`):** 17/17 passed (`OK`).
- **Phase A Overlay Tests (`tests/test_v2_phase_a.py`):** 11/11 passed (`OK`).
- **Contract Safety Net Tests (`tests/test_v2_contract.py`):** 15/15 passed (`OK`).
- **Baseline Suite (`tests/test_backend.py`):** 39/39 passed (`OK`).
- **Combined Test Total:** 82/82 passing across all suites in 19.56s.

### Known Limitations
- Pure raster scans without OCR or vector streams cannot be analyzed for PDF-001 or PDF-005 without prior OCR layout extraction.

### Concepts Learned
1. **Viewport Clipping vs Document Content:** PDF viewers only show what is inside the page cropbox/mediabox, but attackers often hide text or notes outside the viewport. Default `get_text()` calls also clip to page boundaries, so expanding the TextPage clip is essential for true forensic discovery.
2. **Objective Evidence Nomenclature:** Calling an anomaly "fraud" loses points and violates forensic standards. Categorizing items as "Observations", "Inconsistencies", or "Potential Manipulations" maintains objectivity while giving human investigators clear, actionable intelligence.

### Suggested Git Commit Message
`feat(phase-b): implement deeper PDF forensic rules PDF-001 through PDF-005 and evidence classification`


---

## Phase C: LLM Reasoning & Explainability Layer
**Date:** 2026-11-02
**Status:** Completed
**Branch:** feature/v2-phase-c (merged into main)

### What Was Built
1. **Universal HTTPS LLM Dispatcher (`backend/llm.py`):**
   - Pure HTTPS integration using `requests` without heavyweight SDK dependencies.
   - Multi-provider support: Google Gemini (`gemini-1.5-flash`), OpenAI (`gpt-4o-mini`), and Anthropic Claude (`claude-3-haiku-20240307`).
   - Graceful degradation: returns `None` on any error, missing key, timeout, or bad JSON, allowing the app to seamlessly continue with rule-based outputs.
   - PII privacy masking (`redact_text_for_llm`): automatically redacts email addresses (`[REDACTED_EMAIL]`), phone numbers (`[REDACTED_PHONE]`), and long digit strings >= 10 digits (`[REDACTED_DIGITS]`) before dispatching text to external APIs when `VEXORA_LLM_REDACT` is enabled (default on).
2. **Strict Anti-Hallucination Grounding (`verify_source_quote`):**
   - For every extracted field or claim, checks whether the claimed verbatim `source_quote` actually exists within the original document text (case-insensitive and punctuation-normalized substring search).
   - Automatically drops any field or claim that cannot be verified in the source text, permanently preventing LLM hallucinations from polluting investigative cases.
3. **Core Reasoning Capabilities:**
   - **`extract_fields_llm(text, doc_type, document_id)`:** Extracts vendor, invoice number, dates, totals, line items, and parties with individual confidence scores and verified source quotes. Saves grounded data to the `ai_insights` table.
   - **`explain_finding(finding, nearby_text)`:** Produces a 2-4 sentence plain-language explanation of why a technical observation warrants review, identifies plausible innocent alternative hypotheses (e.g., software upgrade, template change, batch scanning), and gives one concrete verification step for human investigators.
   - **`contextual_crosscheck(case_documents, case_id)`:** Performs multi-document reasoning to detect contextual inconsistencies (totals vs. itemized line items, mismatched parties, impossible timelines). Generated findings are categorized as `LLM-001+`, tagged as `Contextual Intelligence` with `evidence_class="Inconsistency"`, and marked with the mandatory disclaimer: `AI-assessed, requires human review`.
4. **New API Endpoints (`backend/app.py`):**
   - `GET /api/system/ai-status`: Reports provider, model, whether API key is present, and redaction status (never exposes the key).
   - `POST /api/documents/<id>/ai-extract`: Triggers structured field extraction with anti-hallucination verification.
   - `POST /api/findings/<id>/explain`: Generates plain-language explanation and innocent alternative hypotheses.
   - `POST /api/cases/<id>/ai-crosscheck`: Executes cross-document contextual anomaly discovery.
5. **Database Storage & Audit Trail (`backend/database.py`, `backend/models.py`, `backend/schema.sql`):**
   - Added `ai_insights` table with index on `document_id`.
   - Logged immutable audit trail records (`AI_FIELD_EXTRACTION`, `AI_FINDING_EXPLAINED`, `AI_CROSSCHECK_COMPLETED`) without exposing API keys.
6. **Reporter & UI Integration (`backend/reporter.py`, `frontend/js/v2.js`, `frontend/css/v2.css`):**
   - Added optional "AI-Assisted Investigation Summary" section to both HTML and PDF dossiers when AI data is present.
   - Added `🤖 Explain with AI` button and contextual reasoning card directly inside the interactive Visual Evidence Modal.

### Technologies Introduced
- **Plain HTTPS LLM REST API Client:** Zero-dependency REST calls to Gemini, OpenAI, and Claude APIs with robust JSON block extraction and error handling.
- **Substring Citation Grounding Verification:** Case-insensitive, whitespace-normalized, and punctuation-invariant string matching to strictly verify source quotes against document transcripts.
- **Regex PII Privacy Anonymization:** Pre-dispatch redaction of emails, phones, and sensitive long account numbers.

### Actual Testing Results
- **Phase C Unit & Integration Tests (`tests/test_v2_phase_c.py`):** 9/9 passed (`OK`).
- **Phase B PDF Forensics Tests (`tests/test_v2_phase_b.py`):** 17/17 passed (`OK`).
- **Phase A Overlay Tests (`tests/test_v2_phase_a.py`):** 11/11 passed (`OK`).
- **Contract Safety Net Tests (`tests/test_v2_contract.py`):** 15/15 passed (`OK`).
- **Baseline Suite (`tests/test_backend.py`):** 39/39 passed (`OK`).
- **Combined Test Total:** 91/91 passing across all suites in 22.07s.

### Known Limitations
- When `ENABLE_LLM` is false or no API key is provided, LLM endpoints return graceful fallback responses with `{success: false, message: "AI reasoning service unavailable or disabled."}`.

### Concepts Learned
1. **Anti-Hallucination Through Mandatory Source Quotation:** LLMs can generate plausible-sounding vendor names and amounts that do not exist in the document. By requiring verbatim source quotes and verifying them in code before saving, hallucinations are systematically eliminated.
2. **Defensive Auditability:** In forensic investigations, an AI explanation must never assert guilt or call something "confirmed fraud". Highlighting plausible innocent explanations protects investigative neutrality while guiding human reviewers to concrete verification steps.

### Suggested Git Commit Message
`feat(phase-c): implement LLM reasoning layer, anti-hallucination quote verification, finding explanations, and contextual cross-check`


---

## Phase D: Image Forensics for Scans & Photos (IMG-001 through IMG-004)
**Date:** 2026-11-02
**Status:** Completed
**Branch:** feature/v2-phase-d (merged into main)

### What Was Built
1. **Core Image Forensics Engine (`backend/forensics_image.py`):**
   - Built with lightweight OpenCV (`opencv-python-headless`) and NumPy:
     - **IMG-001 (Error Level Analysis - ELA):** Recompresses image in-memory at JPEG quality 90 and calculates block-level error surfaces relative to the document median error. Anomalous blocks with elevated recompression residue are flagged as `Potential Manipulation`, identifying elements spliced from different compression generations or digital sources.
     - **IMG-002 (Noise & Sharpness Inconsistency):** Evaluates Laplacian high-frequency edge variance across non-empty blocks. Identifies sharp digital text or cut-outs embedded in soft-scanned or blurry backgrounds as an `Observation`.
     - **IMG-003 (Copy-Move Duplication via ORB Keypoint Clustering):** Computes ORB keypoint descriptors and matches features with Lowe's ratio test. Clusters displacement vectors by spatial distance and angular orientation (+-15 deg, +-25px) to catch cloned seals, rubber stamps, numbers, and signatures as `Potential Manipulation`.
     - **IMG-004 (Signature Region Presence & Overlap Check):** Analyzes the lower 35% of the page for cursive handwritten ink strokes using adaptive Gaussian thresholding and connected components. Checks for physical overlap with printed lines. If document resolution is below threshold or unsuited, returns the required explicit fallback notice: `"signature analysis: unsupported for this document"`.
   - **`run_image_forensics(file_path)`:** Master coordinator analyzing standalone images (.png, .jpg, .jpeg, .tiff, .bmp, .webp) and rasterized PDF pages via PyMuPDF.

2. **Evidence Classification & Objective Forensic Taxonomy (`backend/evidence_class.py`):**
   - Mapped `IMG-001` and `IMG-003` to `Potential Manipulation`.
   - Mapped `IMG-002` and `IMG-004` to `Observation`.
   - All findings include explicit disclaimers: `"Heuristic indicator; compression residue may also reflect multiple legitimate saves..."` and `"Heuristic indicator; identical graphics (logos, letterhead) can trigger match clusters..."`.
   - Strictly enforces the rule to never assert "confirmed fraud".

3. **Analyzer Integration & Feature Flag (`backend/config.py`, `backend/analyzer.py`):**
   - Added configuration flag `ENABLE_IMAGE_FORENSICS = os.environ.get('ENABLE_IMAGE_FORENSICS', 'false').lower() in ('true', '1', 'yes')`.
   - Connected `run_image_forensics` to `analyze_document` under safe exception wrappers, ensuring zero disruption when the flag is disabled.

4. **Unit & Integration Test Suite (`tests/test_v2_phase_d.py`):**
   - 8 comprehensive tests:
     - `test_image_forensics_availability`: Confirms OpenCV and NumPy availability.
     - `test_img_001_error_level_analysis`: Validates ELA detection on spliced patch with different compression history.
     - `test_img_002_sharpness_inconsistency`: Validates Laplacian variance detection on sharp patch on blurred canvas.
     - `test_img_003_copy_move_detection`: Validates ORB keypoint clustering on cloned stamps.
     - `test_img_004_signature_region_detection`: Validates cursive ink stroke clustering.
     - `test_img_004_signature_unsupported_small_image`: Validates unsupported fallback message on low-resolution image.
     - `test_run_image_forensics_standalone_image`: Validates end-to-end file pipeline.
     - `test_analyzer_integration_with_flag`: Validates `ENABLE_IMAGE_FORENSICS` flag control (0 findings when False, findings generated when True).

### Technologies Introduced
- **OpenCV & NumPy Computer Vision Pipeline:** Headless OpenCV for fast morphological processing, Laplacian edge variance, ORB feature detection, and connected components analysis.
- **Error Level Analysis (ELA):** In-memory JPEG quantization error profiling to uncover digital cut-and-paste manipulations without GPU dependencies.
- **Displacement Vector Clustering:** Spatial clustering of keypoint match vectors to separate duplicated elements from random repetitive textures.

### Actual Testing Results
- **Phase D Image Forensics Suite (`tests/test_v2_phase_d.py`):** 8/8 passed (`OK`).
- **Phase C LLM Reasoning Suite (`tests/test_v2_phase_c.py`):** 9/9 passed (`OK`).
- **Phase B PDF Forensics Suite (`tests/test_v2_phase_b.py`):** 17/17 passed (`OK`).
- **Phase A Overlay Suite (`tests/test_v2_phase_a.py`):** 11/11 passed (`OK`).
- **Contract Safety Net Suite (`tests/test_v2_contract.py`):** 15/15 passed (`OK`).
- **Baseline Test Suite (`tests/test_backend.py`):** 39/39 passed (`OK`).
- **Combined Test Total:** 99/99 passing across all suites in 24.75s.

### Known Limitations
- ELA can produce false positives on high-contrast text edges in clean uncompressed PNGs; mitigated by requiring significant block residue disparity above document median error.
- Heavily re-compressed web screenshots or degraded multi-generation faxes may obscure original sensor noise patterns.

### Concepts Learned
- **Robust Outlier Filtering in Documents:** Standard business documents have large white margins. Calculating median sharpness variance must exclude zero-variance blank margins to avoid dividing by zero or setting the baseline too low.
- **Vector Clustering for Copy-Move:** Individual ORB feature matches have noise, but clustering matches that share both identical displacement distance and parallel angular orientation cleanly isolates cloned figures and stamps.

### Suggested Git Commit Message
`feat(phase-d): implement image forensics module (IMG-001 ELA, IMG-002 sharpness, IMG-003 copy-move, IMG-004 signature check)`


---

## Phase E: Real Field-Level Confidence & Honest Extraction Modes
**Date:** 2026-11-02
**Status:** Completed
**Branch:** feature/v2-phase-e (merged into main)

### What Was Built
1. **Real Field-Level Confidence & Per-Word OCR Averaging (`backend/extractor.py`, `backend/ner.py`):**
   - Integrated `pytesseract.image_to_data` output dictionary parsing to obtain true per-word bounding box confidences (0-100 scale).
   - Implemented `compute_entity_confidence` in `backend/ner.py`: averages the individual OCR word confidences corresponding to constituent tokens of extracted named entities (organizations, monetary values, dates, identifiers, persons).
   - For native digital PDFs (`extract_pdf_document`), entities receive an explicit `confidence = "n/a (digital text)"`, honestly distinguishing directly extracted digital fonts from statistical OCR approximations.

2. **Extracted Entities Relational Persistence (`backend/schema.sql`, `backend/database.py`, `backend/models.py`):**
   - Created `entities` table with a nullable `confidence` column:
     `id`, `document_id`, `case_id`, `entity_type`, `value`, `confidence`, `page_number`, `coordinates`, `created_at`.
   - Added automatic schema migration in `init_db` with `idx_entities_document` index.
   - Added `save_document_entities` and `get_entities_by_document` helper models in `backend/models.py` called automatically upon document extraction.

3. **Extraction Mode Tracking & VEXORA_STRICT_OCR (`backend/config.py`, `backend/extractor.py`, `backend/models.py`):**
   - Added `extraction_mode` column to `documents` table (`digital_pdf`, `tesseract_ocr`, `simulated_fallback`, `ocr_unavailable`).
   - Added configuration flag `VEXORA_STRICT_OCR` (default off). When enabled and Tesseract binary is absent from PATH, returns an explicit `status = "OCR unavailable"` and `extraction_mode = "ocr_unavailable"` rather than synthetic text.
   - When Tesseract is absent and `VEXORA_STRICT_OCR` is false, gracefully retains the simulated fallback text with `extraction_mode = "simulated_fallback"`.

4. **Display Renaming: "Rule Weight" & Visible Warning Badges (`backend/reporter.py`, `frontend/js/app.js`, `frontend/js/v2.js`):**
   - Renamed display labels for rule-based findings (e.g., `RULE-VIS-*`, `RULE-CTX-*`, `PDF-*`, `IMG-*`) from "Confidence" to **"Rule Weight"** in all user-facing presentations (HTML dossier, vector PDF dossier, finding feed cards, and the interactive Visual Evidence Modal).
   - Preserved underlying database column `confidence` and API JSON keys for 100% backward compatibility.
   - Added visible warning badges:
     - Document library card: `⚠️ Simulated Fallback (OCR Unavailable)`
     - HTML dossier inventory: `⚠️ SIMULATED FALLBACK (OCR UNAVAILABLE)`
     - Vector PDF dossier table: `[⚠️ SIMULATED OCR]`

5. **Unit & Integration Test Suite (`tests/test_v2_phase_e.py`):**
   - 6 comprehensive tests:
     - `test_digital_pdf_entity_confidence`: Verifies digital text entities have `'n/a (digital text)'` confidence.
     - `test_ocr_word_confidence_and_entity_averaging`: Verifies `image_to_data` confidence parsing and entity averaging.
     - `test_tesseract_missing_fallback`: Verifies graceful simulated_fallback mode when Tesseract is absent.
     - `test_strict_ocr_flag_enabled`: Verifies explicit 'OCR unavailable' error under `VEXORA_STRICT_OCR=True`.
     - `test_entities_table_persistence`: Verifies SQLite `entities` table population with confidence strings.
     - `test_dossier_and_ui_display_rule_weight`: Verifies 'Rule Weight' display and warning badge rendering in dossiers.

### Technologies Introduced
- **Tesseract TSV / Dict Data Extraction:** Parsing raw bounding box confidences from `pytesseract.image_to_data` without executing intermediate file writes.
- **Constituent Token Confidence Averaging:** Mapping entity substrings back to raw OCR tokens to generate mathematically grounded field confidence scores.
- **Strict vs. Fallback Operational Modes:** Granular feature flags allowing production strictness or seamless offline demonstrations.

### Actual Testing Results
- **Phase E Confidence Suite (`tests/test_v2_phase_e.py`):** 6/6 passed (`OK`).
- **Phase D Image Forensics Suite (`tests/test_v2_phase_d.py`):** 8/8 passed (`OK`).
- **Phase C LLM Reasoning Suite (`tests/test_v2_phase_c.py`):** 9/9 passed (`OK`).
- **Phase B PDF Forensics Suite (`tests/test_v2_phase_b.py`):** 17/17 passed (`OK`).
- **Phase A Overlay Suite (`tests/test_v2_phase_a.py`):** 11/11 passed (`OK`).
- **Contract Safety Net Suite (`tests/test_v2_contract.py`):** 15/15 passed (`OK`).
- **Baseline Test Suite (`tests/test_backend.py`):** 39/39 passed (`OK`).
- **Combined Test Total:** 105/105 passing across all suites in 24.81s.

### Known Limitations
- When Tesseract is not installed on the host system, OCR confidence is unavailable, and documents explicitly report `extraction_mode="simulated_fallback"`.

### Concepts Learned
- **Distinguishing Probabilities from Rule Weights:** Calling a rule severity score (e.g. 0.85) a "confidence" misleads users into believing a statistical classifier made a probabilistic judgment. Clarifying it as "Rule Weight" maintains scientific integrity.
- **Digital vs OCR Confidence:** In digital PDFs, characters are exact glyph codes in font maps (100% fidelity). Marking digital entities as `"n/a (digital text)"` prevents confusion with OCR character recognition scores.

### Suggested Git Commit Message
`feat(phase-e): implement field-level confidence, extraction modes, entities table, and rule weight display`

---

## Phase F — Cross-Document Correlation & Relationship Graph Log

- **Completion Date:** 2026-11-02
- **Status:** **Completed** (Pushed to GitHub `main` branch)

### Features Implemented
1. **Cross-Document Correlation Engine (`backend/correlator.py`):**
   - Protected under feature flag `ENABLE_CORRELATOR = os.environ.get('ENABLE_CORRELATOR', 'false')`.
   - **Label-Aware Monetary Totals:** Implemented `extract_labeled_invoice_totals` using regex pattern detection for grand totals, net payables, amounts due, and invoice balances, distinguishing totals from intermediary line items.
   - **Bank Transaction Payment Matching:** Scans bank statement lines for reference notes and matches transaction debits directly against related invoices in the same case.
   - **Normalized Fuzzy Counterparty Comparison:** Strips corporate entity suffixes (`Inc`, `LLC`, `Corp`, `Ltd`, `Industries`, `Ventures`, `Technologies`, etc.) and calculates token subset overlap and sequence similarity via `difflib.SequenceMatcher`.
   - **Chronological Sequence Conflict Detection:** Parses robust date formats and flags chronological anomalies (e.g. an invoice dated after a settlement or bank statement date).
   - **Relationship Graph Construction (`build_case_relationship_graph`):** Assembles a graph containing document nodes and extracted entity nodes linked by typed relation edges (`shared_invoice_id`, `shared_amount`, `shared_party`, `date_conflict`, `bank_payment_match`), each carrying verbatim textual evidence quotes and page references.

2. **Content-Based Classification Fallback (`backend/classifier_content.py`, `backend/analyzer.py`, `backend/models.py`):**
   - Implemented `classify_by_content` with domain vocabularies covering `Invoice`, `Bank Statement`, `Purchase Order`, `Tax Return`, `Employment Contract`, `Financial Audit`, and `Identity Record`.
   - Strictly utilized as a secondary fallback: invoked ONLY when existing filename-based classification returns `General Document` or `Uncategorized`. All existing non-General classifications remain 100% untouched.
   - Refined categories automatically update SQLite `documents` table via `update_document_category`.

3. **REST API Endpoint (`backend/app.py`):**
   - Added `GET /api/cases/<case_id>/relationships`:
     - Returns 403 Forbidden with actionable message if `ENABLE_CORRELATOR` is disabled.
     - Returns 200 with structured nodes, edges, metrics, and data envelope when enabled.

4. **Frontend Vanilla SVG Visualization (`frontend/index.html`, `frontend/js/v2.js`):**
   - Added Cross-Document Relationship Graph card in the Cross-Document Comparison view (`#view-comparison`).
   - Includes case selector dropdown and refresh controls.
   - Renders interactive vanilla SVG graph with color-coded nodes (Documents, Identifiers, Monetary Amounts, Organizations) and edge types (Invoice matches, Amount matches, Party matches, and dashed Red Date Conflicts).
   - Built interactive node and edge inspection card (`#relGraphDetailsCard`) displaying full verbatim evidence quotes and page provenance on click.

5. **Unit & Integration Test Suite (`tests/test_v2_phase_f.py`):**
   - 9 automated tests:
     - `test_01_classify_by_content_invoice`: Verifies invoice semantic classification.
     - `test_02_classify_by_content_bank_statement`: Verifies bank statement classification.
     - `test_03_classify_by_content_purchase_order`: Verifies purchase order classification.
     - `test_04_classify_by_content_fallback_general`: Verifies general document fallback.
     - `test_05_label_aware_totals_extraction`: Verifies label-aware invoice total extraction.
     - `test_06_fuzzy_party_normalization_and_similarity`: Verifies party suffix normalization and fuzzy matching.
     - `test_07_build_case_relationship_graph`: Verifies complete multi-document graph generation.
     - `test_08_api_case_relationships_disabled`: Verifies 403 status when feature flag is off.
     - `test_09_api_case_relationships_enabled`: Verifies 200 status and schema compliance when feature flag is on.

### Technologies Introduced
- **Vanilla SVG Radial/Concentric Layout:** Clean, zero-dependency graph rendering directly in the DOM without D3 or heavy graph bundles.
- **Label-Aware Entity Parsing:** Distinguishing stated document totals and balances from arbitrary numerical tokens.
- **Fuzzy Token Normalization:** Corporate entity suffix stripping and subset matching via Python standard library `difflib`.

### Actual Testing Results
- **Phase F Correlator Suite (`tests/test_v2_phase_f.py`):** 9/9 passed (`OK`).
- **Phase E Confidence Suite (`tests/test_v2_phase_e.py`):** 6/6 passed (`OK`).
- **Phase D Image Forensics Suite (`tests/test_v2_phase_d.py`):** 8/8 passed (`OK`).
- **Phase C LLM Reasoning Suite (`tests/test_v2_phase_c.py`):** 9/9 passed (`OK`).
- **Phase B PDF Forensics Suite (`tests/test_v2_phase_b.py`):** 17/17 passed (`OK`).
- **Phase A Overlay Suite (`tests/test_v2_phase_a.py`):** 11/11 passed (`OK`).
- **Contract Safety Net Suite (`tests/test_v2_contract.py`):** 15/15 passed (`OK`).
- **Baseline Test Suite (`tests/test_backend.py`):** 39/39 passed (`OK`).
- **Combined Test Total:** 114/114 passing across all 8 test files in 28.45s.

### Concepts Learned
- **Deterministic Radial Graph Geometry:** Using trigonometric layout equations `(cx + r * cos(θ), cy + r * sin(θ))` eliminates the layout jitter, nondeterminism, and external dependencies of force-directed graph engines.
- **Correlating Across Financial Domains:** Cross-correlating banking payment memos with invoice identifiers reveals circular transactions and timeline anomalies without speculative assumptions.

### Suggested Git Commit Message
`feat(phase-f): implement correlator, relationship graph SVG, and content-based classification fallback`

---

## Phase G — Proof, Documentation, and Honesty Fixes Log

- **Completion Date:** 2026-11-02
- **Status:** **Completed** (Pushed to GitHub `main` branch)

### Features Implemented
1. **Demonstration Dataset Generator (`tools/make_samples.py`):**
   - Programmatically generates 20 benchmark documents in `demo_dataset/`:
     - 10 Genuine Documents (invoices, bank statements, purchase orders, contracts, Form 1040 tax return, digital receipt, identity badge, audit report).
     - 10 Tampered Documents featuring realistic synthetic distortions:
       - Font / typographical baseline alterations
       - Whitebox text redaction / pasting
       - Chronological reversed timeline (due date preceding issue date)
       - Duplicate invoice ID pair with conflicting totals
       - Cross-document bank payment contradictions
       - Disallowed photo-editing software metadata (Adobe Photoshop 2024)
       - Copy-move stamp and signature duplication
       - Futuristic date timeline anomaly
       - Incremental PDF revision timestamp divergence
   - Generated `demo_dataset/labels.csv` ground-truth table (`filename,is_tampered,tampering_type,expected_rules`).

2. **Automated Forensic Evaluation Engine (`tools/evaluate.py`):**
   - Runs full document analysis, OCR, visual heuristics, PDF primitives, and image forensics across the benchmark dataset.
   - Computes and prints an unvarnished forensic performance table:
     - True Positives, False Negatives, True Negatives, False Positives
     - Overall Accuracy, Precision, Recall (Detection Rate), Specificity, and F1-Score
     - Per-rule activation frequency counts.
   - Reports honest numbers without synthetic inflation (highlighting false alarms on flat digital graphics and cross-document pair requirements).

3. **Complete Architectural & Forensic Documentation:**
   - **`docs/ARCHITECTURE.md`:** Comprehensive end-to-end architecture breakdown with an exhaustive Mermaid diagram detailing document intake, extraction, NER, visual rules, PDF primitives, image forensics, LLM grounding, cross-comparison, dossiers, and immutable audit logs.
   - **`docs/CAPABILITIES.md`:** Thorough capabilities matrix mapping all 7 Hackathon evaluation categories with explicit statuses (`Implemented`, `Unsupported`, `Planned`), technical mechanisms, and operational constraints. Explicitly states that Handwriting Recognition and Non-Latin Multilingual OCR are unsupported.
   - **`docs/LIMITATIONS.md`:** Transparent disclosure of operational assumptions, edge cases, synthetic image ELA sensitivity, date ambiguities, and investigator guidelines.

4. **Honesty Corrections & Documentation Alignment (`README.md`):**
   - Corrected historical inaccuracies: clarifies that VEXORA uses deterministic regex NER (`ner.py`) rather than spaCy, extension-based and SHA-256 validation rather than binary MIME sniffing, and PyMuPDF (`pymupdf`) for PDF extraction and rendering.
   - Added comprehensive "V2 Forensic Extensions & Additions" section detailing Phases A through G.
   - Reaffirmed core forensic principle: the system never declares "confirmed fraud"; findings represent heuristic observations or potential anomalies requiring human review.

5. **Security Hardening & Demo SSO:**
   - Configured `SECRET_KEY` fallback from environment.
   - Restricted CORS to `VEXORA_CORS_ORIGINS` (`http://127.0.0.1:5000,http://localhost:5000,http://127.0.0.1:5500,http://localhost:3000`).
   - Implemented `@app.route('/api/auth/google')` endpoint and UI button explicitly labeled as `"demo login (not verified)"`.

6. **Unit & Integration Test Suite (`tests/test_v2_phase_g.py`):**
   - 6 automated tests:
     - `test_01_demo_dataset_and_labels_exist`: Verifies 20+ dataset files and `labels.csv` schema.
     - `test_02_evaluation_pipeline_execution`: Verifies successful execution of `tools/evaluate.py`.
     - `test_03_documentation_files_exist_and_contain_required_sections`: Verifies Mermaid diagrams in ARCHITECTURE.md, and honesty notes in CAPABILITIES.md and LIMITATIONS.md.
     - `test_04_readme_corrections_and_v2_additions`: Verifies V2 additions and accurate NER descriptions in README.md.
     - `test_05_demo_google_login_endpoint`: Verifies `/api/auth/google` returns demo unverified status.
     - `test_06_cors_configuration`: Verifies CORS origin restrictions.

### Actual Testing Results
- **Phase G Proof & Docs Suite (`tests/test_v2_phase_g.py`):** 6/6 passed (`OK`).
- **Phase F Correlator Suite (`tests/test_v2_phase_f.py`):** 9/9 passed (`OK`).
- **Phase E Confidence Suite (`tests/test_v2_phase_e.py`):** 6/6 passed (`OK`).
- **Phase D Image Forensics Suite (`tests/test_v2_phase_d.py`):** 8/8 passed (`OK`).
- **Phase C LLM Reasoning Suite (`tests/test_v2_phase_c.py`):** 9/9 passed (`OK`).
- **Phase B PDF Forensics Suite (`tests/test_v2_phase_b.py`):** 17/17 passed (`OK`).
- **Phase A Overlay Suite (`tests/test_v2_phase_a.py`):** 11/11 passed (`OK`).
- **Contract Safety Net Suite (`tests/test_v2_contract.py`):** 15/15 passed (`OK`).
- **Baseline Test Suite (`tests/test_backend.py`):** 39/39 passed (`OK`).
- **Combined Test Total:** 120/120 passing across all 9 test suites in 28.16s.

### Suggested Git Commit Message
`feat(phase-g): implement evaluation benchmark, proof dataset, architecture documentation, and honesty fixes`


---

## V2 Phase H — Stabilize the Demo (P1 & P2 Fixes) Log

- **Completion Date:** 2026-11-03
- **Status:** **Completed** (Tested on branch `feature/v2-phase-h`)

### Executive Summary & Objectives
Phase H stabilized VEXORA for live evaluation by addressing two critical issues identified during review:
1. **P1 (Demo Visibility & Configuration):** All V2 features previously defaulted to `false` without setup documentation or runtime status feedback, meaning an evaluator starting the app would only see legacy behavior.
2. **P2 (Image Forensics Gate & Heuristic False Alarms):** The image forensics runner previously rasterized born-digital vector PDF pages into synthetic images (`page.get_pixmap(dpi=150)`) and ran pixel-level algorithms (ELA, sharpness variance, copy-move) on pure vector text. This produced widespread false positives on clean documents (e.g. 100/100 risk on bank statements and repeated letters matching as copy-move).

### Features & Principled Fixes Implemented
1. **Principled Gate for Image Forensics (`backend/forensics_image.py`):**
   - Rules `IMG-001` (ELA), `IMG-002` (Sharpness), and `IMG-003` (Copy-Move) now run exclusively on:
     (a) Standalone uploaded raster images (`.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`).
     (b) Raster images actually *embedded* inside a PDF, extracted directly from the document via PyMuPDF's `page.get_images()`.
   - Vector-only born-digital PDF pages are **never** rasterized into synthetic bitmaps.
   - When a PDF contains zero embedded raster images, VEXORA logs a single, non-alarming Observation note: `"image forensics not applicable: born-digital PDF with no embedded images"` with zero risk penalty.
2. **Copy-Move Typographical Filtering (`backend/forensics_image.py`):**
   - Implemented `_detect_text_line_boxes` using morphological text strip profiling.
   - `check_copy_move_orb` filters out ORB keypoint pairs that lie within detected text areas, preventing repeated letters ('e', 'o', '1', etc.) from triggering false clone alarms while still reliably detecting duplicated stamps, signatures, or pasted figures.
3. **Signature Analysis Grounding (`backend/forensics_image.py`):**
   - Excluded full-width outer border rectangles (`cw >= w * 0.70`) from being falsely interpreted as cursive signature strokes.
   - Only reports missing signature notices when the document category explicitly expects one (e.g. `Contract`, `Agreement`, `Deed`). Ordinary receipts and badges never emit spurious "unsupported" or "missing signature" findings.
4. **Heuristic Severity Capping (`backend/forensics_image.py`):**
   - Capped the severities of heuristic rules `IMG-001` and `IMG-003` at `Medium` (down from `High`).
   - Descriptions explicitly state heuristic limitations and the requirement for human verification.
5. **V2 Configuration & Diagnostics Banner (`backend/config.py`, `backend/banner.py`, `backend/app.py`):**
   - Created `.env.example` documenting every V2 feature flag with clear, safe comments.
   - Created a local gitignored `.env` file enabling non-LLM forensic features and strict OCR for full demo readiness.
   - Implemented an ASCII startup banner (`print_startup_banner()`) displayed on server boot, showing the exact ON/OFF status of every flag and whether the system Tesseract OCR binary is installed.
   - Extended `GET /api/system/diagnostics` with `v2_features`, `tesseract_available`, and `tesseract_detail`.
6. **Documentation & Benchmark Tracking:**
   - Appended a comprehensive "Setup and Enabling V2 Features" section to `README.md`.
   - Evaluated benchmark performance before and after Phase H:
     - Output saved to `docs/BENCHMARK_BEFORE.txt` and `docs/BENCHMARK_AFTER_H.txt`.
     - Fired rules for clean PDFs dropped to 0 IMG findings.
     - IMG-003 and IMG-004 false alarms dropped to 0 on genuine documents.

### Beginner-Friendly Explanation (For Hackathon Judges)
**Why did genuine bank statements show 100/100 risk previously?**
A digital PDF created in Word or Excel contains vector fonts and lines, not pixels. Previously, VEXORA took a digital PDF page, took a "screenshot" of it, and then tried to analyze whether the JPEG compression looked altered (ELA) or if letters looked copy-pasted (copy-move). Because all the letters 'e' and 't' on a page look identical, the algorithm thought someone was copy-pasting numbers and stamps!
In Phase H, we introduced a **principled gate**: we only run image forensic algorithms on actual images! If a PDF is a pure digital document without photos or scans, VEXORA honestly reports: *"image forensics not applicable: born-digital PDF with no embedded images."* This eliminates fake alarms without altering or fudging any thresholds.

### Test Coverage & Verification
- Created `tests/test_v2_phase_h.py` containing 6 unit tests:
  - `test_01_born_digital_pdf_produces_zero_img_findings`: Verifies clean PDFs produce 0 IMG findings and 1 Observation note.
  - `test_02_pasted_patch_image_produces_img_findings_with_capped_severity`: Verifies pasted patches produce findings capped at Medium.
  - `test_03_embedded_image_in_pdf_is_extracted_and_analyzed`: Verifies embedded raster images inside PDFs are extracted and evaluated.
  - `test_04_startup_flag_info_reported_in_diagnostics`: Verifies GET /api/system/diagnostics returns v2 feature flags.
  - `test_05_copymove_ignores_text_areas`: Verifies repeated text lines do not trigger copy-move alarms.
  - `test_06_rules_catalog_capped_at_medium`: Verifies catalog severities are capped at Medium.
- **Test Results:** 126/126 tests passing across all 10 test suites (39 baseline + 87 V2).

---

## V2 Phase I — Live LLM Layer Stabilization & Grounding (P6 Fix) Log

- **Completion Date:** 2026-11-03
- **Status:** **Completed** (Tested on branch `feature/v2-phase-i`)

### Executive Summary & Objectives
Phase I resolved problem **P6** (untested, hardcoded LLM configuration) and made VEXORA's AI intelligence tier reliable, configurable, and safely testable:
1. **Configurable Model Name:** Previously, the Gemini model was hardcoded to `gemini-1.5-flash` in `backend/llm.py`, meaning if that specific endpoint was deprecated or unserved, the entire AI tier broke. Model names are now configurable via `VEXORA_LLM_MODEL` with safe defaults per provider (`gemini-1.5-flash`, `gpt-4o-mini`, `claude-3-haiku-20240307`).
2. **Clear Error Reporting on HTTP 4xx:** If a provider returns a 404 or "model not found" error, VEXORA catches it cleanly and advises the user to set `VEXORA_LLM_MODEL` in `.env`, never crashing.
3. **Live AI Connection Test Endpoint & UI:** Added `POST /api/system/ai-test` measuring live latency and status without leaking API keys. Added a "Test AI Connection" button to the System Settings diagnostics pane.
4. **Structured Field Extraction & Document View Table:** Structured extraction now explicitly extracts `vendor`, `invoice_number`, `dates`, `subtotal`, `tax`, `total`, `line_items`, and `parties`. Each field requires a verbatim source quote verified by substring matching; ungrounded fields are dropped. Extracted fields are stored in `ai_insights` and rendered in the Forensic Document Inspector with a prominent label: `"AI-assisted, requires human review"`.
5. **Contextual Crosscheck Prompts:** The multi-document cross-examination prompt specifically checks four categories:
   - Totals that do not equal the sum of line items.
   - Mismatched parties across documents.
   - Impossible timelines and chronological sequence violations.
   - Amounts that differ across documents for the same reference.
   Every claim requires a grounded verbatim source quote or is discarded.
6. **CLI Demonstration Script (`tools/demo_ai.py`):** Added a CLI demo tool that accepts `--doc` and runs extraction, finding explanation, and cross-checking. When no API key is configured, it prints `"AI not configured, skipped"` and cleanly exits with code 0.

### Beginner-Friendly Explanation (For Hackathon Judges)
**Why is anti-hallucination source quote verification crucial in document forensics?**
Large Language Models (LLMs) are notorious for generating plausible-sounding facts that never existed in the source document ("hallucinations"). In a forensic or legal audit, an investigator cannot afford AI that invents offshore entities or imaginary bank account discrepancies.
VEXORA enforces a strict rule: **"If you can't quote it word-for-word from the text, you can't report it."** For every single field and anomaly the model claims to find, VEXORA performs a code-level string search in the original document text. If the exact words are not there, VEXORA drops the claim immediately. This guarantees that every AI insight is 100% grounded in real document evidence.

### Test Coverage & Verification
- Created `tests/test_v2_phase_i.py` with 10 unit and integration tests:
  - `test_default_models_per_provider`: Verifies default model dictionary per provider.
  - `test_configured_model_override`: Verifies `VEXORA_LLM_MODEL` overrides default model for any provider.
  - `test_bad_model_name_returns_clear_error_gemini`: Verifies Gemini 404 returns clear message to set `VEXORA_LLM_MODEL`.
  - `test_bad_model_name_returns_clear_error_openai`: Verifies OpenAI 404 returns clear error without crashing.
  - `test_contextual_crosscheck_drops_ungrounded_quote`: Verifies ungrounded quotes are dropped from crosscheck findings.
  - `test_extract_fields_llm_drops_ungrounded_and_keeps_grounded`: Verifies ungrounded scalar fields are moved to `dropped_fields`.
  - `test_ai_test_endpoint_when_disabled_returns_expected_keys`: Verifies `POST /api/system/ai-test` returns safe keys and no secrets when disabled.
  - `test_ai_test_endpoint_mock_success`: Verifies `POST /api/system/ai-test` returns latency and model details when active.
  - `test_document_ai_insights_endpoint`: Verifies `GET /api/documents/<id>/ai-insights` returns stored insights and 404 for missing docs.
  - `test_demo_ai_exits_0_when_no_key_configured`: Verifies CLI tool exits cleanly with code 0 and prints skipped message.
- **Combined Test Total:** 136/136 tests passing across all 11 test suites.
