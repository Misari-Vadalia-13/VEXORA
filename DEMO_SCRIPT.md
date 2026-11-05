# VEXORA — Live Judge Demonstration Script (3–5 Minutes)

This script is designed for a concise, high-impact, live evaluation by hackathon judges. It walks through every primary capability of the **VEXORA Document Forensics and Contextual Intelligence Platform**.

---

## Pre-Flight Check (30 Seconds Before Demo)

1. Open a terminal in the project directory:
   ```powershell
   .\.venv\Scripts\python.exe -m backend.app
   ```
2. Open your browser to: **`http://127.0.0.1:5000`**
3. Verify the topbar displays:
   - System title: `VEXORA // FORENSIC INTELLIGENCE ENGINE`
   - Data status: `Data saved locally` (SQLite persistence indicator)
   - OCR status: `⚠️ OCR unavailable - fallback mode` (or `Verified OCR Engine` if Tesseract is installed)
   - AI status: `🤖 AI reasoning: OFF (deterministic mode)` (or `Gemini 2.5 Flash` if API key is active)

---

## Demo Script

### ⏱️ 0:00 – 0:45 | Introduction & 1-Click Demo Seed
**Action:** Click the topbar button: **`📁 Add Demo Case`** (or **`⚡ Reset & Load Demo`**).

> **Talking Point:**
> *"Judges, document fraud in financial procurement, corporate mergers, and legal disputes rarely happens in isolation. A single invoice might look completely clean, yet when correlated with purchase orders and bank statements across a case, massive discrepancies and chronological contradictions emerge.*
> 
> *VEXORA combines low-level PDF vector primitives, OCR glyph coordinate mapping, pixel-level computer vision forensics, and cross-document relational intelligence.*
> 
> *Notice that with one click of **Load Demo Case**, VEXORA just ingested a multi-document procurement case: an invoice, a duplicate vendor invoice, a commercial bank statement, and a purchase order. Each document was cryptographically digested with a SHA-256 hash upon intake."*

---

### ⏱️ 0:45 – 1:45 | Dynamic Forensic Inspector & Evidence Overlays
**Action:** Click **"Forensic Inspection"** in the sidebar (`#forensics`).
1. In the **Document Selector**, select `tampered_01_font_shift.pdf` (or `tampered_02_whitebox_patch.png`).
2. Point out the **Live Document Viewer**:
   - Extraction Mode Badge: **`⚡ Hybrid OCR`** (or `📄 Native Digital` / `📷 Scanned OCR`).
   - Page navigation: `◀ Page 1 of 1 ▶`, Zoom `+ / -`, and `🔤 Text` transcript toggle.
3. Point out the **Evidence Integrity & Chain of Custody Card**:
   - Shows cryptographic SHA-256 with one-click `📋 Copy`.
   - Click **`🔍 Verify Integrity`**: the backend re-hashes the stored disk file and returns a verified green badge: `✓ Hash matches (ISO/IEC 27037 compliant)`.
   - Expand the **`📜 Chain of Custody Timeline`** to show the immutable sequence of intake, extraction, and verification events.
4. Point out the **Forensic Taxonomy Badges**:
   - `Potential Manipulation` (Red badge)
   - `Inconsistency` (Amber badge)
   - `Observation` (Blue badge)
5. On any visual finding card, click the **`🔍 View Evidence`** button.
6. The Evidence Modal opens: demonstrate the amplified **Error Level Analysis (ELA) heatmap** or physical bounding box coordinates on the page.

> **Talking Point:**
> *"Here in the Forensic Inspector, VEXORA analyzes the document primitives. Notice our strict forensic taxonomy: we never assert speculative claims of 'confirmed fraud.' Findings are classified objectively as Observations, Inconsistencies, or Potential Manipulations.*
> 
> *Notice the dynamic viewer on the left: it highlights the extraction engine mode (Hybrid OCR vs Native Digital) and renders real page overlays. With one click on 'Verify Integrity', VEXORA recomputes the SHA-256 hash against the disk file to guarantee chain of custody alignment under ISO/IEC 27037 standards.*
> 
> *When we inspect visual evidence, VEXORA isolates the exact coordinates on the page where typographic shifts or ELA compression anomalies occurred. Every finding is verifiable and tied directly to physical source geometry."*

---

### ⏱️ 1:45 – 2:45 | Cross-Document Comparison & Chronological Timeline
**Action:** Click **"Cross-Doc Compare"** in the sidebar (`#comparison`).
1. In the comparison selectors, select Document A (`tampered_04_duplicate_inv_a.pdf`) and Document B (`tampered_05_duplicate_inv_b.pdf`).
2. Click **`Run Cross-Check`**.
3. Observe the live discrepancy matrix appear immediately:
   - Primary Monetary Value: `$5,000.00` vs `$7,500.00`
   - Counterparty mismatch: `Apex Global Industries` vs `Apex Global Solutions`
   - Near-duplicate variant detection: Jaccard token similarity score.
4. Scroll down to the **Investigation Chronology & Temporal Timeline**:
   - Point out the **Temporal Sequence Anomaly Warning**:
     `⚠️ [RULE-TIME-001] Pre-Dated Commercial Invoice: Invoice INV-2026-0891 (2026-02-10) issued prior to Purchase Order PO-2026-0412 (2026-02-15) authorization.`
   - Point out the vertical chronological timeline tracking events from PO authorization to invoice issuance to bank settlement.

> **Talking Point:**
> *"Now let's examine why single-document analysis fails in real-world fraud. Documents A and B are two invoices. Taken individually, both appear 100% mathematically and typographically clean.*
> 
> *When we run our Cross-Document Comparator, VEXORA cross-references their entity graphs. It immediately catches the duplicate invoice submission: the same invoice number has been billed twice for different amounts to different legal entities.*
> 
> *Furthermore, our Chronological Timeline Synthesizer catches out-of-order temporal anomalies: notice the red alert banner flagging that the invoice was predated 5 days before the authorizing Purchase Order even existed. That is the power of cross-document contextual intelligence."*

---

### ⏱️ 2:45 – 3:30 | Multi-Document Relationship Graph
**Action:** Under Cross-Doc Compare, view the **Cross-Document Relationship Graph**.
1. Select case `CAS-DEMO-2026` in the dropdown (or click `🔄 Refresh`).
2. An interactive SVG network displays nodes and edges connecting documents, counterparties, bank accounts, and transactions.
3. Click or hover over nodes to inspect details in the inspector card.

> **Talking Point:**
> *"VEXORA synthesizes cross-document evidence into an interactive relationship graph rendered in pure SVG without heavy external visualization dependencies. Investigators can visually trace how an invoice connects to a purchase order, an authorized signatory, and a cleared bank statement line item."*

---

### ⏱️ 3:30 – 4:15 | Audit-Ready Dossier Generation
**Action:** Click **"Case Dossiers"** in the sidebar (`#dossier`).
1. Ensure `CAS-DEMO-2026` is selected.
2. Click **`📄 Generate PDF Dossier`** (or **`🌐 Generate HTML Dossier`**).
3. The report opens/downloads: show the 6 structured audit sections:
   1. Executive Summary & Telemetry
   2. Ingested Evidence Inventory (with cryptographic SHA-256 hashes)
   3. Forensic Observations & Visual Anomalies
   4. Cross-Document Discrepancy Matrix
   5. Extracted Information & Field Confidence
   6. Evidence & Traceability with embedded crops & ISO/IEC 27037 custody log

> **Talking Point:**
> *"When an investigation concludes, VEXORA generates a publication-ready forensic dossier in vector PDF or HTML. The dossier includes complete cryptographic custody hashes, extracted field confidence scores, side-by-side discrepancy tables, and embedded evidence crops ready for submission to regulatory authorities or legal counsel."*

---

### ⏱️ 4:15 – 4:45 | Safe Degradation, Privacy & Evaluation Benchmarks
**Action:** Click **"System Settings"** in the sidebar (`#settings`).
1. Show the **AI Health & Diagnostics** card.
2. Click **`🤖 Test AI Connection`**: displays latency and model name, or clean deterministic fallback.
3. Show the **Benchmark Evaluation Results** in `reports/benchmark_results.json`.

> **Talking Point:**
> *"Finally, VEXORA is architected with complete transparency and defense-in-depth security:*
> - *Every line of code is protected against path traversal and role escalation.*
> - *Our optional AI layer enforces strict verbatim quote validation and automatic PII masking (IBAN, card, ID numbers).*
> - *Our automated benchmark achieves 85% single-document accuracy, 100% case-level correlation accuracy, and 100% specificity with zero false alarms across genuine files.*
> - *Our test suite features 250 passing unit tests and 12/12 passing end-to-end checks.*
> *Thank you, judges. We welcome your questions."*

---

## Quick Reference Summary Table for Judges

| Feature | Where to See It | Technical Anchor |
|---|---|---|
| **1-Click Demo Seed** | Topbar: `⚡ Load Demo Case` / `📁 Add Demo Case` | `tools/reset_demo.py` (`POST /api/demo/reset`) |
| **Hybrid Ingestion & Extraction Mode** | Forensic Inspector Header | `backend/extractor.py` (`hybrid_pdf`) |
| **Evidence Integrity & Chain of Custody** | Forensic Inspector Card | `backend/evidence.py` (`GET /api/documents/<id>/integrity`) |
| **Dynamic Document Viewer & Overlays** | Forensic Inspector Canvas | `backend/evidence.py` (`GET /api/documents/<id>/pages/<n>/overlay`) |
| **Pixel Image Forensics (ELA / ORB)** | `🔍 View Evidence` Modal | `backend/forensics_image.py` (`IMG-001..005`) |
| **PDF Structural Stream Forensics** | Document Forensics Feed | `backend/forensics_pdf.py` (`PDF-001..006`) |
| **Cross-Document Discrepancy Matrix** | Cross-Doc Compare View | `backend/comparator.py` |
| **Chronological Timeline & Sequence Anomalies** | Cross-Doc Compare View | `backend/correlator.py` (`RULE-TIME-001..002`) |
| **Interactive SVG Relationship Graph** | Relationship Graph Panel | `backend/correlator.py` |
| **6-Section Vector Dossier (PDF/HTML)** | Case Dossiers View | `backend/reporter.py` |
| **Empirical Evaluation Benchmark** | `reports/benchmark_results.json` | 85.0% Doc Acc / 100% Case Acc / 100% Specificity |
| **Automated Test Coverage** | Terminal: `python -m unittest` | **250 Unit Tests** / **12/12 E2E Checks** |
