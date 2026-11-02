"""
VEXORA — Real PDF Forensics Engine
Performs deep structural, byte-level, and vector inspection of PDF documents:
1. White rectangle masking over text (PDF-R101) - Classic digital cover-up.
2. Multiple %%EOF markers (PDF-R102) - Incremental file updates / post-signing edits.
3. Producer/Creator software mismatch (PDF-R103) - Consumer editors (Canva, iLovePDF, Photoshop) on official records.
4. Embedded images superimposed over text blocks (PDF-R104).
5. Significant image resolution / DPI inconsistency within a single page (PDF-R105).
"""

import os
import re
from pathlib import Path
import pymupdf

PDF_FORENSIC_RULES = {
    'PDF-R101': {
        'id': 'PDF-R101',
        'title': 'Covert Whiteout Masking Detected (Vector Mask over Text)',
        'category': 'Vector Forensics',
        'severity': 'Critical',
        'rule_weight': 0.96,
        'recommendation': 'Examine underlying text layers beneath the opaque white rectangle for altered figures or names.'
    },
    'PDF-R102': {
        'id': 'PDF-R102',
        'title': 'Multiple %%EOF Markers Detected (Incremental Post-Save Edit)',
        'category': 'Structural Forensics',
        'severity': 'High',
        'rule_weight': 0.92,
        'recommendation': 'Inspect file revisions using forensic PDF stream analysis to recover pre-modification states.'
    },
    'PDF-R103': {
        'id': 'PDF-R103',
        'title': 'Suspicious Producer/Creator Metadata Mismatch',
        'category': 'Metadata Forensics',
        'severity': 'High',
        'rule_weight': 0.89,
        'recommendation': 'Official financial/tax records are rarely generated via consumer editing tools (e.g. Canva, iLovePDF). Request source issuer confirmation.'
    },
    'PDF-R104': {
        'id': 'PDF-R104',
        'title': 'Embedded Graphic Superimposed Over Native Text',
        'category': 'Layer Forensics',
        'severity': 'High',
        'rule_weight': 0.88,
        'recommendation': 'Verify whether scanned stamps or logo patches were digitally grafted over preexisting textual fields.'
    },
    'PDF-R105': {
        'id': 'PDF-R105',
        'title': 'Image Resolution Variance Within Single Page',
        'category': 'Raster Forensics',
        'severity': 'Medium',
        'rule_weight': 0.78,
        'recommendation': 'Divergent DPI values indicate composite document assembly from multiple source captures.'
    }
}

SUSPICIOUS_PRODUCERS = [
    'canva', 'ilovepdf', 'smallpdf', 'pdf24', 'photoshop', 'gimp', 
    'paint.net', 'nitro pdf', 'sejda', 'soda pdf', 'foxit phantom'
]

OFFICIAL_KEYWORD_TRIGGERS = [
    'bank', 'tax', 'incometax', 'invoice', 'salary', 'payslip', 'statement', 
    'internal revenue', 'ministry', 'department', 'authorized signatory', 'gstin', 'pan'
]

def check_incremental_saves(file_path_or_bytes):
    """
    Counts occurrences of %%EOF in the binary stream.
    A standard PDF written once terminates with a single %%EOF.
    Multiple %%EOF markers indicate incremental updates (often post-creation tampering).
    """
    if isinstance(file_path_or_bytes, (str, Path)):
        with open(file_path_or_bytes, 'rb') as f:
            raw_bytes = f.read()
    else:
        raw_bytes = file_path_or_bytes

    eof_count = len(re.findall(b'%%EOF', raw_bytes))
    return {
        'eof_count': eof_count,
        'is_incrementally_updated': eof_count > 1
    }

def check_white_rectangle_masking(doc):
    """
    Detects white or near-white vector rectangles that visually mask or overlap
    underlying text blocks. This is the hallmark of manual PDF text alteration.
    """
    masking_anomalies = []

    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        page_num = page_idx + 1

        # Extract text blocks
        blocks = page.get_text("blocks")
        text_rects = []
        for b in blocks:
            if len(b) >= 7 and b[6] == 0:  # text block
                text_rects.append((pymupdf.Rect(b[0], b[1], b[2], b[3]), b[4].strip()))

        # Extract vector drawings
        drawings = page.get_drawings()
        for draw in drawings:
            # Check if drawing has a fill color that is white or near-white
            fill = draw.get('fill')
            if fill is None:
                continue

            # PyMuPDF colors are RGB tuples (r, g, b) with values 0.0 - 1.0 or grayscale (v,)
            is_white = False
            if isinstance(fill, (list, tuple)):
                if len(fill) == 3 and all(c >= 0.97 for c in fill):
                    is_white = True
                elif len(fill) == 1 and fill[0] >= 0.97:
                    is_white = True

            if not is_white:
                continue

            draw_rect = draw.get('rect')
            if not draw_rect or draw_rect.width < 5 or draw_rect.height < 5:
                continue

            # Ignore page background rectangle (which covers entire page)
            if draw_rect.width >= page.rect.width * 0.95 and draw_rect.height >= page.rect.height * 0.95:
                continue

            # Check overlap with any text rects
            for t_rect, text_snippet in text_rects:
                overlap = draw_rect.intersect(t_rect)
                if not overlap.is_empty and (overlap.width * overlap.height > 15):
                    masking_anomalies.append({
                        'page': page_num,
                        'bbox': [round(draw_rect.x0, 1), round(draw_rect.y0, 1), round(draw_rect.x1, 1), round(draw_rect.y1, 1)],
                        'text_covered_sample': text_snippet[:80],
                        'reason': f"Opaque white vector rectangle ({round(draw_rect.width)}x{round(draw_rect.height)}pt) overlaps text: '{text_snippet[:40]}...'"
                    })
                    break  # One finding per white rect

    return masking_anomalies

def check_producer_mismatch(metadata, full_text):
    """
    Checks if an official record claims official provenance (bank/tax/invoice)
    while its PDF producer/creator metadata identifies consumer editing tools.
    """
    producer = (metadata.get('producer') or '').lower()
    creator = (metadata.get('creator') or '').lower()
    meta_str = f"{producer} {creator}"
    text_lower = full_text.lower()

    claimed_official = any(kw in text_lower for kw in OFFICIAL_KEYWORD_TRIGGERS)
    detected_tool = None

    for tool in SUSPICIOUS_PRODUCERS:
        if tool in meta_str:
            detected_tool = tool
            break

    if claimed_official and detected_tool:
        return {
            'suspicious': True,
            'tool': detected_tool.title(),
            'producer': metadata.get('producer') or 'Unknown',
            'creator': metadata.get('creator') or 'Unknown',
            'reason': f"Document contains official financial/tax markers, but was produced or edited via consumer tool '{detected_tool.title()}' (Producer: {metadata.get('producer', 'N/A')})."
        }
    return {'suspicious': False}

def check_superimposed_images(doc):
    """
    Detects embedded raster graphics positioned directly over preexisting text blocks.
    """
    overlays = []
    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        page_num = page_idx + 1

        text_blocks = [
            pymupdf.Rect(b[0], b[1], b[2], b[3])
            for b in page.get_text("blocks")
            if len(b) >= 7 and b[6] == 0 and b[4].strip()
        ]

        # Scan images on page
        image_list = page.get_images(full=True)
        for img_info in image_list:
            xref = img_info[0]
            try:
                rects = page.get_image_rects(xref)
                for img_rect in rects:
                    # Ignore full page background scans
                    if img_rect.width >= page.rect.width * 0.90 and img_rect.height >= page.rect.height * 0.90:
                        continue

                    # Check collision with text blocks
                    for t_rect in text_blocks:
                        overlap = img_rect.intersect(t_rect)
                        if not overlap.is_empty and (overlap.width * overlap.height > 100):
                            overlays.append({
                                'page': page_num,
                                'bbox': [round(img_rect.x0, 1), round(img_rect.y0, 1), round(img_rect.x1, 1), round(img_rect.y1, 1)],
                                'reason': f"Embedded image overlay ({round(img_rect.width)}x{round(img_rect.height)}pt) overlaps underlying text layer."
                            })
                            break
            except Exception:
                continue

    return overlays

def check_image_resolution_inconsistencies(doc):
    """
    Compares image resolutions on the same page.
    A page with both 72 DPI (web screenshot) and 300 DPI (original scan) indicates composite tampering.
    """
    anomalies = []
    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        page_num = page_idx + 1

        image_list = page.get_images(full=True)
        if len(image_list) < 2:
            continue

        resolutions = []
        for img_info in image_list:
            xref = img_info[0]
            try:
                rects = page.get_image_rects(xref)
                if not rects:
                    continue
                pix_w, pix_h = img_info[2], img_info[3]
                pt_w, pt_h = rects[0].width, rects[0].height
                if pt_w > 0 and pt_h > 0:
                    dpi_x = (pix_w / pt_w) * 72.0
                    dpi_y = (pix_h / pt_h) * 72.0
                    avg_dpi = round((dpi_x + dpi_y) / 2.0, 1)
                    resolutions.append((avg_dpi, rects[0]))
            except Exception:
                continue

        if len(resolutions) >= 2:
            dpis = [r[0] for r in resolutions]
            min_dpi = min(dpis)
            max_dpi = max(dpis)
            if min_dpi > 0 and (max_dpi / min_dpi) >= 2.5:
                # Find the outlier
                outlier_bbox = resolutions[0][1]
                anomalies.append({
                    'page': page_num,
                    'min_dpi': min_dpi,
                    'max_dpi': max_dpi,
                    'bbox': [round(outlier_bbox.x0, 1), round(outlier_bbox.y0, 1), round(outlier_bbox.x1, 1), round(outlier_bbox.y1, 1)],
                    'reason': f"Divergent image resolutions detected on Page {page_num}: minimum {min_dpi} DPI vs maximum {max_dpi} DPI ({round(max_dpi/min_dpi, 1)}x variance)."
                })

    return anomalies

def analyze_pdf_forensics(file_path_or_bytes, metadata=None, full_text=""):
    """
    Runs all specialized PDF structural & vector forensic routines.
    Returns a list of standardized forensic findings.
    """
    findings = []

    # 1. Incremental %%EOF check
    eof_res = check_incremental_saves(file_path_or_bytes)
    if eof_res['is_incrementally_updated']:
        rule = PDF_FORENSIC_RULES['PDF-R102']
        findings.append({
            'rule_id': rule['id'],
            'title': rule['title'],
            'category': rule['category'],
            'severity': rule['severity'],
            'confidence': rule['rule_weight'],  # Stored internally, displayed as rule_weight
            'rule_weight': rule['rule_weight'],
            'description': f"File structure contains {eof_res['eof_count']} '%%EOF' termination markers. Incremental updates detected post-creation.",
            'recommendation': rule['recommendation'],
            'page_number': 1,
            'bounding_box': [0.0, 0.0, 0.0, 0.0],
            'evidence_type': 'structural'
        })

    # Open PyMuPDF document for vector and layer checks
    try:
        if isinstance(file_path_or_bytes, (str, Path)):
            doc = pymupdf.open(str(file_path_or_bytes))
        else:
            doc = pymupdf.open(stream=file_path_or_bytes, filetype="pdf")
    except Exception:
        return findings

    try:
        # 2. White rectangle masking
        white_masks = check_white_rectangle_masking(doc)
        rule = PDF_FORENSIC_RULES['PDF-R101']
        for wm in white_masks:
            findings.append({
                'rule_id': rule['id'],
                'title': rule['title'],
                'category': rule['category'],
                'severity': rule['severity'],
                'confidence': rule['rule_weight'],
                'rule_weight': rule['rule_weight'],
                'description': wm['reason'],
                'recommendation': rule['recommendation'],
                'page_number': wm['page'],
                'bounding_box': wm['bbox'],
                'evidence_type': 'vector_mask'
            })

        # 3. Producer / Creator mismatch
        meta = metadata or doc.metadata or {}
        prod_check = check_producer_mismatch(meta, full_text or doc[0].get_text())
        if prod_check['suspicious']:
            rule = PDF_FORENSIC_RULES['PDF-R103']
            findings.append({
                'rule_id': rule['id'],
                'title': rule['title'],
                'category': rule['category'],
                'severity': rule['severity'],
                'confidence': rule['rule_weight'],
                'rule_weight': rule['rule_weight'],
                'description': prod_check['reason'],
                'recommendation': rule['recommendation'],
                'page_number': 1,
                'bounding_box': [0.0, 0.0, 0.0, 0.0],
                'evidence_type': 'metadata'
            })

        # 4. Superimposed images over text
        img_overlays = check_superimposed_images(doc)
        rule = PDF_FORENSIC_RULES['PDF-R104']
        for io in img_overlays:
            findings.append({
                'rule_id': rule['id'],
                'title': rule['title'],
                'category': rule['category'],
                'severity': rule['severity'],
                'confidence': rule['rule_weight'],
                'rule_weight': rule['rule_weight'],
                'description': io['reason'],
                'recommendation': rule['recommendation'],
                'page_number': io['page'],
                'bounding_box': io['bbox'],
                'evidence_type': 'raster_overlay'
            })

        # 5. DPI Inconsistency
        dpi_inconsistencies = check_image_resolution_inconsistencies(doc)
        rule = PDF_FORENSIC_RULES['PDF-R105']
        for di in dpi_inconsistencies:
            findings.append({
                'rule_id': rule['id'],
                'title': rule['title'],
                'category': rule['category'],
                'severity': rule['severity'],
                'confidence': rule['rule_weight'],
                'rule_weight': rule['rule_weight'],
                'description': di['reason'],
                'recommendation': rule['recommendation'],
                'page_number': di['page'],
                'bounding_box': di['bbox'],
                'evidence_type': 'dpi_variance'
            })

    finally:
        doc.close()

    return findings
