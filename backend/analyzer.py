"""
VEXORA — Forensic & Contextual Intelligence Engine (Phase 6)
Analyzes documents for typographic anomalies, font inconsistencies,
text overlaps, coordinate irregularities, missing fields, contradictory identifiers,
and chronological or monetary discrepancies.
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
import pymupdf
from backend.extractor import extract_document_content
from backend.models import (
    get_document_by_id,
    save_document_extraction,
    save_document_findings,
    get_findings_by_document
)

# Rule Identifiers & Definitions
RULES = {
    'RULE-VIS-001': {
        'id': 'RULE-VIS-001',
        'title': 'Discrepant Font Family Detected',
        'category': 'Visual Formatting',
        'severity': 'Medium',
        'confidence': 0.88,
        'recommendation': 'Inspect text block under high magnification to confirm whether characters were digitally inserted.'
    },
    'RULE-VIS-002': {
        'id': 'RULE-VIS-002',
        'title': 'Overlapping Text Elements Detected',
        'category': 'Structural Alignment',
        'severity': 'High',
        'confidence': 0.92,
        'recommendation': 'Examine the bounding box for dual-layer text stamping or overwritten numerical figures.'
    },
    'RULE-VIS-003': {
        'id': 'RULE-VIS-003',
        'title': 'Out-of-Bounds Text Placement',
        'category': 'Structural Alignment',
        'severity': 'Low',
        'confidence': 0.80,
        'recommendation': 'Verify printable boundary margins against canonical document issuer template.'
    },
    'RULE-VIS-004': {
        'id': 'RULE-VIS-004',
        'title': 'Irregular Line Spacing Disparity',
        'category': 'Visual Formatting',
        'severity': 'Low',
        'confidence': 0.75,
        'recommendation': 'Cross-reference baseline alignment with surrounding paragraph structure.'
    },
    'RULE-VIS-005': {
        'id': 'RULE-VIS-005',
        'title': 'Degraded Resolution or Compression Artifact',
        'category': 'Visual Formatting',
        'severity': 'Info',
        'confidence': 0.70,
        'recommendation': 'Request original high-resolution master scan or vector PDF.'
    },
    'RULE-CTX-001': {
        'id': 'RULE-CTX-001',
        'title': 'Missing Mandatory Document Field',
        'category': 'Contextual Inconsistency',
        'severity': 'Medium',
        'confidence': 0.90,
        'recommendation': 'Verify whether document is a preliminary draft or omitted mandatory compliance identifiers.'
    },
    'RULE-CTX-002': {
        'id': 'RULE-CTX-002',
        'title': 'Multiple Conflicting Document Identifiers',
        'category': 'Contextual Inconsistency',
        'severity': 'High',
        'confidence': 0.94,
        'recommendation': 'Inspect whether secondary identifiers originate from reference purchase orders or composite document splicing.'
    },
    'RULE-CTX-003': {
        'id': 'RULE-CTX-003',
        'title': 'Chronological Sequence Inconsistency',
        'category': 'Contextual Inconsistency',
        'severity': 'High',
        'confidence': 0.91,
        'recommendation': 'Audit the timestamp sequence. Check for post-dated terms or reversed billing-due timelines.'
    },
    'RULE-CTX-004': {
        'id': 'RULE-CTX-004',
        'title': 'Conflicting Monetary Values or Currencies',
        'category': 'Contextual Inconsistency',
        'severity': 'High',
        'confidence': 0.93,
        'recommendation': 'Reconcile individual line-item sums against the stated grand total and verify currency consistency.'
    },
        'RULE-DOC-001': {
        'id': 'RULE-DOC-001',
        'title': 'Arithmetic Calculation Inconsistency',
        'category': 'Document Logic',
        'severity': 'Critical',
        'confidence': 0.96,
        'recommendation': 'Audit line-item calculations. Verify whether subtotal, tax rate, or grand total was digitally altered.'
    },
    'RULE-DOC-002': {
        'id': 'RULE-DOC-002',
        'title': 'Chronological Sequence Inversion',
        'category': 'Document Logic',
        'severity': 'High',
        'confidence': 0.92,
        'recommendation': 'Verify billing workflow. Check why payment due date or delivery date precedes document issuance.'
    },
    'RULE-DOC-004': {
        'id': 'RULE-DOC-004',
        'title': 'Conflicting Duplicate Financial Values',
        'category': 'Document Logic',
        'severity': 'High',
        'confidence': 0.94,
        'recommendation': 'Examine header vs summary figures for evidence of cut-and-paste tampering or mismatched form fields.'
    },
    'RULE-DOC-005': {
        'id': 'RULE-DOC-005',
        'title': 'Expired Identification Credential',
        'category': 'Compliance & Identity',
        'severity': 'High',
        'confidence': 0.95,
        'recommendation': 'Verify validity dates against issuing authority standards. Expired credentials cannot substantiate transactions.'
    },
    'RULE-CTX-005': {
        'id': 'RULE-CTX-005',
        'title': 'Metadata Timestamp Mismatch',
        'category': 'Contextual Inconsistency',
        'severity': 'Medium',
        'confidence': 0.78,
        'recommendation': 'Compare PDF creation metadata against document body dates. Note that metadata can be updated on export or print.'
    }
}

# =====================================================================
# 1. Visual & Structural Forensic Analysis
# =====================================================================

def analyze_visual_structure(file_path):
    """
    Examines layout geometry, font distributions, bounding boxes,
    and text intersections across all document pages.
    """
    findings = []
    ext = Path(file_path).suffix.lower().lstrip('.')

    if ext != 'pdf':
        # Image-based visual sanity check
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                w, h = img.size
                if w < 200 or h < 200:
                    rule = RULES['RULE-VIS-005']
                    findings.append({
                        'rule_id': rule['id'],
                        'title': rule['title'],
                        'severity': rule['severity'],
                        'category': rule['category'],
                        'status': 'Potential Anomaly',
                        'confidence': rule['confidence'],
                        'page_number': 1,
                        'coordinates': [0, 0, w, h],
                        'description': f"Low image resolution ({w}x{h} px). Text legibility may be compromised.",
                        'evidence': f"Dimensions: {w}x{h}"
                    })
        except Exception:
            pass
        return findings

    # PDF In-Depth Geometric & Typographic Inspection
    try:
        doc = pymupdf.open(file_path)
    except Exception as e:
        return findings

    all_spans = []
    font_counts = {}

    # First pass: collect all spans and font distributions across all pages
    for page_idx in range(len(doc)):
        page_num = page_idx + 1
        page = doc[page_idx]
        rect = page.rect
        p_dict = page.get_text("dict")
        blocks = p_dict.get("blocks", [])

        for b in blocks:
            if b.get("type") == 0:  # text block
                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        font = span.get("font", "Unknown")
                        size = round(span.get("size", 10.0), 1)
                        bbox = [round(c, 2) for c in span.get("bbox", [0, 0, 0, 0])]

                        span_meta = {
                            'page': page_num,
                            'font': font,
                            'size': size,
                            'bbox': bbox,
                            'text': text,
                            'rect': rect
                        }
                        all_spans.append(span_meta)
                        font_counts[font] = font_counts.get(font, 0) + len(text)

    # Determine dominant font family (font with largest character tally)
    dominant_font = None
    total_chars = sum(font_counts.values())
    if font_counts and total_chars > 0:
        dominant_font = max(font_counts, key=font_counts.get)
        dominant_ratio = font_counts[dominant_font] / total_chars
    else:
        dominant_ratio = 1.0

    # Second pass: Rule checks
    # Check 1: Font Anomaly (RULE-VIS-001)
    # If dominant font accounts for >= 60% of doc, check for isolated spans using an outlier font (< 10% usage)
    # especially if the span contains numbers, dates, or currency symbols
    if dominant_font and dominant_ratio >= 0.60:
        for span in all_spans:
            font = span['font']
            # If font is different from dominant and accounts for < 12% of total chars
            font_share = font_counts.get(font, 0) / total_chars
            if font != dominant_font and font_share < 0.12:
                # Prioritize financial numbers, totals, or critical text
                text = span['text']
                has_critical_token = bool(re.search(r'[\$\€\£\₹\d]|total|due|paid|inv', text, re.IGNORECASE))
                if has_critical_token and len(text) >= 2:
                    rule = RULES['RULE-VIS-001']
                    findings.append({
                        'rule_id': rule['id'],
                        'title': rule['title'],
                        'severity': 'High' if '$' in text or 'total' in text.lower() else 'Medium',
                        'category': rule['category'],
                        'status': 'Potential Anomaly',
                        'confidence': rule['confidence'],
                        'page_number': span['page'],
                        'coordinates': span['bbox'],
                        'description': (
                            f"Text span '{text}' uses isolated font '{font}' ({span['size']}pt) "
                            f"diverging from document primary typeface '{dominant_font}'. Potential typographical alteration."
                        ),
                        'evidence': f"Text: \"{text}\" | Font: {font} ({span['size']}pt)"
                    })

    # Check 1b: Baseline Alignment Disparity on Single Line (RULE-VIS-004)
    for page_idx in range(len(doc)):
        page_num = page_idx + 1
        page = doc[page_idx]
        p_dict = page.get_text("dict")
        for b in p_dict.get("blocks", []):
            if b.get("type") == 0:
                for line in b.get("lines", []):
                    spans = line.get("spans", [])
                    if len(spans) >= 2:
                        y_bottoms = [s['bbox'][3] for s in spans if len(s.get('text', '').strip()) > 1]
                        if len(y_bottoms) >= 2:
                            shift = max(y_bottoms) - min(y_bottoms)
                            if shift >= 3.5:
                                line_text = " ".join(s.get('text', '').strip() for s in spans)
                                if re.search(r'[\$\€\£\₹\d]|total|due|paid|amount|inv', line_text, re.I):
                                    rule = RULES['RULE-VIS-004']
                                    findings.append({
                                        'rule_id': rule['id'],
                                        'title': rule['title'],
                                        'severity': rule['severity'],
                                        'category': rule['category'],
                                        'status': 'Potential Anomaly',
                                        'confidence': rule['confidence'],
                                        'page_number': page_num,
                                        'coordinates': [round(line['bbox'][0], 2), round(line['bbox'][1], 2), round(line['bbox'][2], 2), round(line['bbox'][3], 2)],
                                        'description': (
                                            f"Text line '{line_text}' displays irregular vertical baseline disparity "
                                            f"(shift of {round(shift, 1)}pt between spans). "
                                            "Indicates typographical manipulation or spliced characters."
                                        ),
                                        'evidence': f"Baseline shift: {round(shift, 1)}pt in '{line_text[:40]}'"
                                    })

    # Check 2: Overlapping Text Spans (RULE-VIS-002)
    # Group spans by page
    pages_map = {}
    for span in all_spans:
        pages_map.setdefault(span['page'], []).append(span)

    for p_num, p_spans in pages_map.items():
        n = len(p_spans)
        for i in range(n):
            for j in range(i + 1, n):
                s1 = p_spans[i]
                s2 = p_spans[j]

                # Quick bounding box collision check
                b1 = s1['bbox']
                b2 = s2['bbox']

                # Intersection rectangle
                x_left = max(b1[0], b2[0])
                y_top = max(b1[1], b2[1])
                x_right = min(b1[2], b2[2])
                y_bottom = min(b1[3], b2[3])

                if x_right > x_left + 4 and y_bottom > y_top + 4:
                    area_inter = (x_right - x_left) * (y_bottom - y_top)
                    area1 = max((b1[2] - b1[0]) * (b1[3] - b1[1]), 1.0)
                    area2 = max((b2[2] - b2[0]) * (b2[3] - b2[1]), 1.0)
                    overlap_ratio = area_inter / min(area1, area2)

                    if overlap_ratio > 0.40 and s1['text'] != s2['text']:
                        rule = RULES['RULE-VIS-002']
                        findings.append({
                            'rule_id': rule['id'],
                            'title': rule['title'],
                            'severity': rule['severity'],
                            'category': rule['category'],
                            'status': 'Potential Anomaly',
                            'confidence': rule['confidence'],
                            'page_number': p_num,
                            'coordinates': [x_left, y_top, x_right, y_bottom],
                            'description': (
                                f"Text span '{s1['text']}' overlaps physically with '{s2['text']}' "
                                f"({int(overlap_ratio * 100)}% collision). Indicates text insertion or stamping over existing content."
                            ),
                            'evidence': f"\"{s1['text']}\" collides with \"{s2['text']}\""
                        })

    # Check 3: Out-of-Bounds Placement (RULE-VIS-003)
    for span in all_spans:
        rect = span['rect']
        bbox = span['bbox']
        # Check if coordinates extend beyond page or hug outer boundary (< 5 points from edge)
        if bbox[0] < 5 or bbox[1] < 5 or bbox[2] > rect.width - 5 or bbox[3] > rect.height - 5:
            # Skip running headers or footers at page margins
            if len(span['text']) > 4 and span['size'] > 9:
                rule = RULES['RULE-VIS-003']
                findings.append({
                    'rule_id': rule['id'],
                    'title': rule['title'],
                    'severity': rule['severity'],
                    'category': rule['category'],
                    'status': 'Potential Anomaly',
                    'confidence': rule['confidence'],
                    'page_number': span['page'],
                    'coordinates': bbox,
                    'description': f"Text span '{span['text']}' placed dangerously close to or exceeding page boundary [W:{rect.width}, H:{rect.height}].",
                    'evidence': f"Box: {bbox}"
                })

    doc.close()
    return findings

# =====================================================================
# 2. Contextual & Semantic Forensic Rules
# =====================================================================

def analyze_contextual_rules(doc_category, extracted_text, extracted_data, doc_metadata=None):
    """
    Evaluates contextual integrity: missing mandatory fields, duplicate conflicting
    identifiers, reversed chronologies, monetary mismatches, and metadata discrepancies.
    """
    findings = []
    text = extracted_text or ""
    data = extracted_data or {}
    entities = data.get('entities', {})
    category = (doc_category or '').lower()

    # Rule 1: Missing Mandatory Document Fields (RULE-CTX-001)
    if 'invoice' in category or 'bill' in category:
        missing_fields = []
        if not entities.get('identifiers'):
            missing_fields.append("Invoice / Bill Identifier")
        if not entities.get('dates'):
            missing_fields.append("Issue Date")
        if not entities.get('monetary_values'):
            missing_fields.append("Total Amount / Balance Due")
        if not entities.get('organizations') and not entities.get('persons'):
            missing_fields.append("Vendor / Payee Entity")

        if missing_fields:
            rule = RULES['RULE-CTX-001']
            findings.append({
                'rule_id': rule['id'],
                'title': rule['title'],
                'severity': rule['severity'],
                'category': rule['category'],
                'status': 'Potential Anomaly',
                'confidence': rule['confidence'],
                'page_number': 1,
                'coordinates': None,
                'description': f"Commercial invoice missing mandatory statutory field(s): {', '.join(missing_fields)}.",
                'evidence': f"Missing: {', '.join(missing_fields)}"
            })

    elif 'contract' in category or 'agreement' in category:
        missing_fields = []
        if not entities.get('dates'):
            missing_fields.append("Effective / Execution Date")
        parties_count = len(entities.get('organizations', [])) + len(entities.get('persons', []))
        if parties_count < 2 and not ('employer' in (extracted_text or '').lower() and 'employee' in (extracted_text or '').lower()):
            missing_fields.append("Contracting Counterparties")

        if missing_fields:
            rule = RULES['RULE-CTX-001']
            findings.append({
                'rule_id': rule['id'],
                'title': rule['title'],
                'severity': rule['severity'],
                'category': rule['category'],
                'status': 'Potential Anomaly',
                'confidence': rule['confidence'],
                'page_number': 1,
                'coordinates': None,
                'description': f"Legal agreement missing core requirement(s): {', '.join(missing_fields)}.",
                'evidence': f"Missing: {', '.join(missing_fields)}"
            })

    # Rule 2: Multiple Conflicting Document Identifiers (RULE-CTX-002)
    identifiers = [i['value'] for i in entities.get('identifiers', [])]
    # Filter identifiers to invoice-like patterns (e.g. INV-..., BILL-...)
    inv_ids = set()
    for ident in identifiers:
        ident_clean = ident.strip().upper()
        if ident_clean in ('BILL TO', 'SHIP TO', 'DELIVER TO', 'REMIT TO', 'INVOICE NUMBER', 'INVOICE DATE', 'TAX INVOICE'):
            continue
        if any(prefix in ident_clean for prefix in ['INV-', 'INV:', 'INV#', 'BILL-', 'BILL:', 'BILL#']):
            inv_ids.add(ident_clean)

    if len(inv_ids) > 1 and 'invoice' in category:
        rule = RULES['RULE-CTX-002']
        id_list = ', '.join(sorted(inv_ids))
        findings.append({
            'rule_id': rule['id'],
            'title': rule['title'],
            'severity': rule['severity'],
            'category': rule['category'],
            'status': 'Potential Anomaly',
            'confidence': rule['confidence'],
            'page_number': 1,
            'coordinates': None,
            'description': f"Document contains multiple divergent primary identifiers: {id_list}. Possible composite document tampering.",
            'evidence': f"Identifiers detected: {id_list}"
        })

    # Rule 3: Chronological Sequence Inconsistency (RULE-CTX-003)
    dates = entities.get('dates', [])
    current_year = datetime.now().year
    parsed_dates = []

    for d in dates:
        raw_val = d['value']
        # Try ISO format
        iso_match = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', raw_val)
        if iso_match:
            try:
                y, m, day = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
                if 1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= day <= 31:
                    parsed_dates.append((datetime(y, m, day), raw_val, d.get('page', 1)))
            except ValueError:
                pass

    # Check future dates
    for dt, raw_str, p_num in parsed_dates:
        if dt.year > current_year + 1:
            rule = RULES['RULE-CTX-003']
            findings.append({
                'rule_id': rule['id'],
                'title': rule['title'],
                'severity': rule['severity'],
                'category': rule['category'],
                'status': 'Potential Anomaly',
                'confidence': rule['confidence'],
                'page_number': p_num,
                'coordinates': None,
                'description': f"Document specifies anomalous future date '{raw_str}' (Year {dt.year}). Chronological validity questionable.",
                'evidence': f"Date: {raw_str}"
            })

    # Check for Due Date occurring before Invoice Date
    due_pattern = re.search(r'(?:due(?:\s+date)?|payment\s+date|payable\s+by)[:\s]+([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})', text, re.IGNORECASE)
    inv_pattern = re.search(r'(?:invoice\s+date|issue\s+date|dated)[:\s]+([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})', text, re.IGNORECASE)

    if due_pattern and inv_pattern:
        try:
            d_due = datetime.strptime(due_pattern.group(1).replace('/', '-'), '%Y-%m-%d')
            d_inv = datetime.strptime(inv_pattern.group(1).replace('/', '-'), '%Y-%m-%d')
            if d_due < d_inv:
                rule = RULES['RULE-CTX-003']
                findings.append({
                    'rule_id': rule['id'],
                    'title': rule['title'],
                    'severity': 'Critical',
                    'category': rule['category'],
                    'status': 'Potential Anomaly',
                    'confidence': rule['confidence'],
                    'page_number': 1,
                    'coordinates': None,
                    'description': (
                        f"Payment due date ({due_pattern.group(1)}) is chronologically earlier than invoice issue date ({inv_pattern.group(1)}). "
                        "Reversed billing timeline detected."
                    ),
                    'evidence': f"Issue: {inv_pattern.group(1)} vs Due: {due_pattern.group(1)}"
                })
                # Deep Document Understanding: Chronological Inversion (RULE-DOC-002)
                rule_doc2 = RULES.get('RULE-DOC-002')
                if rule_doc2:
                    findings.append({
                        'rule_id': rule_doc2['id'],
                        'title': rule_doc2['title'],
                        'severity': rule_doc2['severity'],
                        'category': rule_doc2['category'],
                        'status': 'Potential Anomaly',
                        'confidence': rule_doc2['confidence'],
                        'page_number': 1,
                        'coordinates': None,
                        'description': (
                            f"Chronological Inversion: Payment due date ({due_pattern.group(1)}) occurs prior to invoice issuance date ({inv_pattern.group(1)})."
                        ),
                        'evidence': f"Due Date ({due_pattern.group(1)}) < Issue Date ({inv_pattern.group(1)})"
                    })
        except ValueError:
            pass


    # -------------------------------------------------------------
    # Deep Document Understanding: Cross-Field Arithmetic (RULE-DOC-001)
    # -------------------------------------------------------------
    from backend.ner import normalize_structured_document_fields
    structured_doc = normalize_structured_document_fields(text, entities, category)
    fin = structured_doc.get('financials', {})
    val_sub = fin.get('subtotal')
    val_tax = fin.get('tax_amount')
    val_tot = fin.get('grand_total')

    if val_sub is not None and val_tax is not None and val_tot is not None:
        expected = round(val_sub + val_tax, 2)
        diff = round(abs(expected - val_tot), 2)
        if diff > 0.05:
            rule = RULES['RULE-DOC-001']
            findings.append({
                'rule_id': rule['id'],
                'title': rule['title'],
                'severity': rule['severity'],
                'category': rule['category'],
                'status': 'Potential Anomaly',
                'confidence': rule['confidence'],
                'page_number': 1,
                'coordinates': None,
                'description': (
                    f"Calculated arithmetic total (Subtotal: ${val_sub:,.2f} + Tax: ${val_tax:,.2f} = ${expected:,.2f}) "
                    f"does not match stated Grand Total: ${val_tot:,.2f} (Discrepancy: ${diff:,.2f}). "
                    "Indicates numerical modification of itemized breakdown or final total."
                ),
                'evidence': f"Subtotal (${val_sub:,.2f}) + Tax (${val_tax:,.2f}) = ${expected:,.2f} != Total (${val_tot:,.2f})"
            })

    # -------------------------------------------------------------
    # Deep Document Understanding: Duplicate Conflicting Totals (RULE-DOC-004)
    # -------------------------------------------------------------
    # Search for all mentions of "Total: $..." in document text
    all_totals = re.findall(r'(?:total\s+amount|grand\s+total|balance\s+due|amount\s+due|invoice\s+total|\btotal\b)[:\s]*[\$€£₹]?\s*([\d,]+(?:\.\d{1,2})?)', text, re.I)
    unique_totals = set()
    for t_str in all_totals:
        try:
            val = float(re.sub(r'[^0-9.]', '', t_str))
            if val > 0:
                unique_totals.add(val)
        except ValueError:
            pass

    # If there are 2 or more distinct total figures differing by more than $1.00
    if len(unique_totals) >= 2:
        sorted_totals = sorted(list(unique_totals))
        if sorted_totals[-1] - sorted_totals[0] > 1.00 and 'invoice' in category:
            rule = RULES['RULE-DOC-004']
            findings.append({
                'rule_id': rule['id'],
                'title': rule['title'],
                'severity': rule['severity'],
                'category': rule['category'],
                'status': 'Potential Anomaly',
                'confidence': rule['confidence'],
                'page_number': 1,
                'coordinates': None,
                'description': (
                    f"Document states contradictory grand total figures: {', '.join(f'${t:,.2f}' for t in sorted_totals)}. "
                    "Indicates disparate financial summaries or digital stamping over original totals."
                ),
                'evidence': f"Contradictory totals: {', '.join(f'${t:,.2f}' for t in sorted_totals)}"
            })

    # -------------------------------------------------------------
    # Deep Document Understanding: Expired Identification (RULE-DOC-005)
    # -------------------------------------------------------------
    doc_dates = structured_doc.get('dates', {})
    exp_str = doc_dates.get('expiration_date')
    cat_lower = category.lower() if category else ''
    if exp_str and ('id' in cat_lower or 'card' in cat_lower or 'passport' in cat_lower or structured_doc.get('document_type') == 'id_card'):
        try:
            iso_m = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', exp_str)
            if iso_m:
                exp_dt = datetime(int(iso_m.group(1)), int(iso_m.group(2)), int(iso_m.group(3)))
                if exp_dt < datetime.now():
                    rule_doc5 = RULES.get('RULE-DOC-005')
                    if rule_doc5:
                        findings.append({
                            'rule_id': rule_doc5['id'],
                            'title': rule_doc5['title'],
                            'severity': rule_doc5['severity'],
                            'category': rule_doc5['category'],
                            'status': 'Potential Anomaly',
                            'confidence': rule_doc5['confidence'],
                            'page_number': 1,
                            'coordinates': None,
                            'description': (
                                f"Identification credential is expired. Document expiration date '{exp_str}' precedes current operational date."
                            ),
                            'evidence': f"Expiration: {exp_str} < Current Date"
                        })
        except Exception:
            pass

    # Rule 4: Conflicting Monetary Values & Currencies (RULE-CTX-004)
    money_entries = entities.get('monetary_values', [])
    currencies_found = set()
    for m in money_entries:
        val = m['value']
        for curr in ['$', '€', '£', '₹', 'USD', 'EUR', 'GBP', 'INR']:
            if curr in val:
                currencies_found.add(curr.replace('$', 'USD').replace('€', 'EUR').replace('£', 'GBP').replace('₹', 'INR'))

    if len(currencies_found) > 1 and 'invoice' in category:
        rule = RULES['RULE-CTX-004']
        findings.append({
            'rule_id': rule['id'],
            'title': rule['title'],
            'severity': rule['severity'],
            'category': rule['category'],
            'status': 'Potential Anomaly',
            'confidence': rule['confidence'],
            'page_number': 1,
            'coordinates': None,
            'description': f"Document references multiple conflicting currencies ({', '.join(sorted(currencies_found))}) within a single billing statement.",
            'evidence': f"Currencies: {', '.join(sorted(currencies_found))}"
        })

    # Rule 5: Metadata vs. Document Content Mismatch (RULE-CTX-005)
    meta = doc_metadata or {}
    meta_creation = meta.get('creationDate')
    if meta_creation and parsed_dates:
        # PyMuPDF creationDate is often D:YYYYMMDD... or YYYY-MM-DD
        meta_year_match = re.search(r'(?:D:)?(\d{4})', str(meta_creation))
        if meta_year_match:
            meta_year = int(meta_year_match.group(1))
            body_years = [d[0].year for d in parsed_dates]
            # If body claims an agreement date > 3 years before metadata creation
            if body_years and min(body_years) < meta_year - 3:
                rule = RULES['RULE-CTX-005']
                findings.append({
                    'rule_id': rule['id'],
                    'title': rule['title'],
                    'severity': rule['severity'],
                    'category': rule['category'],
                    'status': 'Potential Anomaly',
                    'confidence': rule['confidence'],
                    'page_number': 1,
                    'coordinates': None,
                    'description': (
                        f"PDF technical creation timestamp indicates {meta_year}, while document content references historical date "
                        f"({min(body_years)}). Potential reproduction or metadata desynchronization."
                    ),
                    'evidence': f"Metadata Year: {meta_year} vs Content Year: {min(body_years)}"
                })

    return findings

# =====================================================================
# 3. Risk Assessment & Score Computation
# =====================================================================

def calculate_risk_assessment(findings):
    """
    Calculates composite forensic risk score (0-100) and risk level tier.
    """
    weights = {
        'Critical': 35,
        'High': 20,
        'Medium': 10,
        'Low': 5,
        'Info': 0
    }

    raw_score = 0
    severity_counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0, 'Info': 0}

    for f in findings:
        sev = f.get('severity', 'Low')
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        raw_score += weights.get(sev, 5)

    risk_score = min(raw_score, 100)

    if risk_score >= 60 or severity_counts['Critical'] > 0:
        risk_level = 'Critical Risk'
    elif risk_score >= 35 or severity_counts['High'] > 0:
        risk_level = 'High Risk'
    elif risk_score >= 15:
        risk_level = 'Medium Risk'
    elif risk_score > 0:
        risk_level = 'Low Risk'
    else:
        risk_level = 'Clean / Verified'

    anomalies = [f for f in findings if f.get('severity') != 'Info' and f.get('rule_id')]
    total = len(anomalies)
    if total == 0 and risk_score == 0:
        risk_level = 'Clean / Verified'
        summary = "No visual anomalies or contextual contradictions detected across evaluated forensic rules."
    else:
        summary = (
            f"Evaluated against 10 visual & contextual forensic rules. "
            f"Identified {total} potential anomaly/inconsistency item(s) requiring investigator verification."
        )

    return {
        'risk_score': risk_score,
        'risk_level': risk_level,
        'severity_breakdown': severity_counts,
        'summary': summary
    }

def resolve_document_file_path(doc):
    """
    Resolves the physical filesystem path for a document, checking
    direct paths, active Flask UPLOAD_FOLDER configuration, and default storage paths.
    """
    raw_path = doc.get('file_path')
    if not raw_path:
        return None

    # 1. Try direct path
    p = Path(raw_path)
    if p.exists():
        return str(p.resolve())

    # 2. Check within active Flask current_app UPLOAD_FOLDER
    try:
        from flask import current_app, has_app_context
        if has_app_context() and current_app and current_app.config.get('UPLOAD_FOLDER'):
            candidate = Path(current_app.config['UPLOAD_FOLDER']) / p.name
            if candidate.exists():
                return str(candidate.resolve())
    except Exception:
        pass

    # 3. Check within default Config.UPLOAD_FOLDER
    try:
        from backend.config import Config
        candidate = Path(Config.UPLOAD_FOLDER) / p.name
        if candidate.exists():
            return str(candidate.resolve())
    except Exception:
        pass

    return None

# =====================================================================
# 4. Master Document Analysis Coordinator
# =====================================================================

def analyze_document(doc_id, user="System"):
    """
    Main orchestration routine for Phase 6.
    Ensures extraction is current, executes visual and contextual rule engines,
    persists findings to SQLite, updates document status, and returns a comprehensive report.
    """
    doc = get_document_by_id(doc_id)
    if not doc:
        return {'success': False, 'error': f"Document '{doc_id}' not found."}

    file_path = resolve_document_file_path(doc)
    if not file_path or not os.path.exists(file_path):
        return {'success': False, 'error': f"File for document '{doc_id}' does not exist on disk."}

    # Ensure document extraction is present
    extraction_data = None
    extracted_text = doc.get('extracted_text')
    if doc.get('extracted_data'):
        try:
            extraction_data = json.loads(doc['extracted_data'])
        except Exception:
            extraction_data = None

    if not extraction_data:
        try:
            extraction_data = extract_document_content(file_path)
            extracted_text = extraction_data.get('full_text', '')
            save_document_extraction(doc_id, extraction_data, user=user)
        except Exception as e:
            return {'success': False, 'error': f"Failed to extract document for analysis: {str(e)}"}

    # Phase F Hook: Content-Based Classification Fallback (used strictly if 'General Document' or 'Uncategorized')
    if (doc.get('category') in ('General Document', 'Uncategorized', 'Scanned Artifact', None)) and extracted_text:
        try:
            from backend.classifier_content import classify_by_content
            new_cat, new_conf = classify_by_content(extracted_text, filename=doc.get('filename', ''), file_type=doc.get('file_type', 'pdf'))
            if new_cat and new_cat != 'General Document':
                doc['category'] = new_cat
                doc['classification_confidence'] = new_conf
                from backend.models import update_document_category
                update_document_category(doc_id, new_cat, new_conf, user=user)
        except Exception:
            pass

    # 1. Visual & Structural Analysis
    visual_findings = analyze_visual_structure(file_path)

    # 2. Contextual & Semantic Analysis
    context_findings = analyze_contextual_rules(
        doc.get('category'),
        extracted_text,
        extraction_data,
        extraction_data.get('metadata')
    )

    all_findings = visual_findings + context_findings

    # V2 Phase B Hook: Extended PDF Forensics (PDF-001 to PDF-005)
    try:
        from backend.config import Config
        if getattr(Config, 'ENABLE_EXTENDED_FORENSICS', False):
            from backend.forensics_pdf import run_extended_pdf_forensics
            extended_pdf_findings = run_extended_pdf_forensics(file_path)
            all_findings.extend(extended_pdf_findings)
    except Exception as pdf_ext_err:
        pass

    # V2 Phase D Hook: Image Forensics for Scans & Photos (IMG-001 to IMG-004)
    try:
        from backend.config import Config
        img_flag = getattr(Config, 'ENABLE_IMAGE_FORENSICS', False)
        try:
            from flask import current_app, has_app_context
            if has_app_context() and current_app and 'ENABLE_IMAGE_FORENSICS' in current_app.config:
                img_flag = current_app.config.get('ENABLE_IMAGE_FORENSICS', False)
        except Exception:
            pass

        if img_flag:
            from backend.forensics_image import run_image_forensics
            doc_cat = doc.get('category') if isinstance(doc, dict) else getattr(doc, 'category', None)
            img_findings = run_image_forensics(file_path, doc_category=doc_cat)
            all_findings.extend(img_findings)
    except Exception as img_ext_err:
        pass

    # Annotate findings with objective evidence class labels
    try:
        from backend.evidence_class import classify_finding
        for f in all_findings:
            classify_finding(f)
    except Exception:
        pass

    # 3. Calculate Risk Assessment
    assessment = calculate_risk_assessment(all_findings)

    # 4. Persist findings to database
    saved_records = save_document_findings(doc_id, all_findings, user=user)

    return {
        'success': True,
        'document_id': doc_id,
        'case_id': doc.get('case_id'),
        'filename': doc.get('filename'),
        'findings_count': len(saved_records),
        'risk_score': assessment['risk_score'],
        'risk_level': assessment['risk_level'],
        'severity_breakdown': assessment['severity_breakdown'],
        'summary': assessment['summary'],
        'findings': saved_records,
        'analyzed_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
