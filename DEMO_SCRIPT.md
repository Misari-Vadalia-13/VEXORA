# VEXORA — Live Judge Demonstration Script (3–5 Minutes)

This script is designed for a concise, high-impact, live evaluation by hackathon judges. It walks through every primary capability of the **VEXORA Document Forensics and Contextual Intelligence Platform**.

---

## Pre-Flight Check (30 Seconds Before Demo)

1. Open a terminal in the project directory:
   ```powershell
   .\.venv\Scripts\python.exe -m backend.app
   ```
2. Open your browser to: **`http://127.0.0.1:5000`**
3. Click **`👤 Quick Demo Login`** in the topbar (logs in as `alex.turner`, Senior Forensic Specialist).
4. Verify the topbar displays:
   - System title: `VEXORA // FORENSIC INTELLIGENCE ENGINE`
   - Data status: `Data saved locally` (SQLite persistence indicator)
   - OCR status: `⚠️ OCR unavailable - fallback mode` (or `Verified OCR Engine` if Tesseract is installed)
   - AI status: `🤖 AI reasoning: OFF (deterministic mode)` (or `Gemini 2.5 Flash` if API key is active)
   - Logged-in badge: `Alex Turner (Senior Forensic Specialist)`

---

## Demo Walkthrough

### ⏱️ 0:00 – 0:45 | Introduction, 1-Click Demo Seed & Live Pipeline Stepper
**Action:** Click the topbar button: **`📁 Add Demo Case`** (or **`⚡ Reset & Load Demo`**).

> **Talking Point:**
> *"Judges, document fraud in financial procurement, corporate mergers, and legal disputes rarely happens in isolation. A single invoice might look completely clean, yet when correlated with purchase orders and bank statements across a case, massive discrepancies and chronological contradictions emerge.*
> 
> *Notice our live 7-stage pipeline stepper across the top: as soon as we click Load Demo Case, VEXORA ingests a multi-document procurement case. The pipeline stepper lights up in real time across all 7 analytical phases:*
> *1. Ingestion & Hashing $\to$ 2. PDF Structural Analysis $\to$ 3. Pixel Computer Vision $\to$ 4. Context Rules $\to$ 5. Cross-Doc Comparator $\to$ 6. Risk Scoring $\to$ 7. Dossier Synthesis.*
> 
> *Every document is cryptographically digested with a SHA-256 hash immediately upon intake, establishing an unbroken chain of custody."*

---

### ⏱️ 0:45 – 1:45 | Dynamic Forensic Inspector, Evidence Overlays & Reviewer Decisions
**Action:** Click **"Forensic Inspection"** in the sidebar (`#forensics`).
1. In the **Document Selector**, select `tampered_01_font_shift.pdf` (or `tampered_11_overwritten_text.pdf`).
2. Point out the **Live Document Viewer**:
   - Extraction Mode Badge: **`⚡ Hybrid OCR`** (or `📄 Native Digital` / `📷 Scanned OCR`).
   - Page navigation: `◀ Page 1 of 1 ▶`, Zoom `+ / -`, and `🔤 Text` transcript toggle.
3. Point out the **Evidence Integrity & Chain of Custody Card**:
   - Shows cryptographic SHA-256 with one-click `📋 Copy`.
   - Click **`🔍 Verify Integrity`**: the backend re-hashes the stored disk file and returns a verified green badge: `✓ Hash matches (ISO/IEC 27037 compliant)`.
   - Expand the **`📜 Chain of Custody Timeline`** to show the immutable sequence of intake, extraction, and verification events.
4. Point out the **Forensic Taxonomy Badges**:
   - `Potential manipulation` (Red badge)
   - `Detected inconsistency` (Amber badge)
   - `Observed` (Blue badge)
5. On any visual finding card, click the **`🔍 View Evidence`** button:
   - The Evidence Modal opens: demonstrate the physical bounding box coordinates and the high-resolution crop extracted via `/api/documents/<id>/crop`.
6. Demonstrate **Human Reviewer Decision Tracking**:
   - In the finding card, select **"Confirmed Tampering"** from the Review Decision dropdown.
   - Enter an investigator note (e.g., *"Confirmed baseline font shift on total row"*).
   - Click **`Save Review`**: the decision, note, reviewer username, and timestamp persist immediately into the database and are stamped onto future dossier exports.

> **Talking Point:**
> *"Here in the Forensic Inspector, VEXORA analyzes the document primitives. Notice our strict forensic taxonomy: we never assert speculative claims of 'confirmed fraud.' Findings are classified objectively as Observed, Detected Inconsistency, or Potential Manipulation.*
> 
> *With one click on 'Verify Integrity', VEXORA recomputes the SHA-256 hash against the disk file to guarantee chain of custody alignment under ISO/IEC 27037 principles.*
> 
> *Furthermore, we believe AI should assist human investigators, not replace them. Examiners can record formal review decisions—Confirmed Tampering, Benign / False Alarm, or Inconclusive—directly on each finding card, complete with auditable investigator notes."*

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

### ⏱️ 2:45 – 3:30 | Multi-Document Relationship Graph & Explainable Risk Scoring
**Action:** Under Cross-Doc Compare, view the **Cross-Document Relationship Graph**, then open **Case Risk Score**.
1. Select case `CAS-DEMO-2026` in the graph dropdown (or click `🔄 Refresh`).
2. An interactive SVG network displays nodes and edges connecting documents, counterparties, bank accounts, and transactions without heavy JavaScript charting libraries.
3. In **Case Management**, click the **`⚡ Risk Score`** button on `CAS-DEMO-2026`:
   - The **Explainable Risk Breakdown Modal** opens.
   - Shows the exact deterministic formula:
     $$\text{Score} = \min(100, (\text{Critical} \times 30) + (\text{High} \times 20) + (\text{Medium} \times 10) + (\text{Low} \times 5) + (\text{Discrepancies} \times 25))$$
   - Displays component breakdown (e.g., 2 Critical findings: +60 pts, 1 High finding: +20 pts, 1 Discrepancy: +25 pts $\to$ Clamped at 100 / Critical Priority).
   - Shows mandatory triage disclaimer: *"Triage priority, not a fraud verdict. Requires qualified human examiner review."*

> **Talking Point:**
> *"Investigators face hundreds of cases daily. To prioritize triaging without black-box AI hallucinations, VEXORA computes a transparent, explainable Case Risk Score from 0 to 100.*
> 
> *Every single point is mathematically accounted for: judges can click the score to see the exact formula, finding counts, and cross-document discrepancy weights. It serves strictly as a triage priority tool, explicitly disclaiming autonomous fraud verdicts."*

---

### ⏱️ 3:30 – 4:15 | Audit-Ready Dossier Generation
**Action:** Click **"Case Dossiers"** in the sidebar (`#dossier`).
1. Ensure `CAS-DEMO-2026` is selected.
2. Click **`📄 Generate PDF Dossier`** (or **`🌐 Generate HTML Dossier`**).
3. The report opens/downloads: show the 6 structured audit sections:
   1. Executive Summary & Case Risk Score Breakdown
   2. Ingested Evidence Inventory (with cryptographic SHA-256 hashes)
   3. Forensic Observations & Visual Anomalies (with standardized badges & reviewer sign-offs)
   4. Cross-Document Discrepancy Matrix
   5. Extracted Information & Field Confidence
   6. Evidence & Traceability with embedded crops & ISO/IEC 27037 custody log

> **Talking Point:**
> *"When an investigation concludes, VEXORA generates a publication-ready forensic dossier in vector PDF or HTML. The dossier includes complete cryptographic custody hashes, extracted field confidence scores, side-by-side discrepancy tables, reviewer decisions, and embedded evidence crops ready for submission to regulatory authorities or legal counsel."*

---

### ⏱️ 4:15 – 4:45 | Safe Degradation, Privacy & Evaluation Benchmarks
**Action:** Click **"System Settings"** in the sidebar (`#settings`).
1. Show the **AI Health & Diagnostics** card:
   - Click **`🤖 Test AI Connection`**: displays latency and model name, or clean deterministic fallback.
2. Open `reports/benchmark_results.json` or terminal evaluation summary.

> **Talking Point:**
> *"Finally, VEXORA is architected with complete transparency and defense-in-depth security:*
> - *Every line of code is protected against path traversal, IDOR, and role escalation.*
> - *Our optional AI layer enforces strict verbatim quote validation and automatic PII masking (IBAN, card, ID numbers).*
> - *Our automated benchmark achieves 94.3% single-document accuracy, 90.0% recall, and 100% precision with zero false alarms across genuine files, plus 100% case-level correlation accuracy.*
> - *Our test suite features 263 passing unit tests and 12/12 passing end-to-end checks.*
> *Thank you, judges. We welcome your questions."*

---

## Quick Reference Summary Table for Judges

| Feature | Where to See It | Technical Anchor |
|---|---|---|
| **1-Click Demo Login** | Topbar: `👤 Quick Demo Login` | `POST /api/auth/demo-login` (`alex.turner`) |
| **1-Click Demo Seed** | Topbar: `⚡ Load Demo Case` / `📁 Add Demo Case` | `tools/reset_demo.py` (`POST /api/demo/reset`) |
| **Live 7-Stage Pipeline Stepper** | Topbar Stepper Bar | `#pipelineStepper` (`frontend/js/app.js`) |
| **Hybrid Ingestion & Extraction Mode** | Forensic Inspector Header | `backend/extractor.py` (`hybrid_pdf`) |
| **Evidence Integrity & Chain of Custody** | Forensic Inspector Card | `backend/evidence.py` (`GET /api/documents/<id>/integrity`) |
| **Dynamic Document Viewer & Overlays** | Forensic Inspector Canvas | `backend/evidence.py` (`GET /api/documents/<id>/pages/<n>/overlay`) |
| **Pixel Image Forensics (ELA / ORB)** | `🔍 View Evidence` Modal & `/api/documents/<id>/crop` | `backend/forensics_image.py` (`IMG-001..005`) |
| **PDF Structural Stream Forensics** | Document Forensics Feed | `backend/forensics_pdf.py` (`PDF-001..006`) |
| **Standardized 3-Part Finding Cards** | Forensic Findings List | `backend/explainability.py` (`Observed`, `Inconsistency`, `Manipulation`) |
| **Reviewer Decision Tracking** | Finding Card Review Form | `POST /api/findings/<id>/review` (`models.py`) |
| **Cross-Document Discrepancy Matrix** | Cross-Doc Compare View | `backend/comparator.py` |
| **Chronological Timeline & Sequence Anomalies** | Cross-Doc Compare View | `backend/correlator.py` (`RULE-TIME-001..002`) |
| **Interactive SVG Relationship Graph** | Relationship Graph Panel | `backend/correlator.py` |
| **Explainable Case Risk Scoring** | Case Management Modal | `backend/risk_scoring.py` (`GET /api/cases/<id>/risk-score`) |
| **6-Section Vector Dossier (PDF/HTML)** | Case Dossiers View | `backend/reporter.py` |
| **Empirical Evaluation Benchmark** | `reports/benchmark_results.json` | 94.3% Doc Acc / 90.0% Recall / 100% Prec / 100% Case Acc |
| **Automated Test Coverage** | Terminal: `python -m unittest` | **263 Unit Tests** / **12/12 E2E Checks** (100% pass) |
