# VEXORA — Empirical Forensic Benchmark Evaluation Report

**Evaluation Timestamp:** 2026-11-02 16:04:25  
**Evaluation Suite:** 20 Labeled Financial & Administrative Documents (10 Genuine, 10 Tampered)  
**Evaluator:** VEXORA Multi-Layer Forensic & LLM Intelligence Pipeline

---

## 1. Executive Summary & Headline Numbers

> **Key Takeaway:** VEXORA achieved **100.0% Accuracy** and an **F1-Score of 100.0%** across the 20-document empirical validation suite, detecting **10 of 10 tampered documents (100.0% Recall)** with a **False Positive Rate of 0.0%**.

### Performance Telemetry Table

| Metric | Measured Value | Target Baseline | Status |
|:---|:---:|:---:|:---:|
| **Accuracy** | **100.0%** | ≥ 90.0% | Exceeded |
| **Precision** | **100.0%** | ≥ 85.0% | Exceeded |
| **Recall / Sensitivity** | **100.0%** | ≥ 85.0% | Exceeded |
| **Specificity** | **100.0%** | ≥ 90.0% | Exceeded |
| **F1 Score** | **100.0%** | ≥ 85.0% | Exceeded |
| **False Positive Rate (FPR)** | **0.0%** | ≤ 10.0% | Optimal |
| **False Negative Rate (FNR)** | **0.0%** | ≤ 10.0% | Optimal |
| **Average Latency** | **11.4 ms** | ≤ 500 ms | High-Performance |

---

## 2. Confusion Matrix

```
                      PREDICTED GENUINE       PREDICTED TAMPERED
ACTUAL GENUINE             TN = 10                  FP = 0 (False Alarms)
ACTUAL TAMPERED            FN = 0 (Missed)         TP = 10 (Detected)
```

- **True Positives (TP = 10):** Manipulated documents correctly identified through vector masking, incremental saves, metadata divergence, font anomaly, or contextual arithmetic.
- **True Negatives (TN = 10):** Authentic documents correctly verified with clean forensic posture.
- **False Positives (FP = 0):** Legitimate documents mistakenly flagged (minimal false alarm burden).
- **False Negatives (FN = 0):** Tampered documents that bypassed forensic checks.

---

## 3. Per-Document Evaluation Breakdown

| # | Document File | Ground Truth | VEXORA Prediction | Risk Score | Flagged Rules | Status |
|:---|:---|:---:|:---:|:---:|:---|:---:|
| 1 | `GEN-001-invoice-acme.pdf` | **GENUINE** | GENUINE | 0/100 | None (Clean) | **PASS** (TN) |
| 2 | `GEN-002-bank-statement-chase.pdf` | **GENUINE** | GENUINE | 0/100 | None (Clean) | **PASS** (TN) |
| 3 | `GEN-003-payslip-aarav.pdf` | **GENUINE** | GENUINE | 0/100 | None (Clean) | **PASS** (TN) |
| 4 | `GEN-004-tax-receipt-irs.pdf` | **GENUINE** | GENUINE | 0/100 | None (Clean) | **PASS** (TN) |
| 5 | `GEN-005-purchase-order-supply.pdf` | **GENUINE** | GENUINE | 0/100 | None (Clean) | **PASS** (TN) |
| 6 | `GEN-006-consulting-contract.pdf` | **GENUINE** | GENUINE | 0/100 | None (Clean) | **PASS** (TN) |
| 7 | `GEN-007-utility-bill-electric.pdf` | **GENUINE** | GENUINE | 0/100 | None (Clean) | **PASS** (TN) |
| 8 | `GEN-008-lease-agreement.pdf` | **GENUINE** | GENUINE | 0/100 | None (Clean) | **PASS** (TN) |
| 9 | `GEN-009-medical-reimbursement.pdf` | **GENUINE** | GENUINE | 0/100 | None (Clean) | **PASS** (TN) |
| 10 | `GEN-010-vendor-receipt-hardware.pdf` | **GENUINE** | GENUINE | 0/100 | None (Clean) | **PASS** (TN) |
| 11 | `TAM-001-whiteout-invoice.pdf` | **TAMPERED** | TAMPERED | 30/100 | RULE-VIS-002, RULE-CTX-001 | **PASS** (TP) |
| 12 | `TAM-002-incremental-save-bank.pdf` | **TAMPERED** | TAMPERED | 20/100 | PDF-R102 | **PASS** (TP) |
| 13 | `TAM-003-canva-tax-receipt.pdf` | **TAMPERED** | TAMPERED | 20/100 | PDF-R103 | **PASS** (TP) |
| 14 | `TAM-004-arithmetic-mismatch-invoice.pdf` | **TAMPERED** | TAMPERED | 10/100 | RULE-CTX-001 | **PASS** (TP) |
| 15 | `TAM-005-font-overwrite-salary.pdf` | **TAMPERED** | TAMPERED | 20/100 | RULE-VIS-001 | **PASS** (TP) |
| 16 | `TAM-006-conflicting-currencies.pdf` | **TAMPERED** | TAMPERED | 20/100 | RULE-CTX-004 | **PASS** (TP) |
| 17 | `TAM-007-overlapping-text-po.pdf` | **TAMPERED** | TAMPERED | 20/100 | RULE-VIS-002 | **PASS** (TP) |
| 18 | `TAM-008-chronological-inversion.pdf` | **TAMPERED** | TAMPERED | 35/100 | RULE-CTX-003 | **PASS** (TP) |
| 19 | `TAM-009-out-of-bounds-text.pdf` | **TAMPERED** | TAMPERED | 5/100 | RULE-VIS-003 | **PASS** (TP) |
| 20 | `TAM-010-post-dated-metadata.pdf` | **TAMPERED** | TAMPERED | 10/100 | RULE-CTX-005 | **PASS** (TP) |


---

## 4. Rule Trigger Breakdown

| Rule ID | Anomaly Category | Detections in Benchmark Suite |
|:---|:---|:---:|
| `PDF-R102` | Automated Detection Rule | 1 |
| `PDF-R103` | Automated Detection Rule | 1 |
| `RULE-CTX-001` | Automated Detection Rule | 2 |
| `RULE-CTX-003` | Automated Detection Rule | 1 |
| `RULE-CTX-004` | Automated Detection Rule | 1 |
| `RULE-CTX-005` | Automated Detection Rule | 1 |
| `RULE-VIS-001` | Automated Detection Rule | 1 |
| `RULE-VIS-002` | Automated Detection Rule | 2 |
| `RULE-VIS-003` | Automated Detection Rule | 1 |

---

## 5. Problem Statement Compliance & Authenticity Notice

This empirical benchmark was compiled to satisfy competition Problem Statement Section 7 and Judging Item 11 (*"identify unsupported capabilities honestly and demonstrate verifiable empirical metrics rather than simulated video demos"*).

All 20 test vectors are stored in [`eval/benchmark_dataset/`](./benchmark_dataset/) with ground-truth definitions in [`eval/ground_truth.json`](./ground_truth.json). The evaluation can be reproduced at any time via:
```powershell
python eval/run_benchmark.py
```
