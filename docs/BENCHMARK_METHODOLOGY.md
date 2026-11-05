# VEXORA — Benchmark Evaluation Methodology & Forensic Performance Report

**Date:** November 2026  
**Evaluation Standard:** Zero-Tolerance Digital Forensics & Multi-Document Contextual Correlation  
**Benchmark Suite:** `tools/evaluate.py`  
**Dataset Directory:** `demo_dataset/` (20 verified documents, 3 multi-document cases)

---

## 1. Unified 5-Artifact Benchmark Pipeline

Every run of `tools/evaluate.py` produces an interconnected, reproducible suite of **5 forensic artifacts** in the `reports/` directory:

```
reports/
├── benchmark_results.json    # Complete machine-readable telemetry & metadata
├── benchmark_results.csv     # Granular per-document verification verdicts
├── benchmark_report.md       # Formatted Markdown audit dossier with Markdown tables
├── confusion_matrix.json     # Dedicated 2x2 confusion matrices (document & case levels)
├── benchmark_summary.txt     # High-level ASCII summary for CLI / terminal review
└── archive/                  # Historical timestamped run archives
```

### 1.1 Historical Run Archival
When evaluating against `reports/`, previous benchmark results are automatically archived to `reports/archive/benchmark_results_{TIMESTAMP}.json` and `.csv` before being overwritten. This provides historical reproducibility without data loss.

### 1.2 Test Contamination Isolation
Unit tests (`tests/test_evaluator.py`) pass an isolated temporary directory (`tempfile.mkdtemp()`) to `export_benchmark_reports(..., output_dir=temp_dir)`. This guarantees that executing automated unit tests or CI pipelines never pollutes or overwrites production benchmark artifacts.

---

## 2. Mathematical Metric Definitions & Zero-Division Safety

All performance indicators are computed by `compute_binary_metrics()` with defensive zero-division checks:

$$\text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}$$

$$\text{Precision} = \frac{TP}{TP + FP} \quad (\text{defaults to } 0.0\% \text{ if } TP + FP = 0)$$

$$\text{Recall (Sensitivity)} = \frac{TP}{TP + FN} \quad (\text{defaults to } 0.0\% \text{ if } TP + FN = 0)$$

$$\text{Specificity} = \frac{TN}{TN + FP} \quad (\text{defaults to } 0.0\% \text{ if } TN + FP = 0)$$

$$F_1\text{-Score} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}} \quad (\text{defaults to } 0.0\% \text{ if denominator } = 0)$$

### 2x2 Confusion Matrix Format:
```
                 ┌─────────────────────────────────────────────────────────┐
                 │                    PREDICTED VERDICT                    │
                 ├────────────────────────────┬────────────────────────────┤
                 │ Predicted Genuine/Clean    │ Predicted Tampered/Anomaly │
┌────────────────┼────────────────────────────┼────────────────────────────┤
│ Actual Clean   │ True Negative (TN)         │ False Positive (FP)        │
├────────────────┼────────────────────────────┼────────────────────────────┤
│ Actual Anomaly │ False Negative (FN)        │ True Positive (TP)         │
└────────────────┴────────────────────────────┴────────────────────────────┘
```

---

## 3. Verified Benchmark Results

### 3.1 Document-Level Forensic Performance (Isolated Documents)
Evaluates each document independently against physical, visual, and PDF metadata tampering:

| Metric | Verified Value | Definition |
| :--- | :---: | :--- |
| **Total Evaluated** | **20** | 10 Genuine, 10 Tampered |
| **True Positives (TP)** | **7** | Detected anomalous/tampered documents |
| **True Negatives (TN)** | **10** | Correctly cleared genuine documents |
| **False Positives (FP)** | **0** | Zero false accusations of clean documents |
| **False Negatives (FN)** | **3** | Cross-document anomalies evaluated in isolation |
| **Accuracy** | **85.0%** | $(7 + 10) / 20 = 17 / 20$ |
| **Precision** | **100.0%** | $7 / (7 + 0)$ (Zero false alarms) |
| **Recall (Detection Rate)** | **70.0%** | $7 / (7 + 3)$ |
| **Specificity** | **100.0%** | $10 / (10 + 0)$ |
| **F1-Score** | **82.3%** | Harmonic mean of precision and recall |
| **Processing Failures** | **0** | 100% extraction pipeline yield |

#### Document-Level Confusion Matrix:
- **True Negatives (TN):** 10
- **False Positives (FP):** 0
- **False Negatives (FN):** 3
- **True Positives (TP):** 7

> **Forensic Scientific Explanation of the 3 False Negatives:**  
> The 3 undetected documents in isolated document testing (`tampered_04_duplicate_inv_a.pdf`, `tampered_05_duplicate_inv_b.pdf`, and `tampered_06_bank_mismatch.pdf`) are **100% internally genuine vector PDF files**. They contain valid fonts, valid metadata, consistent layouts, and no visual artifacts.  
> Their tampering consists exclusively of **duplicate invoice collisions** (two identical invoice numbers billed across different vendors) and **cross-document payment discrepancies** (bank statement transfer amounts diverging from purchase orders).  
> In digital forensics, isolated file inspection cannot detect duplicate collision without a counterpart document. When evaluated in multi-document cases (Section 3.2), **detection rises to 100%**.

---

### 3.2 Case-Level Contextual Intelligence Performance (Multi-Document)
Evaluates cross-document correlation, timeline reconstruction, and entity matching across multi-document cases:

| Metric | Verified Value | Definition |
| :--- | :---: | :--- |
| **Total Evaluated Cases** | **3** | 1 Genuine Case, 2 Tampered Cases |
| **True Positives (TP)** | **2** | `case_01_duplicate_invoices`, `case_02_bank_mismatch` |
| **True Negatives (TN)** | **1** | `case_03_clean_procurement` |
| **False Positives (FP)** | **0** | Clean procurement case passed without anomalies |
| **False Negatives (FN)** | **0** | Zero missed case discrepancies |
| **Case Accuracy** | **100.0%** | Perfect case-level classification |
| **Case Recall** | **100.0%** | All multi-document fraud patterns flagged |
| **Case Precision** | **100.0%** | Zero false accusations |
| **Case Specificity** | **100.0%** | Genuine procurement accurately cleared |
| **Case F1-Score** | **100.0%** | Optimal multi-document contextual intelligence |

#### Case-Level Confusion Matrix:
- **True Negatives (TN):** 1
- **False Positives (FP):** 0
- **False Negatives (FN):** 0
- **True Positives (TP):** 2

---

## 4. Rule-Level Classification Fidelity

Beyond binary classification, VEXORA tracks whether the **specific tampering rule** triggered matches the ground-truth annotation:

- **Total Annotated Documents:** 10
- **Exact Ground-Truth Rule Hits:** 3 (Exact specific rule matched ground truth)
- **Exact Rule Classification Accuracy:** 30.0%
- **Partial/Composite Detections:** 4 (Multiple overlapping rules fired, e.g. font anomaly + layout block displacement)
- **Active Rule Activations:**
  - `RULE-CTX-003` (Chronological Inversion): 2 document hits
  - `PDF-003` (PDF Metadata Divergence): 2 document hits
  - `RULE-CTX-001` (Font Family Discrepancy): 1 document hit
  - `RULE-VIS-001` (Font Metric Anomalies): 1 document hit
  - `IMG-002` (White-Box Patch Splicing): 1 document hit
  - `RULE-DOC-002` (Structural Bounding Anomaly): 1 document hit
  - `IMG-001` / `IMG-003` / `IMG-004` (Copy-Move Cloning & ELA): 1 document hit each

---

## 5. Strict Error Isolation Principle

Processing errors (such as unreadable corrupted files or missing binaries) are **strictly quarantined** and excluded from False Positive or False Negative counts:
- An unparseable file is flagged as `PROCESSING_ERROR` and recorded in the audit trail.
- It is never counted as an anomaly detection (which would artificially inflate True Positives).
- Across the 20 benchmark test documents, VEXORA achieved **0 processing failures** (100% extraction pipeline yield).

