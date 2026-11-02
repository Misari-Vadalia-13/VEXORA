# VEXORA Existing System Contract & Behavioral Specification

This document defines the baseline contract for **VEXORA: AI-Powered Document Forensics and Contextual Intelligence System**.
Extracted directly from the running production codebase (Phases 1–9, 39 passing unit tests), this contract serves as the safety net and specification of record.

> **CRITICAL RULE**: Under Section 1 Non-Negotiable Rules, all existing routes, database columns, JSON response keys, HTML element IDs, CSS classes, rule IDs, and data shapes defined herein are **frozen**. New features must be additive only and must never break or alter these definitions.

---

## 1. Flask Served Index & Static Asset Contract

* **Active Index Served by Flask**: `frontend/index.html`
  * Defined in `backend/app.py`:
    ```python
    @app.route('/')
    @app.route('/index.html')
    def serve_index():
        return send_from_directory(FRONTEND_DIR, 'index.html')
    ```
    where `FRONTEND_DIR = BASE_DIR / 'frontend'`.
* **Root `index.html` (`c:\VEXORA\index.html`)**:
  * Pure static redirect stub (`<meta http-equiv="refresh" content="0; url=frontend/index.html">`).
  * **Not served by Flask**.
  * **Rule**: Do NOT touch `c:\VEXORA\index.html`. All UI enhancements apply strictly to `frontend/index.html` and additive assets (`frontend/js/v2.js`, `frontend/css/v2.css`).

---

## 2. Relational Database Schema & Data Dictionaries

Source: `backend/schema.sql` (SQLite, `backend/vexora.db`)

### Table 1: `users`
* `id`: `INTEGER PRIMARY KEY AUTOINCREMENT`
* `username`: `TEXT UNIQUE NOT NULL`
* `email`: `TEXT UNIQUE NOT NULL`
* `password_hash`: `TEXT NOT NULL`
* `role`: `TEXT NOT NULL DEFAULT 'Forensic Analyst'`
* `badge_number`: `TEXT`
* `created_at`: `TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

### Table 2: `cases`
* `id`: `TEXT PRIMARY KEY` (Format: `CAS-YYYY-NNNN`)
* `title`: `TEXT NOT NULL`
* `type`: `TEXT NOT NULL`
* `priority`: `TEXT NOT NULL CHECK(priority IN ('Critical', 'High', 'Medium', 'Low'))`
* `status`: `TEXT NOT NULL CHECK(status IN ('Active', 'In Review', 'Pending', 'Archived', 'Solved'))`
* `investigator`: `TEXT NOT NULL`
* `description`: `TEXT`
* `created_at`: `TIMESTAMP DEFAULT CURRENT_TIMESTAMP`
* `updated_at`: `TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

### Table 3: `documents`
* `id`: `TEXT PRIMARY KEY` (Format: `DOC-YYYY-NNNN` or `DOC-YYYYMMDD-HHMMSS-NNNN`)
* `case_id`: `TEXT`, `FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL`
* `filename`: `TEXT NOT NULL`
* `file_type`: `TEXT NOT NULL` (`pdf`, `png`, `jpg`, `jpeg`)
* `file_size`: `INTEGER NOT NULL` (bytes)
* `file_path`: `TEXT`
* `file_hash`: `TEXT` (Hexadecimal SHA-256)
* `category`: `TEXT DEFAULT 'Uncategorized'`
* `classification_confidence`: `REAL DEFAULT 0.0`
* `status`: `TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Processing', 'Analyzed', 'Flagged', 'Clean'))`
* `extracted_text`: `TEXT`
* `extracted_data`: `TEXT` (JSON serialized layout, metadata, and entities)
* `uploaded_by`: `TEXT DEFAULT 'Lead Investigator'`
* `uploaded_at`: `TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

### Table 4: `findings`
* `id`: `TEXT PRIMARY KEY` (Format: `FND-YYYYMMDD-HHMMSS-NNNN`)
* `case_id`: `TEXT`, `FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE`
* `document_id`: `TEXT`, `FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL`
* `title`: `TEXT NOT NULL`
* `severity`: `TEXT NOT NULL CHECK(severity IN ('Critical', 'High', 'Medium', 'Low', 'Info'))`
* `category`: `TEXT NOT NULL`
* `description`: `TEXT`
* `confidence`: `REAL DEFAULT 0.0`
* `status`: `TEXT NOT NULL DEFAULT 'Unresolved' CHECK(status IN ('Unresolved', 'Verified', 'Dismissed'))`
* `page_number`: `INTEGER DEFAULT 1`
* `coordinates`: `TEXT` (JSON or string representation of bounding box `[x0, y0, x1, y1]`)
* `rule_id`: `TEXT` (e.g., `RULE-VIS-001`, `RULE-CTX-002`)
* `evidence`: `TEXT`
* `created_at`: `TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

### Table 5: `audit_logs`
* `id`: `INTEGER PRIMARY KEY AUTOINCREMENT`
* `action`: `TEXT NOT NULL`
* `entity_type`: `TEXT NOT NULL`
* `entity_id`: `TEXT`
* `details`: `TEXT`
* `user`: `TEXT DEFAULT 'System'`
* `timestamp`: `TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

### Table 6: `comparisons`
* `id`: `TEXT PRIMARY KEY` (Format: `CMP-YYYYMMDDHHMMSS`)
* `case_id`: `TEXT`, `FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE`
* `doc_a_id`: `TEXT NOT NULL`, `FOREIGN KEY (doc_a_id) REFERENCES documents(id) ON DELETE CASCADE`
* `doc_b_id`: `TEXT NOT NULL`, `FOREIGN KEY (doc_b_id) REFERENCES documents(id) ON DELETE CASCADE`
* `discrepancies_count`: `INTEGER DEFAULT 0`
* `matches_count`: `INTEGER DEFAULT 0`
* `results_json`: `TEXT` (JSON serialized list of alignment matrix items)
* `created_at`: `TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

### Table 7: `reports`
* `id`: `TEXT PRIMARY KEY` (Format: `RPT-YYYYMMDD-HHMMSS-NNNN`)
* `case_id`: `TEXT NOT NULL`, `FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE`
* `title`: `TEXT NOT NULL`
* `file_path`: `TEXT NOT NULL`
* `file_format`: `TEXT NOT NULL DEFAULT 'pdf'` (`pdf` or `html`)
* `file_size`: `INTEGER DEFAULT 0`
* `generated_by`: `TEXT DEFAULT 'Lead Investigator'`
* `created_at`: `TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

---

## 3. Forensic Rules Catalog

Defined in `backend/analyzer.py:RULES`.

| Rule ID | Category | Title | Severity | Confidence | Detection Logic & Scope |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `RULE-VIS-001` | Visual Formatting | Discrepant Font Family Detected | `Medium` | `0.88` | Analyzes PDF text spans. Flags spans using fonts with < 15% prevalence across document as potential typographic insertions. |
| `RULE-VIS-002` | Structural Alignment | Overlapping Text Elements Detected | `High` | `0.92` | Detects physical 2D bounding-box collisions between distinct text spans on the same page (> 40% area overlap). |
| `RULE-VIS-003` | Structural Alignment | Out-of-Bounds Text Placement | `Low` | `0.80` | Flags text spans positioned dangerously close to or exceeding outer page margins (< 5 pt margin boundary). |
| `RULE-VIS-004` | Visual Formatting | Irregular Line Spacing Disparity | `Low` | `0.75` | Defined in rule catalog for paragraph baseline disparity checks. *(Note: currently uncalled in visual engine)*. |
| `RULE-VIS-005` | Visual Formatting | Degraded Resolution or Compression Artifact | `Info` | `0.70` | Flags images with dimensions < 200x200 px where text legibility may be compromised. |
| `RULE-CTX-001` | Contextual Inconsistency | Missing Mandatory Document Field | `Medium` | `0.90` | For invoices/bills: checks for missing ID, date, amount, vendor. For contracts: checks for dates and >= 2 counterparties. |
| `RULE-CTX-002` | Contextual Inconsistency | Multiple Conflicting Document Identifiers | `High` | `0.94` | Detects distinct conflicting identifiers matching the same entity prefix type (e.g. two conflicting invoice IDs in one doc). |
| `RULE-CTX-003` | Contextual Inconsistency | Chronological Sequence Inconsistency | `High` | `0.91` | Compares date entities. Flags reversed chronology (e.g., payment due date preceding invoice issue date). |
| `RULE-CTX-004` | Contextual Inconsistency | Conflicting Monetary Values or Currencies | `High` | `0.93` | Flags presence of mixed currency symbols or multiple divergent monetary totals in invoice bodies. |
| `RULE-CTX-005` | Contextual Inconsistency | Metadata Timestamp Mismatch | `Medium` | `0.78` | Compares PDF creation date (`creationDate`) with dates extracted from document text; flags > 1 year discrepancy. |

### Risk Score Calculation Formula
* **Weights**: `Critical` = 35, `High` = 20, `Medium` = 10, `Low` = 5, `Info` = 2
* **Composite Score**: `risk_score = min(sum(weights), 100)`
* **Risk Tiers**:
  * `Critical Risk`: `risk_score >= 60` OR `Critical count > 0`
  * `High Risk`: `risk_score >= 35` OR `High count > 0`
  * `Medium Risk`: `risk_score >= 15`
  * `Low Risk`: `risk_score > 0`
  * `Clean / Verified`: `risk_score == 0`

---

## 4. Evidentiary Data Structures & Record Shapes

### Finding Record Shape (Dictionary returned by `analyzer.py` / stored in `findings`)
```json
{
  "id": "FND-20261102-184500-0001",
  "document_id": "DOC-2026-0001",
  "case_id": "CAS-2026-0001",
  "rule_id": "RULE-VIS-001",
  "title": "Discrepant Font Family Detected",
  "severity": "Medium",
  "category": "Visual Formatting",
  "status": "Potential Anomaly",
  "confidence": 0.88,
  "page_number": 1,
  "coordinates": [72.0, 150.5, 220.0, 165.2],
  "description": "Text span 'Total Due: $9,500' rendered in 'Courier-Bold' (minority font).",
  "evidence": "Font 'Courier-Bold' (1 spans, 4.2%) vs primary 'Helvetica' (23 spans, 95.8%)",
  "created_at": "2026-11-02 18:45:00"
}
```

### Extracted Entities Record Shape (`backend/ner.py` output stored in `documents.extracted_data`)
```json
{
  "entities": {
    "dates": [
      { "value": "2026-03-15", "page": 1 }
    ],
    "monetary_values": [
      { "value": "$4,850,000.50", "page": 1 }
    ],
    "organizations": [
      { "value": "Apex Logistics Corp.", "page": 1 }
    ],
    "persons": [
      { "value": "Dr. Aris Thorne", "page": 1 }
    ],
    "identifiers": [
      { "value": "INV-2026-9921", "page": 1 }
    ],
    "emails": [
      { "value": "billing@apexlogistics.com", "page": 1 }
    ]
  },
  "metadata": {
    "page_count": 1,
    "title": "Invoice",
    "author": "Apex Billing System",
    "producer": "PyMuPDF",
    "creator": "VEXORA Test Generator",
    "creation_date": "2026-03-15"
  },
  "total_words": 142,
  "full_text": "..."
}
```

### Comparison Alignment Matrix Item Shape (`backend/comparator.py`)
```json
{
  "attribute": "Primary Monetary Value",
  "val_a": "$4,850,000.50",
  "val_b": "$4,120,000.00",
  "page_a": 1,
  "page_b": 1,
  "status": "Conflict",
  "verdict": "⚠️ Monetary Mismatch",
  "explanation": "Financial disparity of $730,000.00 (15.1% variance) detected between Document A ($4,850,000.50) and Document B ($4,120,000.00)."
}
```

---

## 5. REST API Route Registry & Response Contracts

All responses follow standard status codes and JSON envelope shapes.

| Method | Route | Description | Required Request Params / Payload | Primary Response JSON Keys |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | Serves `frontend/index.html` | None | HTML content |
| `GET` | `/index.html` | Serves `frontend/index.html` | None | HTML content |
| `GET` | `/api/health` | Healthcheck & DB status | None | `status`, `system`, `version`, `database` |
| `GET` | `/api/stats` | Dashboard metrics | None | `success`, `data` (`total_cases`, `active_cases`, `total_documents`, `total_findings`, `flagged_documents`, `critical_findings`, `high_risk_rate_percent`, `system_status`, `timestamp`) |
| `GET` | `/api/system/diagnostics` | Self-diagnostic probe | None | `success`, `status`, `engine_version`, `timestamp`, `database`, `storage`, `pymupdf_version`, `python_version` |
| `POST` | `/api/auth/register` | User registration | `username`, `email`, `password`, `role`, `badge_number` | `success`, `message`, `user` |
| `POST` | `/api/auth/login` | Session login | `username`, `password` | `success`, `message`, `user` |
| `GET` | `/api/auth/current-user` | Active session user | None | `authenticated`, `user` |
| `GET` | `/api/cases` | List cases | Query params: `priority`, `status`, `search` | `success`, `count`, `data` (list of case objects) |
| `POST` | `/api/cases` | Create case | `title`, `type`, `priority`, `status`, `investigator`, `description` | `success`, `message`, `data` (case object) |
| `GET` | `/api/cases/<case_id>` | Get case by ID | None | `success`, `data` (case object with `documents`, `findings`) |
| `PUT` | `/api/cases/<case_id>` | Update case | `title`, `type`, `priority`, `status`, `investigator`, `description` | `success`, `message`, `data` (updated case object) |
| `DELETE` | `/api/cases/<case_id>` | Delete case | None | `success`, `message` |
| `GET` | `/api/cases/<case_id>/compare` | Cross-compare case docs | None | `success`, `case_id`, `documents_count`, `comparisons_run`, `discrepancies_count`, `discrepancies` |
| `GET` | `/api/cases/<case_id>/dossier` | Get aggregated dossier | None | `success`, `case_id`, `data` (`case`, `executive_summary`, `documents`, `findings`, `cross_document_comparison`, `provenance_graph`, `disclaimer`) |
| `POST` | `/api/cases/<case_id>/report` | Generate PDF/HTML dossier | JSON: `{ "format": "pdf" \| "html" }` | `success`, `report_id`, `case_id`, `file_format`, `file_size_formatted`, `download_url`, `view_url` |
| `GET` | `/api/documents` | List documents | Query params: `case_id`, `category` | `success`, `count`, `data` (list of document objects) |
| `POST` | `/api/documents` | Register document | `filename`, `file_size`, `file_type`, `file_path`, `case_id` | `success`, `message`, `data` (document object) |
| `GET` | `/api/documents/<doc_id>` | Get document by ID | None | `success`, `data` (document object) |
| `DELETE` | `/api/documents/<doc_id>` | Delete document | None | `success`, `message` |
| `POST` | `/api/documents/upload` | Ingest files | Multipart: `file` or `files[]`, `case_id`, `category` | `success`, `message`, `uploaded_count`, `data` |
| `POST` | `/api/documents/<doc_id>/extract` | Extract text & entities | None | `success`, `message`, `document_id`, `data` |
| `GET` | `/api/documents/<doc_id>/extracted` | Get extracted JSON | None | `success`, `document_id`, `data` |
| `POST` | `/api/documents/<doc_id>/analyze` | Run forensic rules | None | `success`, `document_id`, `findings_count`, `risk_score`, `risk_level`, `severity_breakdown`, `summary`, `findings` |
| `GET` | `/api/documents/<doc_id>/findings` | Get findings for doc | None | `success`, `document_id`, `count`, `data` (list of findings) |
| `GET` | `/api/documents/<doc_id>/download` | Stream original file | None | File stream |
| `POST` | `/api/documents/compare` | Pairwise doc comparison | JSON: `{ "doc_a_id": "...", "doc_b_id": "..." }` | `success`, `comparison_id`, `doc_a`, `doc_b`, `alignment_matrix`, `conflicts_count`, `matches_count`, `mismatches_count`, `risk_score`, `verdict` |
| `GET` | `/api/evidence-graph` | Evidence graph nodes | Query param: `case_id` (optional) | `success`, `count`, `data` (list of provenance nodes) |
| `GET` | `/api/findings` | List all findings | Query params: `case_id`, `document_id`, `severity`, `status` | `success`, `count`, `data` (list of findings) |
| `POST` | `/api/findings` | Create manual finding | `case_id`, `title`, `severity`, `category`, `document_id`, `description`, etc. | `success`, `message`, `data` |
| `GET` | `/api/findings/<finding_id>` | Get finding by ID | None | `success`, `data` (finding object) |
| `PATCH` | `/api/findings/<finding_id>` | Update finding status | JSON: `{ "status": "Verified" \| "Dismissed" \| "Unresolved" }` | `success`, `message`, `data` |
| `GET` | `/api/reports` | List generated reports | Query param: `case_id` | `success`, `count`, `data` (list of report records) |
| `GET` | `/api/reports/<report_id>` | Get report metadata | None | `success`, `data`, `download_url`, `view_url` |
| `GET` | `/api/reports/<report_id>/download`| Download report file | None | File stream (`application/pdf` or `text/html`) |
| `GET` | `/api/reports/<report_id>/view` | View report in browser | None | Inline stream |
| `GET` | `/api/audit-logs` | Retrieve audit trail | Query param: `limit` (default 50) | `success`, `count`, `data` (list of audit records) |
| `GET` | `/api/audit-logs/export` | Export audit trail CSV | None | CSV download stream (`vexora_audit_trail_YYYYMMDD_HHMMSS.csv`) |

---

## 6. Frontend Contracts: DOM IDs & Rendering Functions

Source: `frontend/index.html` and `frontend/js/app.js`

### Primary View Containers (`.view-section`)
* `#view-dashboard`: Main telemetry and quick-action view
* `#view-cases`: Investigation case management grid
* `#view-upload`: Multi-document ingestion dropzone & queue
* `#view-library`: Document repository browser
* `#view-forensics`: Visual and contextual forensic inspection feed
* `#view-comparison`: Cross-document discrepancy matrix
* `#view-evidence`: Transparent evidence provenance graph
* `#view-dossier`: Case dossier generation & preview panel
* `#view-settings`: System self-diagnostics & theme management

### Key Rendering DOM Elements
* `#forensicFindingsFeed`: Populated by `renderForensicFindings(findings)`. Contains individual observation and anomaly cards.
* `#forensicDocSelector`: Dropdown select to switch active document for forensic inspection.
* `#comparisonMatrixBody`: Populated by `renderComparisonMatrix(result)`. Table body displaying alignment matrix rows.
* `#compareDocA` & `#compareDocB`: Select elements for pairwise document comparison.
* `#evidenceProvenanceContainer`: Populated by `loadEvidenceProvenanceGraph()`. Grid rendering provenance node cards.
* `#dossierFindingsList`: Populated by `loadCaseDossierPreview(caseId)`. Renders findings in dossier view.
* `#dossierEvidenceInventory`: Renders ingested documents in dossier preview.
* `#dossierDiscrepancyList`: Renders cross-document variances in dossier preview.
* `#dossierRiskBadge`: Displays quantitative risk tier badge in dossier preview.
* `#dossierNarrative`: Displays AI/algorithmic executive summary in dossier preview.
* `#dossierCaseSelector`: Case selection dropdown for dossier generation.
* `#generatedReportsTableBody`: Populated by `loadGeneratedReportsList()`. Lists generated PDF/HTML reports.
* `#auditTrailTableBody`: Populated by `loadAuditTrailLogs()`. Displays system audit events.
* `#docLibraryGrid`: Populated by `initBackendSync()`. Displays documents in repository.
* `#caseManagementGrid`: Populated by `initBackendSync()`. Displays cases grid.

### Key JavaScript Functions (`frontend/js/app.js`)
* `analyzeDocumentAndInspect(docId)`: Triggers POST to `/api/documents/${docId}/analyze`, updates findings, switches view to `#view-forensics`.
* `loadDocumentFindings(docId)`: Fetches `/api/documents/${docId}/findings` and calls `renderForensicFindings`.
* `renderForensicFindings(findings)`: Dynamically generates cards for `#forensicFindingsFeed`.
* `triggerCrossDocumentComparison()`: Reads `#compareDocA` & `#compareDocB`, POSTs to `/api/documents/compare`, calls `renderComparisonMatrix`.
* `renderComparisonMatrix(result)`: Renders rows into `#comparisonMatrixBody`.
* `loadEvidenceProvenanceGraph()`: Fetches `/api/evidence-graph` and renders cards into `#evidenceProvenanceContainer`.
* `loadCaseDossierPreview(caseId)`: Fetches `/api/cases/${caseId}/dossier` and updates dossier DOM elements.
* `exportCurrentCaseDossier(format)`: POSTs to `/api/cases/${caseId}/report` (`pdf` or `html`) and opens report URL.
* `loadGeneratedReportsList()`: Fetches `/api/reports` and updates `#generatedReportsTableBody`.
* `loadAuditTrailLogs()`: Fetches `/api/audit-logs` and populates `#auditTrailTableBody`.
* `navigateToView(viewName)`: Manages client-side hash routing (`#dashboard`, `#cases`, `#forensics`, etc.).
