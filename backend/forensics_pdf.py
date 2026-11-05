"""
VEXORA — Extended PDF Forensics Module (Phase B)
Detects advanced PDF structural anomalies:
- PDF-001: Text hidden or occluded under filled/opaque vector shapes (white-box redaction)
- PDF-002: Incremental updates & post-creation revisions (multiple %%EOF markers)
- PDF-003: Metadata desynchronization (creation date vs modification date divergence)
- PDF-004: Embedded images superimposed over text or severe resolution disparity
- PDF-005: Invisible text elements (render mode 3) or text placed completely off-page

Produces findings in the exact same format as the baseline analyzer.
"""

import os
import re
import logging
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

from backend.evidence_class import get_evidence_class

logger = logging.getLogger(__name__)

# Extended Forensic Rules Catalog
EXTENDED_PDF_RULES = {
    'PDF-001': {
        'id': 'PDF-001',
        'title': 'Text Hidden Under Filled Vector Shape',
        'severity': 'High',
        'category': 'Visual Structure',
        'confidence': 0.92,
        'evidence_class': 'Potential Manipulation',
        'recommendation': 'Inspect occluded text to confirm whether original numerical or identifying values were covered by a vector shape.'
    },
    'PDF-002': {
        'id': 'PDF-002',
        'title': 'Incremental Updates Detected in File Body',
        'severity': 'Low',
        'category': 'Structural Integrity',
        'confidence': 0.85,
        'evidence_class': 'Observation',
        'recommendation': 'Verify whether document was re-saved or digitally signed after its initial compilation.'
    },
    'PDF-003': {
        'id': 'PDF-003',
        'title': 'Metadata Revision Desynchronization',
        'severity': 'Low',
        'category': 'Contextual Metadata',
        'confidence': 0.80,
        'evidence_class': 'Inconsistency',
        'recommendation': 'Examine differences between document body dates, PDF creation date, and PDF modification date.'
    },
    'PDF-004': {
        'id': 'PDF-004',
        'title': 'Embedded Image Superimposed Over Text Region',
        'severity': 'High',
        'category': 'Visual Structure',
        'confidence': 0.89,
        'evidence_class': 'Potential Manipulation',
        'recommendation': 'Check if raster image snippet (such as a signature stamp or patched logo) overlaps vector text.'
    },
    'PDF-005': {
        'id': 'PDF-005',
        'title': 'Hidden or Off-Page Text Element Detected',
        'severity': 'High',
        'category': 'Visual Structure',
        'confidence': 0.94,
        'evidence_class': 'Potential Manipulation',
        'recommendation': 'Inspect text elements located outside the printable page boundary or using invisible rendering mode.'
    },
    'PDF-006': {
        'id': 'PDF-006',
        'title': 'Suspicious Interactive or Executable Object',
        'severity': 'High',
        'category': 'Structural Integrity',
        'confidence': 0.95,
        'evidence_class': 'Potential Manipulation',
        'recommendation': 'Quarantine file and inspect embedded scripts, launch actions, or attached payloads in a sandboxed analysis environment.'
    }
}


# =====================================================================
# 1. Individual PDF Forensic Detectors
# =====================================================================

def check_text_hidden_under_shapes(doc):
    """
    PDF-001: Detects text blocks or spans that are covered or occluded
    by an opaque/filled vector drawing (such as a white rectangle pasted over text).
    """
    findings = []
    rule = EXTENDED_PDF_RULES['PDF-001']

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1

        drawings = page.get_drawings()
        if not drawings:
            continue

        # Extract text blocks
        p_dict = page.get_text("dict")
        blocks = p_dict.get("blocks", [])

        # Filter drawings with a solid fill
        filled_drawings = []
        for d in drawings:
            fill_color = d.get('fill')
            if fill_color is not None:
                d_rect = fitz.Rect(d['rect'])
                # Only consider shapes of meaningful size (> 100 pt^2)
                if d_rect.width >= 10 and d_rect.height >= 8:
                    filled_drawings.append((d_rect, fill_color))

        if not filled_drawings:
            continue

        # Check each text span against filled shapes
        for b in blocks:
            if b.get("type") == 0:  # Text block
                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if len(text) < 2:
                            continue

                        s_rect = fitz.Rect(span.get("bbox", [0, 0, 0, 0]))
                        s_area = s_rect.width * s_rect.height
                        if s_area <= 0:
                            continue

                        for d_rect, fill_col in filled_drawings:
                            # Check if the drawing substantially covers the text span
                            intersect = d_rect & s_rect
                            if not intersect.is_empty:
                                overlap_area = intersect.width * intersect.height
                                overlap_ratio = overlap_area / s_area

                                if overlap_ratio > 0.65:
                                    color_desc = f"RGB{fill_col}" if isinstance(fill_col, (list, tuple)) else str(fill_col)
                                    findings.append({
                                        'rule_id': rule['id'],
                                        'title': rule['title'],
                                        'severity': rule['severity'],
                                        'category': rule['category'],
                                        'status': 'Potential Anomaly',
                                        'confidence': rule['confidence'],
                                        'evidence_class': rule['evidence_class'],
                                        'page_number': page_num,
                                        'coordinates': [round(s_rect.x0, 2), round(s_rect.y0, 2), round(s_rect.x1, 2), round(s_rect.y1, 2)],
                                        'description': (
                                            f"Text span '{text}' is physically covered by a filled vector shape "
                                            f"({int(overlap_ratio * 100)}% covered, fill {color_desc}). "
                                            f"Commonly seen in white-box redactions and digital figure alteration."
                                        ),
                                        'evidence': f"Text \"{text}\" under filled shape rect {list(d_rect)}"
                                    })
                                    break  # Avoid duplicate alerts for same text span

    return findings


def check_incremental_updates(file_path):
    """
    PDF-002: Inspects raw PDF file bytes for multiple %%EOF markers and
    incremental update cross-reference chains (/Prev pointers).
    Differentiates confirmed structural facts from heuristic suspicions.
    """
    findings = []
    rule = EXTENDED_PDF_RULES['PDF-002']

    try:
        with open(file_path, 'rb') as f:
            raw_bytes = f.read()

        eof_count = raw_bytes.count(b'%%EOF')
        prev_matches = re.findall(rb'/Prev\s+(\d+)', raw_bytes)
        prev_offsets = [int(m) for m in prev_matches]

        if eof_count > 1 or len(prev_offsets) > 0:
            revision_count = max(eof_count, len(prev_offsets) + 1)
            evidence_str = f"Raw %%EOF marker count: {eof_count}"
            if prev_offsets:
                evidence_str += f" | /Prev xref offsets: {prev_offsets}"

            findings.append({
                'rule_id': rule['id'],
                'title': rule['title'],
                'severity': rule['severity'],
                'category': rule['category'],
                'status': 'Observation',
                'confidence': rule['confidence'],
                'evidence_class': rule['evidence_class'],
                'page_number': 1,
                'coordinates': None,
                'description': (
                    f"[Confirmed Structural Fact] Document file contains {eof_count} incremental update marker(s) (%%EOF) "
                    f"and {len(prev_offsets)} /Prev cross-reference pointer(s) (revisions: {revision_count}). "
                    f"This technical observation confirms the document body was appended, re-saved, or digitally modified after initial compilation."
                ),
                'evidence': evidence_str
            })
    except Exception as e:
        logger.warning(f"[PDF-002 Error] Failed to read raw bytes: {e}")

    return findings


def check_metadata_inconsistencies(doc):
    """
    PDF-003: Evaluates PDF header metadata for divergence between creation
    date and modification date, or unusual editor software signatures.
    Reported strictly as an Observation.
    """
    findings = []
    rule = EXTENDED_PDF_RULES['PDF-003']

    meta = doc.metadata or {}
    c_date = meta.get('creationDate') or ""
    m_date = meta.get('modDate') or ""
    producer = meta.get('producer') or ""
    creator = meta.get('creator') or ""

    # Check for date divergence
    if c_date and m_date and c_date != m_date:
        # Extract year/month numbers if in standard format D:YYYYMMDD
        c_clean = re.sub(r'[^\d]', '', c_date)[:8]
        m_clean = re.sub(r'[^\d]', '', m_date)[:8]

        if c_clean and m_clean and c_clean != m_clean:
            findings.append({
                'rule_id': rule['id'],
                'title': rule['title'],
                'severity': rule['severity'],
                'category': rule['category'],
                'status': 'Observation',
                'confidence': rule['confidence'],
                'evidence_class': rule['evidence_class'],
                'page_number': 1,
                'coordinates': None,
                'description': (
                    f"PDF technical modification date ({m_date}) differs from original creation date ({c_date}). "
                    f"Tool signature: '{producer or creator or 'Unspecified'}'. Technical observation of subsequent re-export."
                ),
                'evidence': f"CreationDate: {c_date} | ModDate: {m_date}"
            })

    # Check for suspicious editing software
    suspicious_tools = ['canva', 'ilovepdf', 'photoshop', 'pdfescape', 'sejda', 'nitro', 'gimp', 'inkscape', 'illustrator', 'foxit', 'smallpdf', 'pdf2go', 'pdf editor', 'master pdf']
    app_text = f"{producer} {creator}".lower()
    for tool in suspicious_tools:
        if tool in app_text:
            findings.append({
                'rule_id': rule['id'],
                'title': f"Commercial Editor Signature Detected ({tool.capitalize()})",
                'severity': 'Medium',
                'category': rule['category'],
                'status': 'Observation',
                'confidence': 0.85,
                'evidence_class': 'Observation',
                'page_number': 1,
                'coordinates': None,
                'description': (
                    f"Document metadata reveals third-party visual editing software signature: '{tool.capitalize()}'. "
                    f"Corporate and statutory documents are normally generated directly by accounting or ERP engines."
                ),
                'evidence': f"Producer: '{producer}' | Creator: '{creator}'"
            })
            break

    return findings


def check_embedded_images_and_resolution(doc):
    """
    PDF-004: Detects embedded raster images placed directly over underlying vector text,
    as well as wild image resolution disparities across the page.
    """
    findings = []
    rule = EXTENDED_PDF_RULES['PDF-004']

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1

        img_list = page.get_images(full=True)
        if not img_list:
            continue

        # Extract text blocks on page
        p_dict = page.get_text("dict")
        blocks = p_dict.get("blocks", [])
        text_spans = []
        for b in blocks:
            if b.get("type") == 0:
                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        if span.get("text", "").strip():
                            text_spans.append((fitz.Rect(span["bbox"]), span["text"].strip()))

        # Inspect each image on page
        image_dpis = []
        for img_info in img_list:
            xref = img_info[0]
            try:
                img_rects = page.get_image_rects(xref)
            except Exception:
                img_rects = []

            # Calculate effective resolution
            pix = fitz.Pixmap(doc, xref)
            w_px, h_px = pix.width, pix.height

            for i_rect in img_rects:
                if i_rect.width > 5 and i_rect.height > 5:
                    dpi_x = (w_px / i_rect.width) * 72.0
                    image_dpis.append((dpi_x, i_rect))

                    # Check collision with underlying text
                    for s_rect, text in text_spans:
                        s_area = s_rect.width * s_rect.height
                        intersect = i_rect & s_rect
                        if not intersect.is_empty and s_area > 0:
                            overlap_area = intersect.width * intersect.height
                            overlap_ratio = overlap_area / s_area
                            if overlap_ratio > 0.35 or overlap_area > 50:
                                findings.append({
                                    'rule_id': rule['id'],
                                    'title': rule['title'],
                                    'severity': rule['severity'],
                                    'category': rule['category'],
                                    'status': 'Potential Anomaly',
                                    'confidence': rule['confidence'],
                                    'evidence_class': rule['evidence_class'],
                                    'page_number': page_num,
                                    'coordinates': [round(i_rect.x0, 2), round(i_rect.y0, 2), round(i_rect.x1, 2), round(i_rect.y1, 2)],
                                    'description': (
                                        f"Embedded raster image [{int(i_rect.width)}x{int(i_rect.height)} pt] is superimposed directly over "
                                        f"vector text content ('{text}'). Indicates a signature patch, badge, or graphical stamp overlay."
                                    ),
                                    'evidence': f"Image over text '{text}' at bbox {list(i_rect)}"
                                })
                                break

        # Check for full-page background scan overprinted with digital vector text
        p_w, p_h = page.rect.width, page.rect.height
        for (dpi, i_rect) in image_dpis:
            if i_rect.width >= p_w * 0.75 and i_rect.height >= p_h * 0.75:
                text_inside = [t for t in text_spans if (t[0] & i_rect).get_area() > 0]
                if len(text_inside) >= 1:
                    sample_texts = [t[1] for t in text_inside[:3]]
                    sample_str = ", ".join([f"'{s}'" for s in sample_texts])
                    findings.append({
                        'rule_id': 'PDF-004',
                        'title': 'Vector Text Overprinted on Scanned Page Background',
                        'severity': 'Medium',
                        'category': 'Visual Structure',
                        'status': 'Potential Anomaly',
                        'confidence': 0.88,
                        'evidence_class': 'Potential Manipulation',
                        'page_number': page_num,
                        'coordinates': [round(i_rect.x0, 2), round(i_rect.y0, 2), round(i_rect.x1, 2), round(i_rect.y1, 2)],
                        'description': (
                            f"Page {page_num} contains {len(text_inside)} digital vector text element(s) ({sample_str}) "
                            f"rendered over a full-page raster scan [{int(i_rect.width)}x{int(i_rect.height)} pt]. "
                            f"This indicates digital text overprinting / patching onto a scanned document template."
                        ),
                        'evidence': f"{len(text_inside)} vector text spans on background image bbox {list(i_rect)}"
                    })
                    break

        # Check for extreme image resolution disparity (> 3.5x ratio on same page)
        if len(image_dpis) >= 2:
            sorted_dpis = sorted(image_dpis, key=lambda x: x[0])
            min_dpi, min_rect = sorted_dpis[0]
            max_dpi, max_rect = sorted_dpis[-1]
            if min_dpi > 20 and (max_dpi / min_dpi) > 3.5:
                findings.append({
                    'rule_id': 'PDF-004',
                    'title': 'Severe Image Resolution Disparity On Page',
                    'severity': 'Medium',
                    'category': 'Visual Formatting',
                    'status': 'Potential Anomaly',
                    'confidence': 0.82,
                    'evidence_class': 'Observation',
                    'page_number': page_num,
                    'coordinates': [round(min_rect.x0, 2), round(min_rect.y0, 2), round(min_rect.x1, 2), round(min_rect.y1, 2)],
                    'description': (
                        f"Page exhibits disparate embedded image resolutions (Lowest: {int(min_dpi)} DPI vs Highest: {int(max_dpi)} DPI). "
                        f"Disparate resolutions frequently signify composited graphics inserted from external low-res sources."
                    ),
                    'evidence': f"DPI Ratio: {round(max_dpi / min_dpi, 1)}x ({int(min_dpi)} DPI vs {int(max_dpi)} DPI)"
                })

    return findings


def check_invisible_and_offpage_text(doc):
    """
    PDF-005: Identifies text elements that are rendered completely outside
    the visible page viewport, or configured with invisible rendering modes.
    """
    findings = []
    rule = EXTENDED_PDF_RULES['PDF-005']

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1
        p_rect = page.rect

        # Expand clipping box by 500pt around page to capture off-page elements
        expanded_clip = fitz.Rect(
            -500, -500,
            p_rect.width + 500, p_rect.height + 500
        )
        try:
            tp = page.get_textpage(clip=expanded_clip)
            p_dict = page.get_text("dict", textpage=tp)
        except Exception:
            p_dict = page.get_text("dict")

        blocks = p_dict.get("blocks", [])

        for b in blocks:
            if b.get("type") == 0:
                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue

                        bbox = span.get("bbox", [0, 0, 0, 0])
                        s_rect = fitz.Rect(bbox)

                        # Check 1: Text fully outside the visible page boundary
                        # (beyond margins by more than 15 points)
                        is_offpage = (
                            s_rect.x1 < -10 or
                            s_rect.y1 < -10 or
                            s_rect.x0 > (p_rect.width + 10) or
                            s_rect.y0 > (p_rect.height + 10)
                        )

                        if is_offpage:
                            findings.append({
                                'rule_id': rule['id'],
                                'title': rule['title'],
                                'severity': rule['severity'],
                                'category': rule['category'],
                                'status': 'Potential Anomaly',
                                'confidence': rule['confidence'],
                                'evidence_class': rule['evidence_class'],
                                'page_number': page_num,
                                'coordinates': [round(s_rect.x0, 2), round(s_rect.y0, 2), round(s_rect.x1, 2), round(s_rect.y1, 2)],
                                'description': (
                                    f"Text span '{text}' is rendered completely outside the visible page boundaries "
                                    f"[Page: 0,0,{int(p_rect.width)},{int(p_rect.height)} | Text: {list(s_rect)}]. "
                                    f"May indicate hidden prompts, steganographic data, or leftover draft artifacts."
                                ),
                                'evidence': f"Off-page text \"{text}\" at coordinates {list(s_rect)}"
                            })
                            continue

                        # Check 2: Invisible rendering mode (render_mode == 3, "neither fill nor stroke")
                        render_mode = span.get("flags", 0)
                        # PyMuPDF span flags or color match checks
                        # If text font size > 0 but color is 100% transparent or matching background exactly
                        # span flags check
                        if span.get("render_mode") == 3:
                            findings.append({
                                'rule_id': rule['id'],
                                'title': 'Invisible Text Mode 3 Detected',
                                'severity': 'High',
                                'category': rule['category'],
                                'status': 'Potential Anomaly',
                                'confidence': 0.96,
                                'evidence_class': 'Potential Manipulation',
                                'page_number': page_num,
                                'coordinates': [round(s_rect.x0, 2), round(s_rect.y0, 2), round(s_rect.x1, 2), round(s_rect.y1, 2)],
                                'description': (
                                    f"Text span '{text}' uses PDF render mode 3 (invisible text). "
                                    f"The text is extractable by software but invisible to human reviewers."
                                ),
                                'evidence': f"Render mode 3 on text \"{text}\""
                            })

    return findings


# =====================================================================


def check_suspicious_pdf_objects(doc):
    """
    PDF-006: Scans PDF structural catalog, name trees, and xref dictionary objects
    for suspicious interactive or executable constructs:
    - /JavaScript or /JS: Embedded executable scripts
    - /Launch: Shell or executable launch actions
    - /EmbeddedFiles: Hidden embedded file attachments / payloads
    """
    findings = []
    rule = EXTENDED_PDF_RULES['PDF-006']

    try:
        suspicious_xrefs = []
        for xref in range(1, doc.xref_length()):
            try:
                obj_text = doc.xref_object(xref)
                if not obj_text:
                    continue

                if re.search(r'/(JavaScript|JS)\b', obj_text):
                    suspicious_xrefs.append((xref, 'Embedded JavaScript (/JavaScript)', 'High'))
                elif re.search(r'/Launch\b', obj_text):
                    suspicious_xrefs.append((xref, 'Executable Launch Trigger (/Launch)', 'Critical'))
                elif re.search(r'/EmbeddedFiles\b', obj_text):
                    suspicious_xrefs.append((xref, 'Hidden Embedded File Payload (/EmbeddedFiles)', 'Medium'))
            except Exception:
                continue

        seen_types = set()
        for xref, obj_type, sev in suspicious_xrefs:
            if obj_type in seen_types:
                continue
            seen_types.add(obj_type)
            findings.append({
                'rule_id': rule['id'],
                'title': f"Suspicious PDF Object Detected ({obj_type})",
                'severity': sev,
                'category': rule['category'],
                'status': 'Potential Anomaly',
                'confidence': rule['confidence'],
                'evidence_class': rule['evidence_class'],
                'page_number': 1,
                'coordinates': None,
                'description': (
                    f"[Confirmed Structural Fact] PDF structure contains an active {obj_type} at object xref {xref}. "
                    f"Standard business documents, contracts, and financial invoices should contain only passive page streams. "
                    f"Active scripting or external launch triggers represent significant forensic anomalies."
                ),
                'evidence': f"Object xref {xref} specifies {obj_type}"
            })
    except Exception as e:
        logger.warning(f"[PDF-006 Error] Suspicious object scan failed: {e}")

    return findings

# 2. Master Extended PDF Forensics Runner
# =====================================================================

def run_extended_pdf_forensics(file_path):
    """
    Executes all Phase B extended PDF forensic rules against target file.
    Returns a unified list of finding dictionaries conforming to the VEXORA finding shape.
    """
    findings = []
    path_obj = Path(file_path)
    if not path_obj.exists():
        return findings

    # Only process PDF files
    if path_obj.suffix.lower().lstrip('.') != 'pdf':
        return findings

    if fitz is None:
        logger.warning("[Extended PDF Forensics] PyMuPDF (fitz) is not available.")
        return findings

    # 1. Raw Byte Analysis (Incremental Updates)
    findings.extend(check_incremental_updates(file_path))

    # 2. In-Depth PyMuPDF Vector & Geometric Inspection
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        logger.warning(f"[Extended PDF Forensics] Could not open PDF {file_path}: {e}")
        return findings

    try:
        # PDF-001: Text hidden under shapes
        findings.extend(check_text_hidden_under_shapes(doc))

        # PDF-003: Metadata desynchronization
        findings.extend(check_metadata_inconsistencies(doc))

        # PDF-004: Images over text & resolution disparity
        findings.extend(check_embedded_images_and_resolution(doc))

        # PDF-005: Invisible and off-page text
        findings.extend(check_invisible_and_offpage_text(doc))

        # PDF-006: Suspicious interactive or executable objects
        findings.extend(check_suspicious_pdf_objects(doc))
    finally:
        doc.close()

    return findings
