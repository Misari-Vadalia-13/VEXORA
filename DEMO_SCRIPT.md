# VEXORA — Live Judge Demonstration Script (3–5 Minutes)

This script is designed for a concise, high-impact, live evaluation by hackathon judges. It walks through every primary capability of the VEXORA Document Forensics and Contextual Intelligence System.

---

## Pre-Flight Check (30 Seconds Before Demo)

1. Open a terminal in the project directory:
   ```powershell
   .\.venv\Scripts\python.exe -m backend.app
   ```
2. Open your browser to: **http://127.0.0.1:5000**
3. Verify the topbar displays:
   - System title: `VEXORA // FORENSIC INTELLIGENCE ENGINE`
   - OCR status: `⚠️ OCR unavailable - fallback mode` (or `Verified OCR Engine` if Tesseract is installed)
   - AI status: `🤖 AI reasoning: OFF (deterministic mode)` (or `Gemini 2.5 Flash` if API key is active)

---

## Demo Script

### ⏱️ 0:00 – 0:45 | Introduction & 1-Click Demo Seed
**Action:** Click the topbar button: **`⚡ Load Demo Case`**

> **Talking Point:**
> *"Judges, document fraud in financial procurement and legal disputes rarely happens in isolation. A single invoice might look completely clean, yet when correlated with bank statements and vendor registries, massive discrepancies emerge.*
> 
> *VEXORA combines low-level PDF vector primitives, pixel-level computer vision forensics, and cross-document relational intelligence.*
> 
> *Notice that with one click of **Load Demo Case**, VEXORA just ingested a multi-document procurement case: an invoice, a duplicate vendor invoice, a commercial bank statement, and a scanned payment receipt. Each document was cryptographically digested with a SHA-256 hash upon intake."*

---

### ⏱️ 0:45 – 1:30 | Single-Document Forensics & Jump-to-Source Overlays
**Action:** Click **"Document Forensics"** in the sidebar.
1. In the **Select Document to Inspect** dropdown, select `tampered_01_font_shift.pdf` (or `tampered_02_whitebox_patch.png`).
2. Point out the **Forensic Taxonomy Badges**:
   - `Potential Manipulation` (Red badge)
   - `Inconsistency` (Amber badge)
   - `Observation` (Blue badge)
3. On any visual finding card, click the **`🔍 View Evidence`** button.
4. The Evidence Modal opens: demonstrate the **Zoom (+ / - / Reset)** and pan controls.

> **Talking Point:**
> *"Here in the Forensic Inspector, VEXORA analyzes the document structure. Notice our strict forensic taxonomy: we never assert speculative claims of 'confirmed fraud.' Findings are classified objectively as Observations, Inconsistencies, or Potential Manipulations.*
> 
> *Notice the red bounding box on the evidence modal: VEXORA isolates the exact coordinates on the page where typographic inconsistency or ELA recompression residue occurs. Every finding is verifiable and tied directly to physical source geometry."*

---

### ⏱️ 1:30 – 2:30 | Cross-Document Comparison & Discrepancy Matrix
**Action:** Click **"Cross-Document Comparison"** in the sidebar.
1. Document A will show `tampered_04_duplicate_inv_a.pdf` and Document B will show `tampered_05_duplicate_inv_b.pdf` (or bank statement).
2. Click the **`Run Cross-Check`** button.
3. Observe the live discrepancy matrix appear immediately, highlighting:
   - Primary Monetary Value: `$5,000.00` vs `$7,500.00`
   - Counterparty mismatch: `Apex Global Industries` vs `Apex Global Solutions`
   - Identifier clash: Same invoice ID `INV-2026-999` issued to different entities.

> **Talking Point:**
> *"Now let's examine why single-document analysis fails in real-world fraud. Documents A and B are two invoices. Taken individually, both appear 100% mathematically and typographically clean.*
> 
> *When we run our Cross-Document Comparator, VEXORA cross-references their entity graphs. It immediately catches the duplicate invoice submission: the same invoice number has been billed twice for different amounts to different legal entities. This is the power of cross-document contextual intelligence."*

---

### ⏱️ 2:30 – 3:15 | Multi-Document Relationship Graph
**Action:** Click **"Relationship Graph"** in the sidebar.
1. Select case `CAS-DEMO-2026` in the dropdown.
2. An interactive SVG network displays nodes and edges connecting documents, counterparties, bank accounts, and transactions.
3. Hover over nodes to highlight connected entity paths.

> **Talking Point:**
> *"VEXORA synthesizes cross-document evidence into an interactive relationship graph rendered in pure SVG without heavy external visualization dependencies. Investigators can visually trace how an invoice connects to a purchase order, an authorized signatory, and a cleared bank statement line item."*

---

### ⏱️ 3:15 – 4:00 | Audit-Ready Dossier Generation
**Action:** Click **"Case Dossiers"** in the sidebar.
1. Ensure `CAS-DEMO-2026` is selected.
2. Click **`📄 Generate PDF Dossier`** (or **`🌐 Generate HTML Dossier`**).
3. The report opens/downloads: show the 6 structured audit sections:
   1. Executive Summary & Telemetry
   2. Ingested Evidence Inventory (with SHA-256 hashes)
   3. Forensic Observations & Visual Anomalies
   4. Cross-Document Discrepancy Matrix
   5. Extracted Information & Field Confidence
   6. Evidence & Traceability (with bounding box crops)

> **Talking Point:**
> *"When an investigation concludes, VEXORA generates a publication-ready forensic dossier in vector PDF or HTML. The dossier includes complete cryptographic custody hashes, extracted field confidence scores, side-by-side discrepancy tables, and embedded evidence crops ready for submission to regulatory authorities or legal counsel."*

---

### ⏱️ 4:00 – 4:30 | Safe Degradation & AI Layer
**Action:** Click **"Settings"** in the sidebar.
1. Show the **AI Health & Diagnostics** card.
2. Click **`⚡ Test AI Connection`**.
3. If an API key is set, observe latency and model name (`gemini-2.5-flash`). If running offline, observe the clean, explicit diagnostic status message without application failure.

> **Talking Point:**
> *"Finally, VEXORA is architected for safe degradation. When an LLM API key is present, our AI layer provides grounded explanations Disarmed of prompt-injection threats. But if offline or unconfigured, VEXORA never crashes—it operates with 100% deterministic local heuristics. All code, tests, and documentation are transparent and verifiable."*

---

## Quick Reference Summary Table for Judges

| Feature | Where to See It | Technical Anchor |
|---|---|---|
| **1-Click Demo Seed** | Topbar: `⚡ Load Demo Case` | `tools/reset_demo.py` / `POST /api/demo/reset` |
| **Multi-Format Ingestion & SHA-256** | Library / Dossier Section 2 | `backend/uploader.py` |
| **Typographic & Spatial Forensics** | Document Forensics | `backend/analyzer.py` (`RULE-VIS-001..005`) |
| **PDF Stream & Metadata Forensics** | Document Forensics | `backend/forensics_pdf.py` (`PDF-001..005`) |
| **Pixel Image Forensics (ELA / ORB)** | Document Forensics | `backend/forensics_image.py` (`IMG-001..004`) |
| **Visual Evidence Zoom/Pan Modal** | `🔍 View Evidence` Button | `frontend/js/v2.js` (`#v2EvidenceModal`) |
| **Cross-Document Discrepancy Matrix** | Cross-Document Comparison | `backend/comparator.py` |
| **Interactive Relational Graph** | Relationship Graph | `backend/correlator.py` |
| **6-Section Vector Dossier (PDF/HTML)** | Case Dossiers | `backend/reporter.py` |
| **Sequential Audit Trail (CSV/JSON)** | Audit Trail | `GET /api/audit-logs/export` |
| **Empirical Evaluation Benchmark** | `tools/evaluate.py` | 100% Case Precision / 0 Genuine False Alarms |

