# VEXORA — Known Limitations, Assumptions, and Edge Cases

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

---

## 2. Technical Limitations by Subsystem

### 2.1 Optical Character Recognition (OCR)
- **Tesseract Host Dependency:** OCR capability relies on the presence of a functional Tesseract-OCR binary on the operating system PATH. In environments lacking Tesseract, the system operates in fallback mode (`extraction_mode="simulated_fallback"` or `"ocr_unavailable"` under `VEXORA_STRICT_OCR=True`).
- **Low-Resolution Degradation:** Images below 150 DPI or with severe motion blur, sensor noise, or uneven lighting experience substantial token loss and character confusion (e.g. `8` misread as `B`, `0` as `O`, or decimals dropped from monetary figures).
- **Handwriting Inability:** VEXORA does not possess a deep handwritten text recognition (HTR) model. Cursive and freeform handwritten notes are treated as unparsed image regions or noisy low-confidence OCR artifacts.

### 2.2 Image Forensics (ELA, ORB, Sharpness)
- **Synthetic vs. Camera Sensor Mismatch (False Alarms):**
  - Pure digital graphics (such as receipts or badges generated directly in graphic design software or via script) feature mathematically uniform color regions without optical sensor noise.
  - When subjected to Error Level Analysis (ELA) or Laplacian sharpness tiling, these uniform digital regions can exhibit high relative compression difference or low high-frequency variance, resulting in false alarms on legitimate digital assets.
- **Copy-Move Cloned Stamp Detection (`IMG-003`):**
  - Uses OpenCV ORB keypoint descriptor matching. While effective at detecting duplicate physical stamps or signatures copied across the same page, repetitive background textures (such as guilloche security borders, fine gridlines, or dense dot-matrix patterns) can generate false keypoint clusters.
- **Multiple Compression Cycles:**
  - Documents forwarded across messaging platforms (e.g. WhatsApp, Slack, email) undergo aggressive lossy re-compression, smoothing out original forensic compression artifacts and reducing ELA sensitivity.

### 2.3 PDF Primitives Forensics
- **Benign Modification Date Divergence (`PDF-001`):**
  - Many enterprise PDF viewing and archiving tools (such as Adobe Acrobat Reader, Foxit, or automated document indexing services) update the `/ModDate` timestamp when a file is opened, signed, or printed to a virtual printer, even if no document content is altered.
- **Benign Multi-Font Typography (`RULE-VIS-001`, `PDF-002`):**
  - Modern marketing and corporate branding guidelines frequently utilize distinct font families for headers, body paragraphs, and financial summary callouts. Such design choices are flagged as potential typographic anomalies by automated visual heuristics and require human investigator verification.
- **Cad and Form Optional Content (`PDF-004`):**
  - PDFs exported from engineering or architectural software (AutoCAD, Revit) legitimately use `/OCProperties` (Optional Content Layers) for layer visibility. These layers trigger `PDF-004` as a structural notice.

### 2.4 Contextual Intelligence & Fuzzy Matching
- **Date Ambiguity (`RULE-CTX-003`):**
  - Numeric date formats lacking year-month-day explicitness (e.g. `05/06/2026`) are parsed using standard ISO and Western conventions (`DD/MM/YYYY` or `MM/DD/YYYY`). Without explicit regional locale metadata, date sequence heuristics may misinterpret day and month.
- **Fuzzy Counterparty Name False Positives (`fuzzy_party_similarity`):**
  - Corporate names sharing extensive corporate nomenclature (e.g. "Global Logistics Solutions Inc" and "National Logistics Solutions LLC") may achieve similarity ratios near the 0.80 threshold. VEXORA surfaces these as heuristic observations rather than definitive matches.
- **Single-Document Blind Spots:**
  - Certain tampering strategies—such as issuing two conflicting invoices with the identical invoice number `INV-999` to two different counterparties—are completely invisible during isolated single-document analysis and can only be uncovered when running cross-document case comparison.

---

## 3. Likely False Positive Triggers & Investigator Guidance

| Scenario | Triggered Rule | Underlying Cause | Recommended Investigator Action |
|---|---|---|---|
| Modern branded invoice with sans-serif headers and serif totals | `RULE-VIS-001` / `PDF-002` | Intentional typographic design hierarchy | Check whether all fonts are licensed by the same publisher and embedded cleanly. |
| Re-exported PDF from cloud document repository | `RULE-CTX-005` / `PDF-001` | Cloud repository stamped export time into metadata | Correlate `/ModDate` with document body date; verify repository export logs. |
| Clean digital screenshot or flat PNG receipt | `IMG-001` / `IMG-002` | Absence of natural camera sensor noise | Verify receipt source; check transaction ID directly against point-of-sale records. |
| Dense legal contract table with thin cell borders | `RULE-VIS-002` | Mathematical bounding box intersection on borders | View highlighted coordinates in Visual Evidence Overlay to confirm if text is actually obscured. |
| Invoice with separate discount, freight, and tax line items | `RULE-CTX-004` | Simple line-item sum does not match grand total due to unparsed freight/discount lines | Examine line items in document text; verify whether additional statutory fees explain the variance. |

---

## 4. Ethical & Legal Boundaries

1. **No Adjudication of Intent:**
   - Software cannot establish *mens rea* (criminal intent). A font mismatch may be the result of a clumsy document forgery, an innocent template update, or a software font fallback substitution. VEXORA labels all findings as **observations** or **potential anomalies**.
2. **Human-in-the-Loop Requirement:**
   - VEXORA is an investigative assistance tool. All findings, AI explanations, and cross-document discrepancy matrices must be reviewed and corroborated by a qualified forensic document examiner or forensic accountant before any legal or disciplinary action is taken.
