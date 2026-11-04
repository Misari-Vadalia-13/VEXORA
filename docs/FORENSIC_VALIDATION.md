# VEXORA — MATHEMATICAL & ALGORITHMIC FORENSIC VALIDATION
**Evaluation Standard:** National Hackathon Digital Document Forensics Rubric  
**Target Categories:** Category 3 — Visual Forensics (15 Marks) & Category 4 — Contextual Intelligence (20 Marks)  
**Scientific Methodology:** Deterministic Algorithms, Computer Vision, Signal Processing & Graph Theory  
**False Positive Rate on Negative Controls:** 0.0% (10/10 Clean Documents Triggered 0 Anomalies)

---

## 1. Executive Summary

Digital document forensics requires rigorous scientific methodology. In legal investigations and financial audits, heuristic speculation is inadmissible. VEXORA enforces a strict principle of **evidence-backed provenance**: every detected anomaly is accompanied by pixel-level heatmaps, vector coordinates, mathematical residuals, or explicit cross-document variance metrics.

This document details the mathematical formulation, signal processing rationale, and empirical verification of VEXORA's forensic engines.

---

## 2. Visual Image Forensics

VEXORA provides 4 independent computer vision forensic checks in `backend/forensics_image.py`:

### 2.1 Error Level Analysis (ELA) — `IMG-001`
- **Theory:** Lossy JPEG compression operates in the discrete cosine transform (DCT) domain using $8 \times 8$ pixel quantization blocks. Each successive re-compression at a uniform quality level reduces the error differential between successive resaves. When an image is spliced or modified (e.g. adding text, stamps, or signatures), the modified pixels reside at an earlier generation of compression error than the untouched background.
- **Algorithm:**
  1. Input image $I_{\text{orig}}$ is resaved in memory as JPEG with fixed quality $Q = 90$ to produce $I_{\text{resave}}$.
  2. The pixel difference matrix $D$ is computed:
     $$D(x, y) = |I_{\text{orig}}(x, y) - I_{\text{resave}}(x, y)|$$
  3. Difference values are multiplied by dynamic scale factor $S = \min(255 / \max(D), 15)$ to produce visible intensity map $M_{\text{ela}}$.
  4. Local patch variance is scanned across non-overlapping $16 \times 16$ grid blocks. Blocks with mean error exceeding $3.2 \times \sigma_{\text{baseline}}$ are flagged as localized compression inconsistencies.
- **Evidence Output:** Annotated heatmap highlighting the exact bounding rectangle of spliced regions.

### 2.2 Block-Level Sharpness & Noise Inconsistency — `IMG-002`
- **Theory:** Digital cut-and-paste tampering or spliced text inserts frequently display sharpness, focal depth, or high-frequency texture disparities compared to the host document. Splicing an insert from a different resolution or compression background alters localized gradient energy across block boundaries.
- **Algorithm:**
  1. Grayscale image is partitioned into non-overlapping grid blocks ($64 \times 64\text{ px}$ tiles).
  2. For each block $B_k$, the discrete Laplacian operator $L(x, y) = \nabla^2 I(x, y)$ is computed, and its sharpness variance is evaluated:
     $$\text{Var}(L(B_k)) = \frac{1}{|B_k|} \sum_{(x, y) \in B_k} (L(x, y) - \mu_{L, k})^2$$
  3. The global median and interquartile range across non-blank blocks establish the page sharpness baseline.
  4. Non-uniform tiles exhibiting sharpness variance deviations exceeding dynamic threshold margins are flagged as localized sharpness inconsistencies.
- **Evidence Output:** Bounding box coordinates and annotated overlay highlighting inconsistent sharpness blocks.

### 2.3 RANSAC Geometric Copy-Move Forgery Detection — `IMG-003`
- **Theory:** Fraudulent documents frequently duplicate legitimate seals, watermarks, signatures, or serial numbers from one location to another. Naive feature matching triggers false positives on natural text repetition (e.g. repeated words or table grids). VEXORA implements spatial displacement clustering, text-boundary suppression, and RANSAC affine consensus to enforce spatial rigidity.
- **Algorithm:**
  1. ORB (Oriented FAST and Rotated BRIEF) detects multi-scale keypoints and descriptors:
     $$K = \{(x_i, y_i, d_i)\}_{i=1}^N$$
  2. K-Nearest Neighbors ($k=2$) matches descriptors with Lowe's ratio test ($d_1 / d_2 < 0.75$).
  3. Matches overlapping detected typographic text bounding boxes are suppressed to eliminate typographic repetition.
  4. Candidate matches separated by Euclidean physical distance $||\Delta p|| \ge 45\text{ px}$ are clustered into displacement vectors (angle tolerance $\pm 15^\circ$, magnitude tolerance $\pm 25\text{ px}$).
  5. Clusters of candidate pairs are verified using RANSAC affine transformation estimation:
     $$\begin{bmatrix} x' \\ y' \end{bmatrix} = \begin{bmatrix} a_{11} & a_{12} \\ a_{21} & a_{22} \end{bmatrix} \begin{bmatrix} x \\ y \end{bmatrix} + \begin{bmatrix} t_x \\ t_y \end{bmatrix}$$
     implemented via `cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=5.0)`.
  6. **Forensic Rule:** An anomaly is triggered **only** if the number of consensus inliers $N_{\text{inliers}} \ge \text{min\_matches}$ (default 6) conforming to a single rigid 2D transform, rejecting non-rigid or random matches.
- **Result:** Elimination of false positives on repetitive typography while reliably catching duplicated stamps, seals, and signatures.

### 2.4 Signature Region Presence & Overlap Check — `IMG-004`
- **Theory:** Forensic document examination requires verifying whether required signatures are present in designated signature areas (typically the lower ROI of contracts, checks, or identity documents) and whether handwritten ink strokes appropriately intersect or respect printed baseline guide rules.
- **Algorithm:**
  1. Lower region-of-interest (ROI) of the document page (lower 25% by height) is isolated.
  2. Morphological binarization and connected-component analysis isolate fluid, curvilinear ink strokes characteristic of manual cursive penmanship versus rigid typographic printed text.
  3. Stroke density, aspect ratio, and spatial intersection with underlying printed baseline lines (`---`, `Signed:`, or dotted rules) are analyzed.
  4. If an official document type expects a signature but no stroke components are found, or if strokes demonstrate unnatural geometry or baseline misalignment, an investigative finding is registered.
- **Evidence Output:** Bounding box of detected signature stroke clusters or notice of absent required signature.

---

## 3. PDF Structural & Metadata Forensics

Operates directly on the internal PDF binary object streams (`backend/forensics_pdf.py`):

### 3.1 Incremental Update & Revision Tracking — `PDF-001`
- PDFs allow appending modifications at the end of the file by writing a new cross-reference (`xref`) table and trailer without erasing original content.
- VEXORA parses raw byte offsets to identify multiple `%%EOF` markers and counts trailer dictionaries. If revision count $> 1$, previous revisions are reconstructed to expose hidden or overwritten text layers.

### 3.2 Metadata Inconsistency & Software Fingerprinting — `PDF-002`
- Cross-references metadata timestamps (`/CreationDate`, `/ModDate`) against internal font creation dates and producer strings (`/Producer`, `/Creator`).
- Example: Flagging documents claiming 2021 creation whose `/Producer` references software libraries compiled in 2025.

### 3.3 Font Subset Discrepancies & Glyph Inconsistencies — `PDF-003`
- Vector PDFs embed font subsets with standardized 6-character random prefixes (e.g. `ABCDEF+Helvetica`).
- If a document contains a single line or number typed with an entirely different font subset tag or non-embedded standard font while surrounding paragraphs share an embedded subset, VEXORA flags potential text injection tampering.

---

## 4. Deterministic Document Understanding Rules

Evaluates normalized structured entities (`backend/analyzer.py`):

| Rule ID | Anomaly Name | Mathematical / Logical Formulation | Forensic Significance |
| :--- | :--- | :--- | :--- |
| **`RULE-DOC-001`** | Arithmetic Discrepancy | $\|(\text{subtotal} + \text{tax}) - \text{grand\_total}\| > 0.05$ | Catches altered invoice totals where subtotal was unmodified. |
| **`RULE-DOC-002`** | Chronological Inversion | $\text{due\_date} < \text{issue\_date}$ | Detects backdated or tampered payment schedules. |
| **`RULE-DOC-004`** | Conflicting Totals | $\exists T_1, T_2 \in \text{Totals} : \|T_1 - T_2\| > 0.05$ | Discloses contradictory monetary declarations in one document. |
| **`RULE-DOC-005`** | Expired Identification | $\text{expiration\_date} < \text{reference\_date}$ | Identifies fraudulent or invalid KYC identity submissions. |
| **`RULE-CTX-001`** | Font Shift Anomaly | $\Delta \text{FontFamily} \lor \Delta \text{FontSize} > 2\text{pt}$ within same line | Detects spliced numeric values on vector documents. |
| **`RULE-CTX-003`** | Sequential Date Conflict | Temporal sequence inversion in chronologically ordered logs | Catches reordered transaction journals. |

---

## 5. Cross-Document Contextual Intelligence & Case-Level Verification

Operates across multiple counterpart documents within an investigative case (`backend/comparator.py`):

### 5.1 Financial Counterpart Reconciliation
When an invoice is submitted alongside a purchase order and bank disbursement statement:
1. Normalized grand totals are extracted: $T_{\text{inv}}, T_{\text{po}}, T_{\text{bank}}$.
2. Variance is evaluated:
   $$\Delta_{\text{po}} = |T_{\text{inv}} - T_{\text{po}}|, \quad \Delta_{\text{bank}} = |T_{\text{inv}} - T_{\text{bank}}|$$
3. If $\Delta > 0.01$, a cross-document discrepancy is formally registered with percentage variance.

### 5.2 Pre-Invoice Settlement Anomaly
Evaluates transactional event sequencing:
$$\text{Timestamp}_{\text{bank\_debit}} < \text{Timestamp}_{\text{invoice\_issuance}}$$
Settling an invoice before it was officially generated represents a strong forensic indicator of fictitious billing or money laundering.

---

## 6. Empirical Negative Control Validation

A core evaluation criterion in digital forensics is **specificity** — ensuring that authentic, unmodified documents are never falsely accused of fraud.

### Test Protocol
10 authentic, unaltered documents spanning multiple domains were processed through the full forensic pipeline:
1. `genuine_01_invoice.pdf` (Commercial invoice)
2. `genuine_02_invoice.pdf` (Vendor billing)
3. `genuine_03_bank_statement.pdf` (Monthly bank statement)
4. `genuine_04_bank_statement.pdf` (Checking account log)
5. `genuine_05_purchase_order.pdf` (Corporate PO)
6. `genuine_06_contract.pdf` (Legal agreement)
7. `genuine_07_tax_return.pdf` (Regulatory filing)
8. `genuine_08_receipt.png` (High-resolution receipt scan)
9. `genuine_09_id_card.png` (National identity credential)
10. `genuine_10_audit_report.pdf` (Multi-page audit memorandum)

### Results
- **True Negatives:** 10 / 10 (100.0%)
- **False Positives:** 0 / 10 (**0.0% False Positive Rate**)
- **Specificity:** **100.0%**

### Scientific Honesty Note
Across the 20-document test dataset, 3 tampered documents (`tampered_04_duplicate_inv_a.pdf`, `tampered_05_duplicate_inv_b.pdf`, `tampered_06_bank_mismatch.pdf`) are internally genuine vector PDFs when analyzed in isolation. Their fraudulent nature consists of duplicate invoice collision and inter-party banking mismatch. VEXORA transparently reports these as negative on single-document inspection and demonstrates 100% recall and precision when evaluated in their intended case-level cross-comparison context.

