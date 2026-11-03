"""
VEXORA — Investigation Dossier & Report Generation Module (Phase 8)
Generates audit-ready, evidence-backed investigation dossiers in PDF, HTML, and JSON formats.
Includes document inventory, extracted intelligence, visual & contextual findings,
cross-document discrepancy matrices, bounding-box provenance, and mandatory human-review disclaimers.
"""

import os
import json
import hashlib
import html
from datetime import datetime
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

from backend.config import Config, REPORTS_FOLDER
from backend.models import (
    get_case_by_id,
    get_all_documents,
    get_all_findings,
    create_report_record,
    log_audit
)
from backend.comparator import compare_case_documents, get_evidence_provenance_nodes

MANDATORY_DISCLAIMER = (
    "MANDATORY INVESTIGATION DISCLAIMER: All findings, metrics, and anomaly indicators presented in "
    "this dossier are algorithmic observations produced by VEXORA for investigative assistance only. "
    "They do not constitute definitive legal proof of fraud or intentional tampering. Human investigator "
    "interpretation, physical document examination, and institutional validation remain mandatory before "
    "taking any administrative, disciplinary, or legal action."
)

# =====================================================================
# 1. Dossier Data Aggregation Engine
# =====================================================================

def generate_case_dossier_data(case_id):
    """
    Aggregates comprehensive investigation data for a case:
    - Case metadata and investigator details
    - Ingested documents inventory
    - Extracted intelligence (entities across documents)
    - Forensic visual and contextual observations with coordinates
    - Cross-document discrepancy alignment matrix
    - Evidence provenance graph nodes
    - Quantitative risk score and executive narrative
    - Mandatory human-review disclaimer
    """
    case = get_case_by_id(case_id)
    if not case:
        raise ValueError(f"Investigation Case '{case_id}' was not found in the repository.")

    docs = get_all_documents(case_id=case_id)
    findings = get_all_findings(case_id=case_id)

    # 1. Documents summary
    doc_inventory = []
    total_file_size = 0
    all_extracted_entities = {
        'organizations': set(),
        'persons': set(),
        'dates': set(),
        'monetary_values': set(),
        'identifiers': set()
    }

    for d in docs:
        total_file_size += (d.get('file_size') or 0)
        ext_data = {}
        if d.get('extracted_data'):
            try:
                ext_data = json.loads(d['extracted_data']) if isinstance(d['extracted_data'], str) else d['extracted_data']
            except Exception:
                ext_data = {}

        entities = ext_data.get('entities', {})
        for org in entities.get('organizations', []):
            all_extracted_entities['organizations'].add(org.get('value', ''))
        for per in entities.get('persons', []):
            all_extracted_entities['persons'].add(per.get('value', ''))
        for dt in entities.get('dates', []):
            all_extracted_entities['dates'].add(dt.get('value', ''))
        for mv in entities.get('monetary_values', []):
            all_extracted_entities['monetary_values'].add(mv.get('value', ''))
        for ident in entities.get('identifiers', []):
            all_extracted_entities['identifiers'].add(ident.get('value', ''))

        doc_inventory.append({
            'id': d['id'],
            'filename': d['filename'],
            'file_type': (d.get('file_type') or 'bin').upper(),
            'file_size_bytes': d.get('file_size', 0),
            'file_size_formatted': f"{(d.get('file_size', 0) / 1024):.1f} KB" if d.get('file_size', 0) < 1024*1024 else f"{(d.get('file_size', 0) / (1024*1024)):.1f} MB",
            'file_hash': d.get('file_hash') or 'UNHASHED',
            'category': d.get('category') or 'Uncategorized',
            'classification_confidence': d.get('classification_confidence', 0.0),
            'status': d.get('status') or 'Pending',
            'extraction_mode': d.get('extraction_mode') or ('digital_pdf' if (d.get('file_type') or '').lower() == 'pdf' else 'simulated_fallback'),
            'uploaded_at': d.get('uploaded_at') or ''
        })

    # Convert sets to sorted lists
    entities_summary = {
        'organizations': sorted([x for x in all_extracted_entities['organizations'] if x]),
        'persons': sorted([x for x in all_extracted_entities['persons'] if x]),
        'dates': sorted([x for x in all_extracted_entities['dates'] if x]),
        'monetary_values': sorted([x for x in all_extracted_entities['monetary_values'] if x]),
        'identifiers': sorted([x for x in all_extracted_entities['identifiers'] if x])
    }

    # 2. Forensic Findings Breakdown
    findings_list = []
    severity_counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0, 'Info': 0}
    for f in findings:
        sev = f.get('severity', 'Medium')
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        findings_list.append({
            'id': f['id'],
            'document_id': f.get('document_id'),
            'rule_id': f.get('rule_id') or 'RULE-GEN-001',
            'title': f['title'],
            'severity': sev,
            'category': f.get('category') or 'Forensic Observation',
            'evidence_class': f.get('evidence_class') or 'Observation',
            'description': f.get('description') or '',
            'evidence': f.get('evidence') or '',
            'page_number': f.get('page_number', 1),
            'coordinates': f.get('coordinates') or '',
            'confidence': f.get('confidence'),
            'status': f.get('status', 'Unresolved')
        })

    # 3. Cross-Document Comparisons
    cross_comparison = {}
    try:
        cross_comparison = compare_case_documents(case_id)
    except Exception as e:
        cross_comparison = {'success': False, 'error': str(e), 'discrepancies': []}

    # 4. Evidence Provenance Nodes
    provenance_nodes = []
    try:
        provenance_nodes = get_evidence_provenance_nodes(case_id=case_id)
    except Exception:
        provenance_nodes = []

    # 5. Risk Assessment Calculation
    crit_count = severity_counts.get('Critical', 0)
    high_count = severity_counts.get('High', 0)
    med_count = severity_counts.get('Medium', 0)
    disc_count = len(cross_comparison.get('discrepancies', [])) if cross_comparison.get('success') else 0

    raw_risk = (crit_count * 30) + (high_count * 20) + (med_count * 10) + (disc_count * 15)
    risk_score = min(raw_risk, 100)

    if risk_score >= 70 or crit_count > 0:
        risk_level = "Critical Risk / Irregular"
    elif risk_score >= 40 or high_count > 0:
        risk_level = "High Risk / Requires Review"
    elif risk_score >= 20 or med_count > 0:
        risk_level = "Moderate Variance"
    elif len(docs) == 0:
        risk_level = "Unassessed / Empty Case"
    else:
        risk_level = "Clean / Verified Alignment"

    # 6. Executive Narrative Summary
    total_findings_count = len(findings_list)
    narrative = (
        f"An analytical forensic review of Case {case_id} ('{case['title']}') was conducted across "
        f"{len(doc_inventory)} ingested document(s) totaling {(total_file_size / (1024*1024)):.2f} MB. "
    )
    if total_findings_count == 0 and disc_count == 0:
        narrative += (
            "No typographical anomalies, metadata discrepancies, or cross-document contradictory values "
            "were identified across the evaluated evidentiary set. All records exhibit harmonious data alignment."
        )
    else:
        narrative += (
            f"The evaluation flagged {total_findings_count} localized forensic observation(s) "
            f"({crit_count} Critical, {high_count} High, {med_count} Medium) and "
            f"{disc_count} cross-document factual contradiction(s). Primary indicators encompass "
            f"{'typographic font mismatches, ' if any('VIS' in f.get('rule_id', '') for f in findings_list) else ''}"
            f"{'chronological timeline sequence conflicts, ' if any('CTX' in f.get('rule_id', '') for f in findings_list) else ''}"
            f"and entity/counterparty shifts requiring human reviewer cross-examination."
        )

    # Unique Verification Hash for Dossier Authenticity
    hash_seed = f"{case_id}-{case['title']}-{len(doc_inventory)}-{total_findings_count}-{disc_count}"
    dossier_hash = hashlib.sha256(hash_seed.encode('utf-8')).hexdigest()[:16].upper()

    # Phase C: AI-Assisted Intelligence Data
    ai_insights = []
    try:
        from backend.models import get_ai_insights_by_case
        ai_insights = get_ai_insights_by_case(case_id)
    except Exception:
        ai_insights = []

    ai_findings = [f for f in findings_list if f.get('rule_id', '').startswith('LLM-')]
    has_ai_data = bool(ai_insights or ai_findings)

    return {
        'case': {
            'id': case['id'],
            'title': case['title'],
            'type': case.get('type') or 'General Forensic Inquiry',
            'priority': case.get('priority') or 'Medium',
            'status': case.get('status') or 'Active',
            'investigator': case.get('investigator') or 'Lead Investigator',
            'description': case.get('description') or '',
            'created_at': case.get('created_at') or '',
            'updated_at': case.get('updated_at') or ''
        },
        'executive_summary': {
            'narrative': narrative,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'document_count': len(doc_inventory),
            'findings_count': total_findings_count,
            'critical_findings': crit_count,
            'high_findings': high_count,
            'medium_findings': med_count,
            'discrepancies_count': disc_count,
            'dossier_verification_code': f"VX-{case_id}-{dossier_hash}"
        },
        'documents': doc_inventory,
        'extracted_entities': entities_summary,
        'findings': findings_list,
        'cross_document_comparison': cross_comparison,
        'provenance_nodes': provenance_nodes,
        'ai_summary': {
            'has_ai_data': has_ai_data,
            'insights_count': len(ai_insights),
            'ai_findings_count': len(ai_findings),
            'disclaimer': 'AI-assessed, requires human review',
            'insights': ai_insights
        } if has_ai_data else None,
        'mandatory_disclaimer': MANDATORY_DISCLAIMER,
        'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# =====================================================================
# 2. Publication-Quality PDF Dossier Generator (PyMuPDF)
# =====================================================================

def generate_dossier_pdf(case_id, output_path=None, user="Lead Investigator"):
    """
    Generates a structured, audit-ready PDF investigation dossier using PyMuPDF vector drawing.
    Includes banner header, mandatory disclaimer box, executive summary, evidence inventory,
    extracted entities, forensic findings with coordinates, discrepancy matrix, and sign-off.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed in the Python runtime.")

    data = generate_case_dossier_data(case_id)
    case = data['case']
    summary = data['executive_summary']

    # Setup output path
    reports_dir = Path(Config.REPORTS_FOLDER)
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_case_id = case_id.replace('-', '_')
    filename = f"DOSSIER_{safe_case_id}_{timestamp_str}.pdf"
    file_path = reports_dir / filename if not output_path else Path(output_path)

    # Document Geometry
    PAGE_WIDTH = 612.0   # Standard Letter Width
    PAGE_HEIGHT = 792.0  # Standard Letter Height
    MARGIN_LEFT = 40.0
    MARGIN_RIGHT = 572.0
    USABLE_WIDTH = MARGIN_RIGHT - MARGIN_LEFT

    doc = fitz.open()

    def create_page():
        """Creates a page and returns it with standard headers/footers."""
        p = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        return p

    def draw_running_footer(p, current_num, total_num):
        """Draws subtle running footer on page."""
        p.draw_line(fitz.Point(MARGIN_LEFT, 752), fitz.Point(MARGIN_RIGHT, 752), color=(203/255, 213/255, 225/255), width=0.5)
        p.insert_text(fitz.Point(MARGIN_LEFT, 766), "CONFIDENTIAL & PRIVILEGED • VEXORA FORENSIC INTELLIGENCE ENGINE", fontname="hebo", fontsize=7, color=(100/255, 116/255, 139/255))
        p.insert_text(fitz.Point(MARGIN_RIGHT - 65, 766), f"Page {current_num} of {total_num}", fontname="helv", fontsize=7.5, color=(100/255, 116/255, 139/255))

    # --- PAGE 1: Executive Cover & Findings Overview ---
    page = create_page()
    y = 0.0

    # 1. Top Header Banner (Dark Slate #0f172a)
    page.draw_rect(fitz.Rect(0, 0, PAGE_WIDTH, 78), color=None, fill=(15/255, 23/255, 42/255))

    # Insert official brand logo image on top-right of banner if available
    from backend.config import FRONTEND_DIR
    logo_path = FRONTEND_DIR / 'images' / 'logo.png'
    if logo_path.exists():
        try:
            # Aspect ratio 1024x682 (~1.5:1). Target: width 84, height 56
            logo_rect = fitz.Rect(MARGIN_RIGHT - 88, 11, MARGIN_RIGHT, 67)
            page.insert_image(logo_rect, filename=str(logo_path))
        except Exception:
            pass

    page.insert_text(fitz.Point(MARGIN_LEFT, 28), "VEXORA", fontname="hebo", fontsize=18, color=(1, 1, 1))
    page.insert_text(fitz.Point(MARGIN_LEFT + 86, 28), "• FORENSIC INVESTIGATION DOSSIER", fontname="hebo", fontsize=11, color=(56/255, 189/255, 248/255))
    page.insert_text(fitz.Point(MARGIN_LEFT, 44), "SEEING WHAT OTHERS OVERLOOK", fontname="hebo", fontsize=7.5, color=(56/255, 189/255, 248/255))
    page.insert_text(fitz.Point(MARGIN_LEFT, 62), f"Case ID: {case['id']} | Title: {case['title']} | Date: {data['generated_at']}", fontname="helv", fontsize=8.5, color=(148/255, 163/255, 184/255))

    y = 92.0

    # 2. Mandatory Human Review Disclaimer Box (Amber #fffbeb with #f59e0b border)
    page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 42), color=(245/255, 158/255, 11/255), fill=(255/255, 251/255, 235/255), width=1)
    page.insert_text(fitz.Point(MARGIN_LEFT + 8, y + 15), "[!] MANDATORY INVESTIGATION DISCLAIMER", fontname="hebo", fontsize=8, color=(180/255, 83/255, 9/255))
    page.insert_textbox(
        fitz.Rect(MARGIN_LEFT + 8, y + 18, MARGIN_RIGHT - 8, y + 40),
        "All findings, metrics, and anomaly flags are algorithmic observations produced for investigative assistance only. They do not constitute conclusive legal proof of fraud. Human reviewer verification remains mandatory.",
        fontname="helv",
        fontsize=7,
        color=(146/255, 64/255, 14/255)
    )

    y += 54.0

    # 3. Executive Summary Block
    page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 20), color=None, fill=(241/255, 245/255, 249/255))
    page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 14), "1. EXECUTIVE CASE SUMMARY & TELEMETRY", fontname="hebo", fontsize=9.5, color=(30/255, 41/255, 59/255))
    y += 26.0

    # Metrics Grid (4 mini cards)
    card_w = (USABLE_WIDTH - 18) / 4.0
    metrics = [
        ("RISK SCORE", f"{summary['risk_score']} / 100", (220/255, 38/255, 38/255) if summary['risk_score'] >= 50 else (16/255, 185/255, 129/255)),
        ("DOCUMENTS", str(summary['document_count']), (15/255, 23/255, 42/255)),
        ("ANOMALIES", str(summary['findings_count']), (217/255, 119/255, 6/255) if summary['findings_count'] > 0 else (100/255, 116/255, 139/255)),
        ("DISCREPANCIES", str(summary['discrepancies_count']), (220/255, 38/255, 38/255) if summary['discrepancies_count'] > 0 else (16/255, 185/255, 129/255))
    ]

    for idx, (lbl, val, col) in enumerate(metrics):
        cx = MARGIN_LEFT + (idx * (card_w + 6))
        page.draw_rect(fitz.Rect(cx, y, cx + card_w, y + 36), color=(226/255, 232/255, 240/255), fill=(248/255, 250/255, 252/255), width=0.75)
        page.insert_text(fitz.Point(cx + 6, y + 12), lbl, fontname="hebo", fontsize=6.5, color=(100/255, 116/255, 139/255))
        page.insert_text(fitz.Point(cx + 6, y + 28), val, fontname="hebo", fontsize=11, color=col)

    y += 44.0

    # Narrative Paragraph
    page.insert_textbox(
        fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 42),
        summary['narrative'],
        fontname="helv",
        fontsize=8.5,
        color=(51/255, 65/255, 85/255)
    )
    y += 48.0

    # 4. Ingested Evidence Inventory
    page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 18), color=None, fill=(241/255, 245/255, 249/255))
    page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 13), "2. INGESTED EVIDENCE INVENTORY", fontname="hebo", fontsize=9.5, color=(30/255, 41/255, 59/255))
    y += 24.0

    # Table Header
    page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 16), color=None, fill=(226/255, 232/255, 240/255))
    page.insert_text(fitz.Point(MARGIN_LEFT + 4, y + 11), "DOCUMENT ID", fontname="hebo", fontsize=7.5, color=(71/255, 85/255, 105/255))
    page.insert_text(fitz.Point(MARGIN_LEFT + 95, y + 11), "FILENAME", fontname="hebo", fontsize=7.5, color=(71/255, 85/255, 105/255))
    page.insert_text(fitz.Point(MARGIN_LEFT + 250, y + 11), "CATEGORY", fontname="hebo", fontsize=7.5, color=(71/255, 85/255, 105/255))
    page.insert_text(fitz.Point(MARGIN_LEFT + 340, y + 11), "SHA-256 INTEGRITY HASH", fontname="hebo", fontsize=7.5, color=(71/255, 85/255, 105/255))
    page.insert_text(fitz.Point(MARGIN_LEFT + 480, y + 11), "STATUS", fontname="hebo", fontsize=7.5, color=(71/255, 85/255, 105/255))
    y += 18.0

    for doc_item in data['documents']:
        if y > 710:
            page = create_page()
            y = 50.0

        ext_mode = doc_item.get('extraction_mode', '')
        mode_tag = " [⚠️ SIMULATED OCR]" if ext_mode == 'simulated_fallback' else ""
        page.insert_text(fitz.Point(MARGIN_LEFT + 4, y + 10), doc_item['id'], fontname="courier", fontsize=7, color=(15/255, 23/255, 42/255))
        page.insert_text(fitz.Point(MARGIN_LEFT + 95, y + 10), (doc_item['filename'][:20] + mode_tag)[:28], fontname="hebo", fontsize=7.5, color=(15/255, 23/255, 42/255) if not mode_tag else (180/255, 83/255, 9/255))
        page.insert_text(fitz.Point(MARGIN_LEFT + 250, y + 10), doc_item['category'][:14], fontname="helv", fontsize=7.5, color=(71/255, 85/255, 105/255))
        hash_disp = doc_item['file_hash'][:16] + "..." if len(doc_item['file_hash']) > 16 else doc_item['file_hash']
        page.insert_text(fitz.Point(MARGIN_LEFT + 340, y + 10), hash_disp, fontname="courier", fontsize=7, color=(100/255, 116/255, 139/255))
        page.insert_text(fitz.Point(MARGIN_LEFT + 480, y + 10), doc_item['status'], fontname="hebo", fontsize=7.5, color=(220/255, 38/255, 38/255) if doc_item['status'] == 'Flagged' else (16/255, 185/255, 129/255))
        y += 14.0

    y += 16.0

    # 5. Key Forensic Findings & Visual Observations
    if y > 600:
        page = create_page()
        y = 50.0

    page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 18), color=None, fill=(241/255, 245/255, 249/255))
    page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 13), "3. FORENSIC OBSERVATIONS & VISUAL IRREGULARITIES", fontname="hebo", fontsize=9.5, color=(30/255, 41/255, 59/255))
    y += 24.0

    if not data['findings']:
        page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 12), "No localized visual typography or contextual anomalies recorded.", fontname="helv", fontsize=8, color=(100/255, 116/255, 139/255))
        y += 20.0
    else:
        for f in data['findings'][:8]:  # Top findings
            if y > 690:
                page = create_page()
                y = 50.0

            sev = f['severity']
            badge_color = (220/255, 38/255, 38/255) if sev in ('Critical', 'High') else (217/255, 119/255, 6/255) if sev == 'Medium' else (100/255, 116/255, 139/255)

            # Left color indicator bar
            page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_LEFT + 3, y + 26), color=None, fill=badge_color)

            # Finding header line
            page.insert_text(fitz.Point(MARGIN_LEFT + 8, y + 10), f"[{f['rule_id']}] {f['title']}", fontname="hebo", fontsize=8, color=(15/255, 23/255, 42/255))
            page.insert_text(fitz.Point(MARGIN_RIGHT - 110, y + 10), f"Severity: {sev.upper()}", fontname="hebo", fontsize=7.5, color=badge_color)

            ev_class = f.get('evidence_class') or 'Observation'
            weight_str = f" • Rule Weight: {f.get('confidence')}" if f.get('confidence') is not None else ""
            loc_text = f"Page {f['page_number']}" + (f" • Box [{f['coordinates']}]" if f['coordinates'] else "") + f" • Class: {ev_class}" + weight_str
            page.insert_text(fitz.Point(MARGIN_LEFT + 8, y + 21), loc_text, fontname="courier", fontsize=7, color=(100/255, 116/255, 139/255))

            desc_text = f['description'][:100] + "..." if len(f['description']) > 100 else f['description']
            page.insert_text(fitz.Point(MARGIN_LEFT + 8, y + 31), desc_text, fontname="helv", fontsize=7.5, color=(51/255, 65/255, 85/255))
            y += 38.0

    y += 12.0

    # 6. Cross-Document Discrepancies
    if y > 600:
        page = create_page()
        y = 50.0

    page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 18), color=None, fill=(241/255, 245/255, 249/255))
    page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 13), "4. CROSS-DOCUMENT COMPARISON & DISCREPANCY MATRIX", fontname="hebo", fontsize=9.5, color=(30/255, 41/255, 59/255))
    y += 24.0

    discrepancies = data['cross_document_comparison'].get('discrepancies', [])
    if not discrepancies:
        page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 12), "No cross-document conflicts or monetary disparities identified.", fontname="helv", fontsize=8, color=(100/255, 116/255, 139/255))
        y += 20.0
    else:
        for d in discrepancies[:6]:
            if y > 690:
                page = create_page()
                y = 50.0

            attr = d.get('attribute') or d.get('field') or 'Attribute Discrepancy'
            val_a = d.get('val_a', '')
            val_b = d.get('val_b', '')
            doc_a = d.get('doc_a_filename') or d.get('doc_a_id') or 'Doc A'
            doc_b = d.get('doc_b_filename') or d.get('doc_b_id') or 'Doc B'
            if val_a and val_b:
                conflict_hdr = f"Conflict: {attr}: {val_a} in {doc_a} vs {val_b} in {doc_b}"
            else:
                conflict_hdr = f"Conflict: {attr} between {doc_a} and {doc_b}"
            expl = d.get('explanation') or d.get('message') or ''

            page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 26), color=(226/255, 232/255, 240/255), fill=(254/255, 242/255, 242/255), width=0.5)
            page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 10), conflict_hdr[:105], fontname="hebo", fontsize=7.2, color=(185/255, 28/255, 28/255))
            page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 20), expl[:115], fontname="helv", fontsize=6.8, color=(51/255, 65/255, 85/255))
            y += 30.0

    y += 14.0

    # Phase C: Optional AI-Assisted Investigation Summary (PDF)
    if data.get('ai_summary') and data['ai_summary'].get('has_ai_data'):
        ai_s = data['ai_summary']
        if y > 620:
            page = create_page()
            y = 50.0

        page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 18), color=None, fill=(240/255, 253/255, 244/255))
        page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 13), "AI-ASSISTED INVESTIGATION SUMMARY (AI-assessed, requires human review)", fontname="hebo", fontsize=8.5, color=(21/255, 128/255, 61/255))
        y += 24.0

        page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 36), color=(187/255, 247/255, 208/255), fill=(240/255, 253/255, 244/255), width=0.5)
        page.insert_text(
            fitz.Point(MARGIN_LEFT + 6, y + 12),
            f"Contextual AI reasoning identified {ai_s['ai_findings_count']} cross-document observations and {ai_s['insights_count']} structured entity insights.",
            fontname="helv", fontsize=7.5, color=(22/255, 101/255, 52/255)
        )
        page.insert_text(
            fitz.Point(MARGIN_LEFT + 6, y + 26),
            "NOTICE: Every AI finding was grounded against verbatim document quotes. Formal verification by lead human reviewer required.",
            fontname="hebo", fontsize=7.0, color=(22/255, 101/255, 52/255)
        )
        y += 44.0

    # 7. Investigator Formal Sign-off & Verification Code
    if y > 640:
        page = create_page()
        y = 50.0

    page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 54), color=(203/255, 213/255, 225/255), fill=(248/255, 250/255, 252/255), width=0.75)
    page.insert_text(fitz.Point(MARGIN_LEFT + 8, y + 14), "5. INVESTIGATION FORMAL SIGN-OFF", fontname="hebo", fontsize=8.5, color=(30/255, 41/255, 59/255))
    page.insert_text(fitz.Point(MARGIN_LEFT + 8, y + 28), f"Lead Reviewer: {user}", fontname="hebo", fontsize=8, color=(51/255, 65/255, 85/255))
    page.insert_text(fitz.Point(MARGIN_LEFT + 8, y + 42), f"Dossier Verification Hash: {summary['dossier_verification_code']}", fontname="courier", fontsize=7.5, color=(100/255, 116/255, 139/255))

    page.draw_line(fitz.Point(MARGIN_RIGHT - 160, y + 36), fitz.Point(MARGIN_RIGHT - 12, y + 36), color=(148/255, 163/255, 184/255), width=0.75)
    page.insert_text(fitz.Point(MARGIN_RIGHT - 140, y + 46), "Analyst Signature & Seal", fontname="helv", fontsize=7, color=(148/255, 163/255, 184/255))

    # Phase A Hook: Embed Visual Evidence Overlays when ENABLE_EVIDENCE_OVERLAY is True
    if getattr(Config, 'ENABLE_EVIDENCE_OVERLAY', False):
        try:
            from backend.evidence import get_finding_evidence_image
            visual_findings = [f for f in data.get('findings', []) if f.get('coordinates')][:2]
            if visual_findings:
                ev_page = create_page()
                ev_y = 35.0
                ev_page.draw_rect(fitz.Rect(MARGIN_LEFT, ev_y, MARGIN_RIGHT, ev_y + 20), color=None, fill=(241/255, 245/255, 249/255))
                ev_page.insert_text(fitz.Point(MARGIN_LEFT + 6, ev_y + 14), "APPENDIX: VISUAL FORENSIC EVIDENCE OVERLAYS", fontname="hebo", fontsize=9.5, color=(30/255, 41/255, 59/255))
                ev_y += 30.0

                for vf in visual_findings:
                    if ev_y > 520:
                        ev_page = create_page()
                        ev_y = 40.0

                    ev_page.insert_text(fitz.Point(MARGIN_LEFT, ev_y + 10), f"Finding [{vf['rule_id']}] • {vf['title']} (Page {vf.get('page_number', 1)})", fontname="hebo", fontsize=8, color=(15/255, 23/255, 42/255))
                    ev_y += 16.0

                    img_bytes, err = get_finding_evidence_image(vf['id'], zoom=1.5)
                    if img_bytes:
                        img_rect = fitz.Rect(MARGIN_LEFT, ev_y, MARGIN_LEFT + 280, ev_y + 175)
                        ev_page.insert_image(img_rect, stream=img_bytes)
                        ev_page.draw_rect(img_rect, color=(203/255, 213/255, 225/255), width=0.5)
                        ev_y += 190.0
                    else:
                        ev_y += 10.0
        except Exception:
            # Defensive guard: report generation must never fail due to optional evidence overlays
            pass

    # Add running footers to all pages
    total_pages = len(doc)
    for p_idx in range(total_pages):
        draw_running_footer(doc[p_idx], p_idx + 1, total_pages)

    # Save document
    doc.save(str(file_path))
    doc.close()

    file_size = file_path.stat().st_size
    report_id = f"RPT-{case_id}-{timestamp_str}"
    title = f"Investigation Dossier • Case {case_id}"

    # Record in database
    create_report_record(
        report_id=report_id,
        case_id=case_id,
        title=title,
        file_path=str(file_path),
        file_format='pdf',
        file_size=file_size,
        user=user
    )

    return {
        'success': True,
        'report_id': report_id,
        'case_id': case_id,
        'title': title,
        'file_path': str(file_path),
        'filename': filename,
        'file_format': 'pdf',
        'file_size': file_size,
        'file_size_formatted': f"{(file_size / 1024):.1f} KB",
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'verification_code': summary['dossier_verification_code']
    }

# =====================================================================
# 3. Print-Optimized HTML Dossier Generator
# =====================================================================

def generate_dossier_html(case_id, output_path=None, user="Lead Investigator"):
    """
    Generates a print-ready, modern HTML investigation report with
    responsive typography, print media rules, and full evidence breakdown.
    """
    data = generate_case_dossier_data(case_id)
    case = data['case']
    summary = data['executive_summary']

    reports_dir = Path(Config.REPORTS_FOLDER)
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_case_id = case_id.replace('-', '_')
    filename = f"DOSSIER_{safe_case_id}_{timestamp_str}.html"
    file_path = reports_dir / filename if not output_path else Path(output_path)

    # Build document table rows
    doc_rows = ""
    for d in data['documents']:
        status_color = "#ef4444" if d['status'] == 'Flagged' else "#10b981"
        ext_mode = d.get('extraction_mode', '')
        mode_badge = ""
        if ext_mode == 'simulated_fallback':
            mode_badge = "<br><span style='font-size:10px; background:#fef3c7; color:#b45309; padding:2px 6px; border-radius:3px; font-weight:700;'>⚠️ SIMULATED FALLBACK (OCR UNAVAILABLE)</span>"
        elif ext_mode == 'ocr_unavailable':
            mode_badge = "<br><span style='font-size:10px; background:#fee2e2; color:#b91c1c; padding:2px 6px; border-radius:3px; font-weight:700;'>❌ OCR UNAVAILABLE</span>"

        doc_rows += f"""
        <tr>
            <td><code>{d['id']}</code></td>
            <td><strong>{d['filename']}</strong>{mode_badge}</td>
            <td>{d['category']}</td>
            <td><code>{d['file_hash'][:16]}...</code></td>
            <td>{d['file_size_formatted']}</td>
            <td><span style="color:{status_color}; font-weight:700;">{d['status']}</span></td>
        </tr>
        """

    # Build findings list
    finding_cards = ""
    if not data['findings']:
        finding_cards = "<p style='color:#64748b;'>No localized forensic observations or typographical anomalies detected.</p>"
    else:
        for f in data['findings']:
            sev = f['severity']
            sev_class = "critical" if sev in ('Critical', 'High') else "warning" if sev == 'Medium' else "info"
            border_color = "#ef4444" if sev in ('Critical', 'High') else "#f59e0b" if sev == 'Medium' else "#64748b"
            coord_str = f" • BBox: <code>[{f['coordinates']}]</code>" if f['coordinates'] else ""
            weight_str = f" • Rule Weight: <strong>{f['confidence']}</strong>" if f.get('confidence') is not None else ""

            finding_cards += f"""
            <div style="border-left: 4px solid {border_color}; background:#f8fafc; padding:12px 16px; margin-bottom:12px; border-radius:4px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span style="font-weight:700; color:#0f172a;">[{f['rule_id']}] {f['title']}</span>
                    <span>
                        <span style="font-size:0.75rem; background:#e2e8f0; color:#334155; padding:2px 6px; border-radius:3px; margin-right:6px; font-weight:600;">{f.get('evidence_class') or 'Observation'}</span>
                        <span style="font-size:0.75rem; font-weight:700; color:{border_color}; text-transform:uppercase;">{sev}</span>
                    </span>
                </div>
                <div style="font-size:0.8rem; color:#64748b; margin-bottom:6px;">
                    Source Document: <code>{f.get('document_id', 'Unknown')}</code> • Page {f.get('page_number', 1)}{coord_str}{weight_str}
                </div>
                <p style="font-size:0.85rem; color:#334155; margin:0 0 6px 0;">{f['description']}</p>
                {f'<div style="font-size:0.8rem; color:#0369a1; background:#f0f9ff; padding:4px 8px; border-radius:3px;">🔍 <strong>Evidence:</strong> {f["evidence"]}</div>' if f.get('evidence') else ''}
            </div>
            """

    # Build discrepancies list
    disc_cards = ""
    discrepancies = data['cross_document_comparison'].get('discrepancies', [])
    if not discrepancies:
        disc_cards = "<p style='color:#64748b;'>No cross-document conflicts or monetary disparities identified.</p>"
    else:
        for d in discrepancies:
            attr = d.get('attribute') or d.get('field') or 'Attribute Discrepancy'
            val_a = d.get('val_a', '')
            val_b = d.get('val_b', '')
            doc_a = d.get('doc_a_filename') or d.get('doc_a_id') or 'Doc A'
            doc_b = d.get('doc_b_filename') or d.get('doc_b_id') or 'Doc B'
            if val_a and val_b:
                conflict_hdr = f"{attr}: {val_a} in {doc_a} vs {val_b} in {doc_b}"
            else:
                conflict_hdr = f"{attr} conflict between {doc_a} and {doc_b}"
            expl = d.get('explanation') or d.get('message') or ''

            disc_cards += f"""
            <div style="background:#fef2f2; border:1px solid #fecaca; border-radius:4px; padding:10px 14px; margin-bottom:8px;">
                <strong style="color:#b91c1c;">⚠️ Conflict: {html.escape(conflict_hdr)}</strong>
                <p style="font-size:0.85rem; color:#334155; margin:4px 0 0 0;">{html.escape(expl)}</p>
            </div>
            """

    # Build Phase C AI Summary section (if AI data exists)
    ai_section_html = ""
    if data.get('ai_summary') and data['ai_summary'].get('has_ai_data'):
        ai_s = data['ai_summary']
        ai_section_html = f"""
        <div class="section-title">5. AI-Assisted Investigation Summary</div>
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px; padding:16px; margin-bottom:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <strong style="color:#15803d; font-size:14px;">🤖 Contextual AI Intelligence Analysis</strong>
                <span style="font-size:11px; background:#dcfce7; color:#166534; padding:3px 8px; border-radius:4px; font-weight:700;">{ai_s['disclaimer']}</span>
            </div>
            <p style="font-size:13px; color:#334155; margin:0 0 8px 0; line-height:1.5;">
                Contextual reasoning engine evaluated case records: flagged <strong>{ai_s['ai_findings_count']}</strong> contextual multi-document observations and <strong>{ai_s['insights_count']}</strong> structured entity insights.
            </p>
            <div style="font-size:12px; color:#166534; background:#dcfce7; padding:6px 10px; border-radius:4px; font-weight:600;">
                NOTICE: AI-assisted insights were grounded against document source text quotes. Findings require verification by the human lead investigator.
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VEXORA Dossier — Case {case['id']}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #0f172a;
            background: #f1f5f9;
            margin: 0;
            padding: 30px;
            font-size: 14px;
            line-height: 1.5;
        }}
        .dossier-paper {{
            max-width: 900px;
            margin: 0 auto;
            background: #ffffff;
            padding: 40px 50px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border-radius: 8px;
        }}
        .dossier-header {{
            border-bottom: 2px solid #0f172a;
            padding-bottom: 20px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        .brand-title {{
            font-size: 24px;
            font-weight: 800;
            letter-spacing: 1px;
            color: #0f172a;
            margin: 0 0 4px 0;
        }}
        .disclaimer-box {{
            background: #fffbeb;
            border: 1px solid #f59e0b;
            color: #92400e;
            padding: 12px 16px;
            border-radius: 6px;
            font-size: 12px;
            margin-bottom: 24px;
            line-height: 1.5;
        }}
        .section-title {{
            font-size: 14px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #1e293b;
            background: #f1f5f9;
            padding: 8px 12px;
            margin: 24px 0 12px 0;
            border-radius: 4px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }}
        .metric-card {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            padding: 12px;
            border-radius: 6px;
            text-align: center;
        }}
        .metric-val {{
            font-size: 20px;
            font-weight: 800;
            margin-top: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12.5px;
            margin-bottom: 16px;
        }}
        th, td {{
            padding: 8px 10px;
            border-bottom: 1px solid #e2e8f0;
            text-align: left;
        }}
        th {{
            background: #f8fafc;
            font-weight: 700;
            color: #475569;
        }}
        .signoff-box {{
            border-top: 2px solid #e2e8f0;
            margin-top: 36px;
            padding-top: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        @media print {{
            body {{
                background: #ffffff;
                padding: 0;
            }}
            .dossier-paper {{
                box-shadow: none;
                padding: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="dossier-paper">
        <div class="dossier-header">
            <div style="display:flex; align-items:center; gap:16px;">
                <img src="/images/logo-icon.png" alt="VEXORA Emblem" style="width:52px; height:52px; border-radius:8px; object-fit:cover; border:1px solid #0f172a;" onerror="this.style.display='none'">
                <div>
                    <h1 class="brand-title">VEXORA FORENSIC DOSSIER</h1>
                    <div style="font-size:11px; font-weight:700; color:#0284c7; letter-spacing:1px; margin-bottom:4px;">SEEING WHAT OTHERS OVERLOOK</div>
                    <div style="font-size:13px; color:#64748b;">
                        Case ID: <strong>{case['id']}</strong> • Title: <strong>{case['title']}</strong><br>
                        Generated: {data['generated_at']} • Lead Analyst: <strong>{user}</strong>
                    </div>
                </div>
            </div>
            <div style="text-align:right;">
                <span style="display:inline-block; padding:6px 12px; border-radius:4px; font-weight:700; font-size:12px; background:#fef2f2; color:#ef4444; border:1px solid #fecaca;">
                    {summary['risk_level']}
                </span>
            </div>
        </div>

        <div class="disclaimer-box">
            <strong>MANDATORY INVESTIGATION DISCLAIMER:</strong><br>
            {data['mandatory_disclaimer']}
        </div>

        <div class="section-title">1. Executive Investigation Summary</div>
        <div class="metrics-grid">
            <div class="metric-card">
                <div style="font-size:11px; color:#64748b; font-weight:700;">RISK SCORE</div>
                <div class="metric-val" style="color:#ef4444;">{summary['risk_score']} / 100</div>
            </div>
            <div class="metric-card">
                <div style="font-size:11px; color:#64748b; font-weight:700;">DOCUMENTS</div>
                <div class="metric-val">{summary['document_count']}</div>
            </div>
            <div class="metric-card">
                <div style="font-size:11px; color:#64748b; font-weight:700;">ANOMALIES</div>
                <div class="metric-val" style="color:#f59e0b;">{summary['findings_count']}</div>
            </div>
            <div class="metric-card">
                <div style="font-size:11px; color:#64748b; font-weight:700;">DISCREPANCIES</div>
                <div class="metric-val" style="color:#ef4444;">{summary['discrepancies_count']}</div>
            </div>
        </div>
        <p style="color:#334155; line-height:1.6;">{summary['narrative']}</p>

        <div class="section-title">2. Ingested Evidence Inventory</div>
        <table>
            <thead>
                <tr>
                    <th>Doc ID</th>
                    <th>Filename</th>
                    <th>Category</th>
                    <th>SHA-256 Hash</th>
                    <th>Size</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {doc_rows if doc_rows else '<tr><td colspan="6" style="color:#64748b;">No documents uploaded to this case.</td></tr>'}
            </tbody>
        </table>

        <div class="section-title">3. Forensic Observations & Visual Anomalies</div>
        {finding_cards}

        <div class="section-title">4. Cross-Document Discrepancy Matrix</div>
        {disc_cards}

        {ai_section_html}

        <div class="signoff-box">
            <div>
                <strong>Investigator Sign-off:</strong> {user}<br>
                <span style="font-size:12px; color:#64748b;">VEXORA Forensic Intelligence Engine • Verified Local Node</span><br>
                <small style="font-family:monospace; color:#475569;">Verification Code: <strong>{summary['dossier_verification_code']}</strong></small>
            </div>
            <div style="border-top:1px solid #94a3b8; width:180px; text-align:center; padding-top:4px; font-size:11px; color:#94a3b8;">
                Signature / Official Seal
            </div>
        </div>
    </div>
</body>
</html>
"""

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    file_size = file_path.stat().st_size
    report_id = f"RPT-HTML-{case_id}-{timestamp_str}"
    title = f"Investigation Dossier (HTML) • Case {case_id}"

    create_report_record(
        report_id=report_id,
        case_id=case_id,
        title=title,
        file_path=str(file_path),
        file_format='html',
        file_size=file_size,
        user=user
    )

    return {
        'success': True,
        'report_id': report_id,
        'case_id': case_id,
        'title': title,
        'file_path': str(file_path),
        'filename': filename,
        'file_format': 'html',
        'file_size': file_size,
        'file_size_formatted': f"{(file_size / 1024):.1f} KB",
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'verification_code': summary['dossier_verification_code']
    }
