# VEXORA — Forensic Boundaries & Limitations Disclosure

Forensic integrity requires transparent disclosure of scientific, technological, and algorithmic limitations. This document outlines the explicit boundaries of **VEXORA** (*AI-Powered Document Forensics and Contextual Intelligence System*).

---

## 1. Single-Document Isolation vs. Cross-Document Correlation

### The "Internally Genuine" Anomaly Paradox
When an individual document is analyzed in isolation, certain high-impact financial and forensic anomalies cannot be detected mathematically.

**Empirical Evidence from VEXORA Evaluation Benchmark:**
- In the 20-document benchmark suite (`tools/evaluate.py`), single-document forensic analysis achieved **85.0% Accuracy** (7/10 True Positives, 3 False Negatives, 0 False Positives).
- The 3 undetected documents (`tampered_04_duplicate_inv_a.pdf`, `tampered_05_duplicate_inv_b.pdf`, and `tampered_06_bank_mismatch.pdf`) are **100% genuine, vector-rendered digital documents** when examined by themselves:
  - `tampered_04` and `tampered_05`: Both invoices contain flawless fonts, valid metadata, no vector overwrites, and correct internal arithmetic. The anomaly is that *the same invoice number was issued to two different corporate counterparties with differing payment totals*. This duplicate collision is completely invisible without counterpart document comparison.
  - `tampered_06`: A bank statement that is internally clean and arithmetic-balanced, but whose credit line contradicts the payment total in the procurement invoice.
- **The Solution:** When evaluated as a cohesive case via VEXORA's **Cross-Document Comparator & Correlator**, the system achieves **100.0% Accuracy, 100.0% Recall, and 100.0% Precision**, identifying the duplicate collision and monetary variance immediately.

---

## 2. Optical Character Recognition (OCR) Boundaries

1. **Resolution Thresholds:**
   VEXORA rasterizes scanned PDF pages at 200 DPI (`zoom=2.78`) with Pillow autocontrast enhancement. Scanned documents below 150 DPI or severely downsampled web thumbnails may exhibit degraded character recognition or missing bounding boxes.
2. **Handwriting vs. Typography:**
   Tesseract OCR is optimized for printed Latin typography and standard business letterheads. Freeform cursive handwriting, complex calligraphic signatures, and handwritten marginalia may yield low confidence scores or unextracted text blocks.
3. **Severe Perspective Distortion & Skew:**
   While VEXORA includes automatic contrast enhancement, physical scans with extreme rotation (> 45 degrees) or severe barrel/keystone perspective warping should be pre-straightened for optimal coordinate precision.

---

## 3. Pixel-Level Image Tampering Heuristics

1. **Error Level Analysis (ELA) Limitations:**
   - ELA evaluates the difference between an image and its recompressed version at 90% JPEG quality.
   - Legitimate actions—such as resaving an image through email clients, messaging platforms, or document scanners—can introduce uniform or localized compression artifacts that resemble visual tampering.
   - For this reason, VEXORA classifies ELA findings as **`Observation`** with **`Medium`** severity, and always provides visual difference heatmaps so human investigators can inspect the actual compression distribution.
2. **Copy-Move ORB Keypoint Matching:**
   - Repetitive geometric patterns (such as dotted guide lines, invoice grid borders, or patterned security backgrounds) can generate spurious keypoint clusters.
   - VEXORA incorporates collinear point rejection and text-line masking to suppress false alarms, but highly repetitive decorative borders may occasionally trigger advisory observations.

---

## 4. Heuristics vs. Judicial Proof

- **Automated Triage, Not Legal Proof:**
  VEXORA does not issue verdicts of "confirmed fraud" or "guilty forgery." Every output is an automated heuristic observation, discrepancy metric, or potential manipulation indicator designed to assist a qualified forensic investigator.
- **Standard of Review:**
  All findings must be confirmed by a certified Forensic Document Examiner (FDE) or authorized digital forensic analyst before being admitted as legal evidence or used in adversarial proceedings.

---

## 5. Storage & Audit Architecture Boundaries

- **Database Engine:**
  VEXORA utilizes SQLite (`backend/vexora.db`) with process-level mutex locks (`@_synchronized_model`). While reliable for investigative desktop workstations and departmental deployments, SQLite is not a distributed high-throughput enterprise database cluster.
- **Audit Logging Convention:**
  The `audit_logs` table records chronological actions via application convention. It does not claim formal compliance with hardware Write-Once-Read-Many (WORM) storage, hardware security modules (HSM), or cryptographic distributed consensus ledgers.

---

## 6. Optional AI Reasoning Engine Boundaries

- **Triage Assistant Status:**
  The external LLM reasoning layer (Google Gemini / OpenAI) is strictly an advisory intelligence synthesizer. It assists investigators by generating plain-language summaries, formulating plausible innocent hypotheses, and suggesting verification steps.
- **Anti-Hallucination Constraints:**
  Although VEXORA enforces verbatim source-quote substring matching to discard ungrounded assertions, AI responses must never be used as autonomous or unreviewed decisions.
