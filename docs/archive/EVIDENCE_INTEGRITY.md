# VEXORA — Digital Evidence Integrity & Cryptographic Chain of Custody

**Standard Alignment:** Aligned with ISO/IEC 27037:2012 principles (Digital Evidence Handling & Chain of Custody; not an accredited third-party certification)  
**Security Tier:** Append-Only Cryptographic Audit Trail & Strict Layer Separation  
**Implementation Modules:** `backend/database.py`, `backend/models.py`, `backend/extractor.py`

---

## 1. ISO/IEC 27037 Digital Evidence Alignment

In judicial, regulatory, and corporate investigations, forensic observations are worthless if the evidence chain of custody can be disputed. VEXORA adheres to the core tenets of ISO/IEC 27037:

1. **Relevance & Acquisition:** The original evidence artifact is ingested without alteration.
2. **Identification & Sealing:** At ingest time, a cryptographic SHA-256 digest is generated and recorded for tamper detection.
3. **Integrity Verification:** Periodic verification recomputes file hashes to detect physical disk tampering.
4. **Traceability:** Every investigator action, OCR extraction, analytical scan, and report generation is cryptographically chained.

---

## 2. Append-Only Hash-Chained Audit Trail

To prevent malicious insiders or attackers with database access from altering historical investigation records, VEXORA implements an **append-only hash chain** directly within SQLite.

### 2.1 Cryptographic Chain Formulation

Each record in `audit_logs` contains:
- `prev_hash`: The `event_hash` of the immediately preceding record.
- `event_hash`: The SHA-256 cryptographic digest of the current record sealed with `prev_hash`.

$$\text{event\_hash}_i = \text{SHA-256}\left(\text{prev\_hash}_i \parallel \text{timestamp}_i \parallel \text{action}_i \parallel \text{entity\_type}_i \parallel \text{entity\_id}_i \parallel \text{details}_i \parallel \text{user}_i\right)$$

For the initial event ($i = 0$), the chain anchors to a defined genesis constant:
$$\text{prev\_hash}_0 = \text{"GENESIS\_00000000000000000000000000000000000000000000000000000000"}$$

### 2.2 Tamper Detection Algorithm

The verification engine (`verify_audit_trail_integrity()`) performs a complete linear chain traversal:
1. Validates that $\text{prev\_hash}_i == \text{event\_hash}_{i-1}$ for all $i \ge 1$.
2. Recomputes $\text{event\_hash}_i$ from the raw field values and verifies $\text{recomputed} == \text{stored}$.
3. If an attacker:
   - Modifies any action, actor, timestamp, or details $\rightarrow$ **Hash mismatch detected**.
   - Inserts a rogue log entry $\rightarrow$ **Chain broken detected**.
   - Deletes an intermediate log entry $\rightarrow$ **Preceding hash mismatch detected**.

Tested and verified in `tests/test_integrity_custody.py` (`test_audit_hash_chain_tamper_detection`).

### 2.3 Storage Architecture & Immutability Disclosure

> **Forensic Integrity Note on Storage Immutability:**  
> The append-only hash chain provides application-level *tamper-evidence*—any retroactive modification, insertion, or deletion breaks cryptographic linkage and is detected during integrity verification (`verify_audit_trail_integrity()`). However, because SQLite executes within the local host filesystem, this constitutes application-layer tamper-evidence rather than hardware-enforced Write-Once-Read-Many (WORM) or independently immutable cloud object locking.

---

## 3. Strict Forensic Data Separation

A critical vulnerability in legacy forensic systems is data contamination—where synthetic annotations, OCR hallucinated text, or downstream rule descriptions pollute the ground-truth extracted text.

VEXORA maintains strict separation across distinct database columns and data structures:

| Data Slot | Storage Column / Key | Source | Contamination Barrier |
| :--- | :--- | :--- | :--- |
| **`extracted_text`** | `documents.extracted_text` | PyMuPDF text stream or raw Tesseract output | **100% Verbatim document text only**. No rule IDs, synthetic labels, or AI opinions. |
| **`ocr_text`** | `pages[i].text` (when `ocr_applied=True`) | Tesseract OCR engine | Quarantined per page; flagged with `ocr_confidence`. |
| **`metadata`** | `documents.metadata` | PDF trailers / image EXIF | Key-value pairs (`Producer`, `CreationDate`, `Author`). |
| **`visual_observations`** | `findings.evidence` | ELA, noise maps, copy-move clusters | Visual bounding coordinates and difference maps. |
| **`forensic_findings`** | `findings` table | Deterministic forensic rule engine | Structured anomaly records with rule IDs and severity. |
| **`synthetic_descriptions`**| `ai_insights.data` | Optional LLM contextual explanations | Stored in dedicated `ai_insights` table with mandatory disclaimers. |

Tested and verified in `tests/test_integrity_custody.py` (`test_strict_ocr_data_separation`).

---

## 4. Coordinate Transformation Under PDF Rotation

Documents frequently undergo 90°, 180°, or 270° clockwise rotations during scanning or printing:

1. **Orientation Detection:** PyMuPDF extracts `page.rotation` (0, 90, 180, 270).
2. **Dimension Transformation:** For 90° or 270° rotations, the page width and height dimensions are transposed ($W \leftrightarrow H$) to match the visual viewport coordinate space.
3. **Bounding Box Normalization:** Text blocks extracted via `page.get_text("blocks")` automatically align with the rotated orientation:
   $$0 \le x_0 < x_1 \le W_{\text{rotated}}, \quad 0 \le y_0 < y_1 \le H_{\text{rotated}}$$
4. **Metadata Preservation:** The exact rotation angle is preserved in each page extraction dictionary (`'rotation': int(page.rotation)`), enabling dynamic frontend viewer canvases to render overlay highlights at the precise visual location.

Tested and verified in `tests/test_integrity_custody.py` (`test_coordinate_transformation_under_rotation`).

