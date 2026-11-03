# VEXORA — Known Limitations, Assumptions, and Empirical Benchmark

Forensic integrity requires transparent disclosure of operational boundaries. VEXORA does not claim infallibility, does not issue legal verdicts of "fraud," and explicitly documents the technical conditions under which its automated heuristics may yield false alarms or miss subtle alterations.

---

## 1. Core Operating Assumptions

1. **English Language Documents:**
   - All OCR dictionaries, contextual regex heuristics, named entity recognition (NER) patterns, and statutory field checklists are calibrated exclusively for English commercial, legal, and identity documents.
   - Non-Latin orthographies (e.g. Cyrillic, Arabic, Chinese, Devanagari) and non-English commercial idioms are not supported and will produce unparsed or low-confidence tokens.

2. **Standard Document Layouts:**
   - Contextual rules assume standard Western commercial formatting (e.g. clear demarcations for Issue Date, Due Date, Subtotal, Tax, Grand Total).
   - Highly abstract, artistic, or non-standard invoice templates may lack recognizable statutory anchors and trigger `RULE-CTX-001` (Missing Statutory Fields).

3. **Digital vs. Physical Forensics Boundary:**
   - VEXORA analyzes the digital representation of documents (PDF stream dictionaries, font descriptor tables, raster compression matrices, and optical character geometry).
   - It cannot verify physical paper chemistry, watermark ink luminescence, or microscopic fiber indentations that require physical laboratory examination.

4. **Synthetic Demonstration Dataset:**
   - The included evaluation benchmark consists of 20 programmatically generated synthetic files (`demo_dataset/`) created by `tools/make_samples.py` to illustrate specific anomaly classes. It does not represent real-world paper scans or historical forensic archives.

---

## 2. Technical Limitations by Subsystem

### 2.1 Optical Character Recognition (OCR)
- **Tesseract Host Dependency:** OCR capability relies on the presence of a functional Tesseract-OCR binary on the operating system PATH. In environments lacking Tesseract, the system operates in fallback mode (`extraction_mode="simulated_fallback"` or `"ocr_unavailable"` under `VEXORA_STRICT_OCR=True`).
- **Low-Resolution Degradation:** Images below 150 DPI or with severe motion blur, sensor noise, or uneven lighting experience substantial token loss and character confusion (e.g. `8` misread as `B`, `0` as `O`, or decimals dropped from monetary figures).
- **Handwriting Inability:** VEXORA does not possess a deep handwritten text recognition (HTR) model. Cursive and freeform handwritten notes are treated as unparsed image regions or noisy low-confidence OCR artifacts.

### 2.2 Image Forensics (ELA, ORB, Sharpness)
- **Principled Gate & Scope:**
  - Image forensics rules (`IMG-001`, `IMG-002`, `IMG-003`) execute strictly on standalone raster image uploads (`png`, `jpg`, `tiff`, `bmp`) and raster images embedded inside PDFs.
  - Born-digital PDF vector text pages are explicitly excluded from pixel-level raster forensics, because rasterizing clean vector fonts creates artificial compression and sharpness boundaries that produce false positives.
- **Synthetic vs. Camera Sensor Mismatch (False Alarms):**
  - Pure digital graphics (such as receipts or badges generated directly via script or graphic design software) feature mathematically uniform color fills lacking optical sensor noise.
  - When subjected to Error Level Analysis (ELA) or Laplacian sharpness tiling, these uniform digital regions exhibit sharp mathematical contrast, resulting in false alarms on legitimate digital assets.
- **Copy-Move Cloned Stamp Detection (`IMG-003`):**
  - Uses OpenCV ORB keypoint descriptor matching. While matches within detected text regions are filtered out to avoid matching repeated font letters, repetitive background textures (such as guilloche security borders, fine gridlines, or identical corporate logos) can generate false keypoint clusters.
- **Multiple Compression Cycles:**
  - Documents forwarded across messaging platforms (e.g. WhatsApp, Slack, email) undergo aggressive lossy re-compression, smoothing out original forensic compression artifacts and reducing ELA sensitivity.

### 2.3 PDF Primitives Forensics
- **Benign Modification Date Divergence (`PDF-001`):**
  - Many enterprise PDF viewing and archiving tools (such as Adobe Acrobat Reader, Foxit, or automated document indexing services) update the `/ModDate` timestamp when a file is opened, signed, or printed to a virtual printer, even if no document content is altered.
- **Benign Multi-Font Typography (`RULE-VIS-001`, `PDF-002`):**
  - Modern marketing and corporate branding guidelines frequently utilize distinct font families for headers, body paragraphs, and financial summary callouts. Such design choices are flagged as potential typographic anomalies by automated visual heuristics and require human investigator verification.
- **CAD and Form Optional Content (`PDF-004`):**
  - PDFs exported from engineering or architectural software (AutoCAD, Revit) legitimately use `/OCProperties` (Optional Content Layers) for layer visibility. These layers trigger `PDF-004` as a structural notice.
- **Benchmark Coverage:**
  - Rules `PDF-001`, `PDF-002`, `PDF-004`, and `PDF-005` pass their unit tests on targeted synthetic test PDFs, but do not fire on the 20-file benchmark dataset because those specific files do not contain incremental xref revisions, subset font injections, or hidden layers. Only `PDF-003` (software metadata signatures) fires on the demo dataset.

### 2.4 Contextual Intelligence & Fuzzy Matching
- **Date Ambiguity (`RULE-CTX-003`):**
  - Numeric date formats lacking year-month-day explicitness (e.g. `04/05/2026`) are parsed using standard Western conventions (`DD/MM/YYYY` or `MM/DD/YYYY`). Without explicit regional locale metadata, date sequence heuristics may misinterpret day and month.
- **Fuzzy Counterparty Name False Positives (`fuzzy_party_similarity`):**
  - Corporate names sharing extensive corporate nomenclature (e.g. "Global Logistics Solutions Inc" and "National Logistics Solutions LLC") may achieve similarity ratios near the 0.80 threshold. VEXORA surfaces these as heuristic observations rather than definitive matches.
- **Single-Document Blind Spots:**
  - Certain tampering strategies—such as duplicate invoice numbers issued to different clients or invoices that contradict bank transaction amounts—are completely undetectable in isolated single-document analysis and require cross-document case comparison.

---

## 3. Empirical Benchmark Performance & Measured Metrics

The evaluation benchmark (`tools/evaluate.py`) was executed across the 20 demonstration documents (`demo_dataset/`) and 3 cross-document case scenarios (`demo_dataset/cases.csv`). The measured, unvarnished results are recorded below:

### 3.1 Single-Document Isolated Benchmark (20 Synthetic Files)

| Metric | Measured Value | Forensic Interpretation |
|---|---|---|
| **Total Test Documents** | 20 | 10 Genuine Documents, 10 Tampered Documents |
| **Accuracy** | **60.0%** | Overall correct classifications across single files |
| **Recall (Detection Rate)** | **70.0%** | 7 of 10 tampered documents detected |
| **Precision** | **58.3%** | 7 of 12 flagged documents were truly tampered |
| **Specificity (Clean Rate)** | **50.0%** | 5 of 10 genuine documents correctly passed as clean |
| **F1-Score** | **63.6%** | Harmonic mean of precision and recall |

#### Honest Analysis of the 5 False Positives (Alarms on Genuine Files):
1. `genuine_01_invoice.pdf`: Flagged by `RULE-CTX-001` (missing mandatory statutory fields due to non-standard layout) and `RULE-VIS-001` (minor font size hierarchy shifts).
2. `genuine_02_invoice.pdf`: Flagged by `RULE-CTX-002` (round dollar amount heuristic triggered on exact $5,000.00 total).
3. `genuine_06_contract.pdf`: Flagged by `RULE-CTX-001` (missing statutory invoice fields, as contracts omit invoice-specific payment terms).
4. `genuine_08_receipt.png`: Flagged by `IMG-001` (ELA) and `IMG-002` (Sharpness variance) because flat computer-generated image fills lack camera sensor noise and produce sharp synthetic compression edges.
5. `genuine_09_id_card.png`: Flagged by `IMG-001` (ELA) and `IMG-002` (Sharpness variance) for the same synthetic pixel reasons.

#### Honest Analysis of the 3 False Negatives (Missed Tampered Files):
1. `tampered_04_duplicate_inv_a.pdf`
2. `tampered_05_duplicate_inv_b.pdf`
3. `tampered_06_bank_mismatch.pdf`

*Why single-document analysis missed them:* Each of these documents is internally consistent, grammatically correct, and mathematically valid in isolation. `tampered_04` and `tampered_05` are clean invoices that only become fraudulent when compared against each other (duplicate invoice numbers submitted to different vendors). `tampered_06` is a clean invoice whose tampering only exists because it conflicts with bank statement `genuine_03`. Single-document analysis cannot detect cross-document fraud.

---

### 3.2 Cross-Document Case-Level Benchmark (3 Multi-Document Scenarios)

When documents are evaluated within multi-document investigation cases using the Cross-Document Comparator (`backend/comparator.py`) and Correlation Graph (`backend/correlator.py`), the benchmark measures:

| Metric | Measured Value | Forensic Interpretation |
|---|---|---|
| **Total Test Cases** | 3 | 1 Genuine Case, 2 Tampered Cases |
| **Case-Level Accuracy** | **100.0%** | All 3 multi-document scenarios correctly classified |
| **Case Recall (Detection)** | **100.0%** | Both tampered multi-document cases detected |
| **Case Precision** | **100.0%** | Zero false alarm cases |
| **Case Specificity** | **100.0%** | Clean procurement case correctly verified |
| **Case F1-Score** | **100.0%** | Perfect harmonic balance across case scenarios |

#### Why Case-Level Correlation Reached 100%:
- **Case 01 (`case_01_duplicate_invoices`):** Compares `tampered_04` and `tampered_05`. The comparator detects conflicting primary monetary totals ($5,000.00 vs $7,500.00) and conflicting counterparties under the exact same invoice number `INV-2026-999`.
- **Case 02 (`case_02_bank_mismatch`):** Compares `genuine_03_bank_statement.pdf` and `tampered_06_bank_mismatch.pdf`. The comparator identifies a $2,250.00 discrepancy between the invoice total ($14,250.00) and the cleared bank debit ($12,000.00).
- **Case 03 (`case_03_clean_procurement`):** Compares `genuine_01_invoice.pdf` and `genuine_05_purchase_order.pdf`. Identifies matching invoice identifiers, aligned totals ($1,250.00), and identical counterparties with zero discrepancies.

---

## 4. Likely False Positive Triggers & Investigator Guidance

| Scenario | Triggered Rule | Underlying Cause | Recommended Investigator Action |
|---|---|---|---|
| Modern branded invoice with sans-serif headers and serif totals | `RULE-VIS-001` / `PDF-002` | Intentional typographic design hierarchy | Check whether all fonts are licensed by the same publisher and embedded cleanly. |
| Re-exported PDF from cloud document repository | `RULE-CTX-005` / `PDF-001` | Cloud repository stamped export time into metadata | Correlate `/ModDate` with document body date; verify repository export logs. |
| Clean digital screenshot or flat PNG receipt | `IMG-001` / `IMG-002` | Absence of natural camera sensor noise | Verify receipt source; check transaction ID directly against point-of-sale records. |
| Dense legal contract table with thin cell borders | `RULE-VIS-002` | Mathematical bounding box intersection on borders | View highlighted coordinates in Visual Evidence Overlay to confirm if text is actually obscured. |
| Invoice with separate discount, freight, and tax line items | `RULE-CTX-004` | Simple line-item sum does not match grand total due to unparsed freight/discount lines | Examine line items in document text; verify whether additional statutory fees explain the variance. |

---

## 5. Ethical & Legal Boundaries

1. **No Adjudication of Intent:**
   - Software cannot establish *mens rea* (criminal intent). A font mismatch may be the result of a clumsy document forgery, an innocent template update, or a software font fallback substitution. VEXORA labels all findings as **observations** or **potential anomalies**.
2. **Human-in-the-Loop Requirement:**
   - VEXORA is an investigative assistance tool. All findings, AI explanations, and cross-document discrepancy matrices must be reviewed and corroborated by a qualified forensic document examiner or forensic accountant before any legal or disciplinary action is taken.
3. **Audit Trail Integrity:**
   - The SQLite `audit_log` records system events sequentially by application convention. It is not a cryptographic blockchain or tamper-proof hardware ledger. In production deployments, it must be protected by OS-level access control and regular off-site replication.
