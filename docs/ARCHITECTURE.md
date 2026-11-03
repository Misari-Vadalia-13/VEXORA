# VEXORA — System Architecture & Forensic Pipeline

## 1. High-Level Architecture Overview

VEXORA is an AI-powered forensic document intelligence platform designed to uncover typographic anomalies, physical image manipulations, statutory omissions, chronological contradictions, and cross-document discrepancies.

The system is constructed with a modular, layered architecture adhering strictly to forensic honesty: automated algorithms generate **heuristic observations** and **potential anomalies**, never speculative claims of "confirmed fraud." Every assertion is tied directly to its physical bounding box, page index, and verbatim source text.

---

## 2. Forensic Dataflow Pipeline (Mermaid Diagram)

```mermaid
flowchart TD
    %% Intake Layer
    subgraph Intake ["1. Document Intake & Storage"]
        Upload["File Upload (PDF / PNG / JPG / TIFF)"] --> Hash["SHA-256 Hash & Safe Sanitization"]
        Hash --> Store["Filesystem Storage (uploads/) & SQLite Metadata Registration"]
    end

    %% Pre-Processing Layer
    subgraph PreProcessing ["2. Intake Classification & Text Extraction"]
        Store --> Classify["Classification (Filename Heuristics + Content Fallback)"]
        Classify --> Extractor["Extraction Engine"]
        Extractor --> DigitalPDF["Native PDF Parsing (PyMuPDF / Character Spans)"]
        Extractor --> TesseractOCR["Optical Character Recognition (pytesseract image_to_data)"]
        Extractor --> FallbackMode["Fallback / Strict OCR Guard (VEXORA_STRICT_OCR)"]
    end

    %% Intelligence Layer
    subgraph Forensics ["3. Forensic Analysis & Verification Engines"]
        DigitalPDF --> NER["Rule & Regex Entity Extraction (ner.py)"]
        TesseractOCR --> NER
        FallbackMode --> NER
        NER --> EntityConf["Field-Level Confidence Calculation (entities table)"]

        EntityConf --> VisualRules["Visual & Typographic Forensics (RULE-VIS-001..005)"]
        EntityConf --> ContextRules["Contextual Inconsistency Engine (RULE-CTX-001..005)"]
        DigitalPDF --> PDFPrims["PDF Primitives Forensics (PDF-001..005)"]

        %% Principled Image Forensics Gate
        Store -.-> Gate{"Input Gate:\nRaster Upload or\nPDF Embedded Image?"}
        Gate -- Yes --> ImgForensics["Image Forensics (IMG-001 ELA, IMG-002 Sharpness, IMG-003 Copy-Move, IMG-004 Signature)"]
        Gate -- Born-Digital Vector Page --> SkipImg["Skip Raster Forensics (Exclude Born-Digital Text Pages)"]
    end

    %% Contextual Intelligence Layer
    subgraph CrossCheck ["4. Contextual Cross-Check & AI Reasoning"]
        VisualRules --> EvidenceDB[("Persist Findings (findings table)")]
        ContextRules --> EvidenceDB
        PDFPrims --> EvidenceDB
        ImgForensics --> EvidenceDB

        EvidenceDB --> Comparator["Cross-Document Comparator (comparator.py: Diff Values & Discrepancy Matrix)"]
        EvidenceDB --> Correlator["Cross-Document Correlator & Graph (correlator.py: Multi-Doc Network)"]
        EvidenceDB --> LLM["Configurable LLM Tier (backend/llm.py: VEXORA_LLM_MODEL / POST /api/system/ai-test)"]
        LLM --> HallucinationGuard["Anti-Hallucination Source Quote Grounding"]
    end

    %% Output & Traceability Layer
    subgraph Presentation ["5. Auditability, Complete Dossiers & UI"]
        EvidenceDB --> OverlayAPI["Visual Evidence Overlay API (/api/findings/id/evidence-image)"]
        Correlator --> SVGGraph["Interactive Vanilla SVG Relationship Graph"]
        Comparator --> MatrixUI["Discrepancy Matrix UI"]
        HallucinationGuard --> ExplainUI["Interactive AI Reasoning Explanations & Extracted Fields"]
        
        %% 5-Part Complete Dossier
        EvidenceDB & Comparator & Correlator & LLM --> DossierEngine["Comprehensive Dossier Engine (backend/reporter.py)"]
        DossierEngine --> SecK1["K1: Extracted Information & Confidence"]
        DossierEngine --> SecK2["K2: Evidence & Traceability with Overlays"]
        DossierEngine --> SecK3["K3: Plain-Language Investigation Summary"]
        DossierEngine --> SecK4["K4: Areas Requiring Further Verification"]
        DossierEngine --> SecK5["K5: Technical Boundaries & Limitations"]

        DossierEngine --> AuditTrail["SQLite Audit Trail (audit_log: Append-Only by Convention)"]
    end
```

---

## 3. Subsystem Breakdown

### 3.1 Document Ingestion & Safe Intake (`backend/uploader.py`)
- Accepts PDF documents and raster images (`png`, `jpg`, `jpeg`, `tiff`, `bmp`).
- Computes SHA-256 cryptographic digests upon upload to prevent duplicate collision attacks.
- Sanitizes filenames via `secure_filename` and enforces a 16MB maximum content payload.

### 3.2 Classification & Content Fallback (`backend/classifier.py`, `backend/classifier_content.py`)
- **Primary Stage:** Filename and keyword heuristics classify documents into standardized domains (`Invoice`, `Bank Statement`, `Purchase Order`, `Tax Return`, `Contract`, `Customs Declaration`).
- **Secondary Fallback:** If the primary stage returns `General Document` or `Uncategorized`, `classify_by_content` scans extracted text bodies for legal, banking, and accounting markers, refining the category without overriding filename rules.

### 3.3 Text Extraction & Confidence Scoring (`backend/extractor.py`, `backend/ner.py`)
- **Digital PDFs:** Extracted with character-level bounding boxes and font matrices via PyMuPDF (`pymupdf`). Confidence is marked as `"n/a (digital text)"` to distinguish mathematical font glyphs from OCR probabilities.
- **Scanned Images:** Processed via `pytesseract.image_to_data` extracting word-level confidence metrics (`0.0` - `100.0`). Extracted entities (monetary amounts, dates, IDs, organizations) compute an exact mathematical average of their constituent tokens.
- **Offline / Fallback Protection:** Under `VEXORA_STRICT_OCR=False`, missing OCR binaries gracefully report `extraction_mode="simulated_fallback"`; under `VEXORA_STRICT_OCR=True`, they return an explicit error and log the status without fabricating text.

### 3.4 Forensic Rule Engines
1. **Typographic & Visual Analysis (`backend/analyzer.py`):**
   - `RULE-VIS-001`: Font size and typeface anomalies across text lines.
   - `RULE-VIS-002`: Spatial collisions and overlapping text bounding boxes.
   - `RULE-VIS-003`: Altered baseline alignment within numerical strings.
   - `RULE-VIS-004`: Irregular spacing and character kerning shifts.
   - `RULE-VIS-005`: Low image resolution and scan degradation.
2. **PDF Primitives Analysis (`backend/forensics_pdf.py`):**
   - `PDF-001`: Incremental updates with divergent cross-reference modification timestamps.
   - `PDF-002`: Embedded font subset anomalies (isolated Type 1 or TrueType insertions).
   - `PDF-003`: Software manipulation signatures (e.g. Photoshop, GIMP, Canva, Illustrator).
   - `PDF-004`: Hidden optional content layers (`/OCProperties`).
   - `PDF-005`: Inconsistent page geometric dimensions (stitched multi-source scans).
3. **Image Frequency & Spatial Forensics (`backend/forensics_image.py`):**
   - **Principled Execution Gate:** `IMG-001` (ELA), `IMG-002` (Sharpness), and `IMG-003` (Copy-Move) run strictly on uploaded raster image files and raster images embedded inside PDFs (extracted via PyMuPDF `page.get_images()`). They are bypassed on born-digital PDF vector pages to prevent false alarms on rendered text.
   - `IMG-001`: Error Level Analysis (ELA) resaving image at 90% quality to detect compression anomalies. Capped at Medium severity.
   - `IMG-002`: Laplacian sharpness variance tiling detecting regional blurring or softening. Capped at Medium severity.
   - `IMG-003`: ORB keypoint descriptor matching detecting copy-move cloned stamps. Excludes detected text regions to avoid matching repeated font letters. Capped at Medium severity.
   - `IMG-004`: Contour aspect ratio analysis for signature region extraction.

### 3.5 Contextual Intelligence & Cross-Document Graph (`backend/comparator.py`, `backend/correlator.py`)
- **Pairwise Comparator:** Compares two documents within a case, extracting concrete discrepancy values (`attribute`, `doc_a_val`, `doc_b_val`) for monetary shifts, invoice ID clashes, and counterparty discrepancies.
- **Label-Aware Totals:** Distinguishes invoice grand totals and amounts due from intermediate line items.
- **Fuzzy Counterparty Matching:** Strips corporate suffixes (`LLC`, `Corp`, `Inc`, `Industries`) and computes sequence similarity ratios via Python standard library `difflib`.
- **Chronological Conflict Discovery:** Identifies impossible timeline events (e.g. payment settlement preceding invoice issue date).
- **Vanilla SVG Graph:** Renders a responsive, interactive SVG graph with document nodes, entity nodes, and typed correlation edges without external JavaScript graphing frameworks.

### 3.6 Grounded AI Reasoning Layer (`backend/llm.py`)
- Connects over pure HTTPS via standard `requests` to Google Gemini, Anthropic Claude, or OpenAI without heavy SDKs.
- **Configurable Model & Resilience:** Configurable via `VEXORA_LLM_MODEL` environment variable (defaults to `gemini-2.5-flash` for Gemini and `gpt-4o-mini` for OpenAI). Gracefully catches HTTP 404 / 400 "model not found" errors and provides actionable diagnostic remediation without application crashes.
- **Live Health Diagnostics:** Provides `POST /api/system/ai-test` endpoint and settings UI button to verify live credentials, latency, and model availability.
- **Privacy First:** Redacts PII (emails, phone numbers, long digit sequences) prior to outbound transmission. Transmits extracted text only; binary document files never leave the server.
- **Anti-Hallucination Quote Grounding:** Every extracted entity and explanation claim must match a verbatim substring from the source document text; claims failing this check are discarded.

### 3.7 Comprehensive Dossier & Auditability (`backend/reporter.py`)
- Compiles complete case evidence into a publication-ready report (Vector PDF via PyMuPDF/ReportLab or HTML).
- **Five Mandatory Problem Statement Sections:**
  1. **Extracted Information & Confidence (K1):** Tabulates extracted business fields with field-level confidence scores (`"n/a (digital text)"` or percentage OCR confidence) and bounding-box coordinates.
  2. **Evidence & Traceability with Overlays (K2):** Embedded evidence crops highlighting physical finding bounding boxes in red.
  3. **Investigation Plain-Language Summary (K3):** Objective overview of case status, document count, and anomaly severity breakdown.
  4. **Areas Requiring Further Verification (K4):** Actionable forensic checklist directing investigators to specific discrepancies, unverified line items, and missing metadata.
  5. **Technical Boundaries & Limitations (K5):** Explicit disclosure of heuristic limits, OCR bounds, and legal non-adjudication disclaimers.
- **Audit Trail:** Sequential SQLite `audit_log` recording all user and system operations (append-only by application convention).
