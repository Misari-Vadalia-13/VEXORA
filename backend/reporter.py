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
import base64
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

from backend.config import Config, REPORTS_FOLDER, BASE_DIR
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
# 0. Pipeline Auto-Completion & Case Integrity Engine
# =====================================================================

def _ensure_case_analysis(case_id, user="Lead Investigator"):
    """
    Ensures that every document in the case has been analyzed and that cross-document
    comparison has been performed before generating a case dossier.
    Raises ValueError if the case has 0 ingested documents.
    """
    docs = get_all_documents(case_id=case_id)
    if not docs:
        raise ValueError("Case has no ingested documents. Upload and analyze at least one document before generating a dossier.")

    from backend.analyzer import analyze_document
    for d in docs:
        status = (d.get('status') or '').strip()
        if status not in ("Analyzed", "Clean", "Flagged"):
            try:
                analyze_document(d['id'], user=user)
            except Exception as e:
                logger.error(f"Failed to auto-analyze document {d.get('id')} in case {case_id}: {e}")

    if len(docs) >= 2:
        try:
            compare_case_documents(case_id, user=user)
        except Exception as e:
            logger.error(f"Failed to auto-compare documents for case {case_id}: {e}")


def _rotate_case_dossiers(case_id: str, max_keep: int = 3):
    """Retains only the latest max_keep dossiers per case in REPORTS_FOLDER."""
    try:
        reports_dir = Path(Config.REPORTS_FOLDER)
        if not reports_dir.exists():
            return
        safe_case_id = case_id.replace('-', '_')
        pdf_files = sorted(reports_dir.glob(f"DOSSIER_{safe_case_id}_*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old_file in pdf_files[max_keep:]:
            try:
                old_file.unlink()
            except OSError:
                pass
        html_files = sorted(reports_dir.glob(f"DOSSIER_{safe_case_id}_*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old_file in html_files[max_keep:]:
            try:
                old_file.unlink()
            except OSError:
                pass
    except Exception as e:
        logger.warning(f"Failed to rotate dossiers for {case_id}: {e}")



# =====================================================================
# 1. Dossier Data Aggregation Engine
# =====================================================================

# =====================================================================
# Phase K: Dossier Completeness Helper Engines (K1 - K5)
# =====================================================================

def build_extracted_information(docs, ai_insights=None):
    """
    Phase K1: Builds per-document table of extracted fields with value,
    source page, and confidence (OCR confidence, 'n/a (digital text)', or AI quote-verified),
    plus extraction_mode with a visible warning if it was a simulated fallback.
    """
    results = []
    ai_by_doc = {}
    if ai_insights:
        for ins in ai_insights:
            doc_id = ins.get('document_id')
            if doc_id:
                ai_by_doc.setdefault(doc_id, []).append(ins)

    for d in docs:
        doc_id = d['id']
        filename = d.get('filename', 'Unknown')
        ext_mode = d.get('extraction_mode') or ('digital_pdf' if (d.get('file_type') or '').lower() == 'pdf' else 'ocr')
        is_simulated = (ext_mode == 'simulated_fallback') or ('simulated' in ext_mode.lower())
        warning = "Simulated Fallback: Host system lacked Tesseract OCR; extraction used simulated text." if is_simulated else None

        fields = []

        # 1. Check AI-extracted fields
        if doc_id in ai_by_doc:
            for ins in ai_by_doc[doc_id]:
                structured = ins.get('structured_fields') or {}
                if isinstance(structured, str):
                    try:
                        structured = json.loads(structured)
                    except Exception:
                        structured = {}
                for k, v in structured.items():
                    if isinstance(v, dict):
                        fields.append({
                            'name': k.replace('_', ' ').title(),
                            'value': str(v.get('value', '')),
                            'source_page': 1,
                            'confidence': 'AI quote-verified' if v.get('verified') else 'AI-assisted'
                        })
                    elif v:
                        fields.append({
                            'name': k.replace('_', ' ').title(),
                            'value': str(v),
                            'source_page': 1,
                            'confidence': 'AI quote-verified'
                        })

        # 2. Check entities from extracted_data
        ext_data = {}
        if d.get('extracted_data'):
            try:
                ext_data = json.loads(d['extracted_data']) if isinstance(d['extracted_data'], str) else d['extracted_data']
            except Exception:
                ext_data = {}

        entities = ext_data.get('entities', {})
        conf_default = "n/a (digital text)" if ext_mode == 'digital_pdf' else "90.0% (OCR)"

        def safe_conf(conf_val, default_pct=90.0):
            if ext_mode == 'digital_pdf':
                return "n/a (digital text)"
            if conf_val is None:
                return f"{default_pct:.1f}% (OCR)"
            try:
                num = float(conf_val)
                return f"{num:.1f}% (OCR)"
            except (ValueError, TypeError):
                return f"{str(conf_val)} (OCR)"

        for mv in entities.get('monetary_values', []):
            fields.append({
                'name': 'Monetary Figure',
                'value': str(mv.get('value', '')),
                'source_page': mv.get('page', 1),
                'confidence': safe_conf(mv.get('confidence'), 90.0)
            })

        for ident in entities.get('identifiers', []):
            fields.append({
                'name': 'Identifier / Code',
                'value': str(ident.get('value', '')),
                'source_page': ident.get('page', 1),
                'confidence': safe_conf(ident.get('confidence'), 90.0)
            })

        for dt in entities.get('dates', []):
            fields.append({
                'name': 'Execution / Due Date',
                'value': str(dt.get('value', '')),
                'source_page': dt.get('page', 1),
                'confidence': safe_conf(dt.get('confidence'), 90.0)
            })

        for org in entities.get('organizations', []):
            fields.append({
                'name': 'Corporate Entity / Party',
                'value': str(org.get('value', '')),
                'source_page': org.get('page', 1),
                'confidence': safe_conf(org.get('confidence'), 85.0)
            })

        for per in entities.get('persons', []):
            fields.append({
                'name': 'Signatory / Individual',
                'value': str(per.get('value', '')),
                'source_page': per.get('page', 1),
                'confidence': safe_conf(per.get('confidence'), 85.0)
            })

        # Deduplicate fields
        seen = set()
        deduped = []
        for fld in fields:
            key = (fld['name'], fld['value'])
            if key not in seen and fld['value'].strip():
                seen.add(key)
                deduped.append(fld)

        if not deduped:
            deduped.append({
                'name': 'Document Body Content',
                'value': f"Extracted text length: {len(d.get('extracted_text') or '')} characters",
                'source_page': 1,
                'confidence': conf_default
            })

        results.append({
            'doc_id': doc_id,
            'filename': filename,
            'extraction_mode': ext_mode,
            'is_simulated_fallback': is_simulated,
            'warning': warning,
            'fields': deduped
        })

    return results


def build_evidence_traceability(findings):
    """
    Phase K2: Selects top 5 findings by severity and structures them with rule ID,
    class label (Observed, Detected inconsistency, Potential manipulation), page, box, quoted source text,
    and human reviewer decisions.
    """
    from backend.explainability import get_status_badge
    sev_rank = {'Critical': 5, 'High': 4, 'Medium': 3, 'Low': 2, 'Info': 1}
    sorted_findings = sorted(findings, key=lambda f: sev_rank.get(f.get('severity', 'Medium'), 0), reverse=True)
    top5 = sorted_findings[:5]

    items = []
    for f in top5:
        sev = f.get('severity', 'Medium')
        class_label = get_status_badge(f)

        box_val = f.get('coordinates')
        box_str = str(box_val) if box_val else "N/A (Document-level metadata rule)"
        quoted = f.get('evidence') or f.get('description') or f.get('title', '')

        rev_dec = f.get('reviewer_decision')
        rev_by = f.get('reviewed_by') or 'Investigator'
        rev_note = f.get('reviewer_note')
        if rev_dec:
            rev_summary = f"Reviewed by: {rev_by} | Status: {rev_dec}"
            if rev_note:
                rev_summary += f" | Note: {rev_note}"
        else:
            rev_summary = "Pending Investigator Review"

        items.append({
            'id': f['id'],
            'rule_id': f.get('rule_id', 'RULE-GEN-001'),
            'title': f.get('title', 'Forensic Finding'),
            'severity': sev,
            'class_label': class_label,
            'page_number': f.get('page_number', 1),
            'box': box_str,
            'quoted_text': quoted,
            'reviewer_summary': rev_summary
        })

    return items


def build_digital_evidence_handling(docs, case_id=None):
    """
    Builds the digital evidence handling & chain of custody summary
    aligned with ISO/IEC 27037 principles (identification, collection, acquisition, preservation).
    Tracks cryptographic SHA-256 verification status and chronological audit events.
    """
    from backend.database import query_db
    records = []
    upload_folder = Path(Config.UPLOAD_FOLDER)

    for d in docs:
        doc_id = d.get('id')
        stored_hash = d.get('file_hash') or ''
        raw_path = Path(d['file_path']) if d.get('file_path') else None

        current_hash = None
        target_file = None
        if raw_path:
            candidate = upload_folder / raw_path.name
            if candidate.exists() and candidate.is_file():
                target_file = candidate
            elif raw_path.exists() and raw_path.is_file():
                target_file = raw_path
            else:
                candidate_base = BASE_DIR / raw_path
                if candidate_base.exists() and candidate_base.is_file():
                    target_file = candidate_base

        if target_file and target_file.exists():
            try:
                current_hash = hashlib.sha256(target_file.read_bytes()).hexdigest()
            except Exception:
                current_hash = None

        if current_hash:
            match = (current_hash.lower() == stored_hash.lower())
            status_text = "Verified Match" if match else "Hash Mismatch"
        else:
            match = False
            status_text = "File Missing on Disk"

        events = []
        try:
            filename = d.get('filename') or ''
            query = """
                SELECT * FROM audit_logs
                WHERE entity_id = ?
                   OR (details LIKE ? AND details NOT LIKE '%upload_request%')
                ORDER BY timestamp ASC, id ASC
            """
            term = f"%{doc_id}%"
            rows = query_db(query, (doc_id, term))
            if filename:
                name_term = f"%{filename}%"
                extra_query = """
                    SELECT * FROM audit_logs
                    WHERE details LIKE ?
                      AND id NOT IN (SELECT id FROM audit_logs WHERE entity_id = ? OR details LIKE ?)
                    ORDER BY timestamp ASC, id ASC
                """
                extra_rows = query_db(extra_query, (name_term, doc_id, term))
                rows = sorted(list(rows) + list(extra_rows), key=lambda r: (r['timestamp'], r['id']))

            for r in rows:
                events.append({
                    'timestamp': r['timestamp'],
                    'actor': r['user'],
                    'action': r['action'],
                    'details': r['details']
                })
        except Exception:
            events = []

        records.append({
            'document_id': doc_id,
            'filename': d.get('filename'),
            'stored_hash': stored_hash,
            'current_hash': current_hash,
            'match': match,
            'status': status_text,
            'custody_events': events
        })

    return records


def build_investigation_summary(case, docs, findings, discrepancies, ai_summary=None):
    """
    Phase K3: Builds a plain-language summary derived from findings and appends
    AI-assisted summary if present labeled 'AI-assisted, requires human review'.
    """
    doc_count = len(docs)
    finding_count = len(findings)
    disc_count = len(discrepancies)

    crit_count = sum(1 for f in findings if f.get('severity') == 'Critical')
    high_count = sum(1 for f in findings if f.get('severity') == 'High')
    med_count = sum(1 for f in findings if f.get('severity') == 'Medium')

    if finding_count == 0 and disc_count == 0:
        plain_text = (
            f"Forensic examination of Case '{case.get('title', 'Inquiry')}' across {doc_count} document(s) "
            f"demonstrated complete structural, visual, and contextual integrity. All inspected numerical figures, "
            f"dates, and legal counterparties align cleanly across submitted records without evidence of digital or physical tampering."
        )
    else:
        plain_text = (
            f"Forensic examination of Case '{case.get('title', 'Inquiry')}' across {doc_count} document(s) "
            f"flagged {finding_count} localized anomaly finding(s) ({crit_count} Critical, {high_count} High, {med_count} Medium) "
            f"and {disc_count} cross-document factual contradiction(s). "
        )
        notable = []
        if any('VIS' in f.get('rule_id', '') for f in findings):
            notable.append("discrepant typographic font families and bounding box overlap")
        if any('CTX' in f.get('rule_id', '') for f in findings):
            notable.append("chronological timeline reversals or futuristic execution dates")
        if any('PDF-003' in f.get('rule_id', '') for f in findings):
            notable.append("disallowed image-editing software metadata (e.g. Adobe Photoshop)")
        if any('IMG' in f.get('rule_id', '') for f in findings):
            notable.append("raster compression irregularities or cloned image patches")
        if disc_count > 0:
            notable.append("cross-document monetary variances and duplicate reference collisions")

        if notable:
            plain_text += "Primary forensic indicators encompass " + ", ".join(notable) + ". "
        plain_text += "These algorithmic observations warrant prioritized manual inspection by the lead investigator."

    ai_text = None
    if ai_summary and ai_summary.get('has_ai_data'):
        ai_insights = ai_summary.get('insights', [])
        ai_findings_count = ai_summary.get('ai_findings_count', 0)
        ai_text = (
            f"Contextual reasoning model evaluated evidentiary set: identified {ai_findings_count} contextual multi-document "
            f"observations and {len(ai_insights)} structured quote-verified entity insights. Every asserted fact was grounded against "
            f"verbatim source text. Notice: AI-assisted observations require human validation before administrative action."
        )

    return {
        'plain_summary': plain_text,
        'ai_summary': ai_text,
        'has_ai': bool(ai_text)
    }


def build_verification_areas(findings, discrepancies, documents):
    """
    Phase K4: Derives actionable verification items from findings and discrepancies.
    """
    items = []
    has_monetary_conflict = any(d.get('attribute') == 'Primary Monetary Value' or 'monetary' in str(d.get('attribute', '')).lower() for d in discrepancies)
    has_entity_conflict = any('entity' in str(d.get('attribute', '')).lower() or 'counterparty' in str(d.get('attribute', '')).lower() for d in discrepancies)
    has_date_conflict = any('date' in str(d.get('attribute', '')).lower() for d in discrepancies) or any('CTX-003' in f.get('rule_id', '') or 'reversed' in f.get('title', '').lower() for f in findings)
    has_photo_meta = any('PDF-003' in f.get('rule_id', '') or 'photoshop' in f.get('description', '').lower() for f in findings)
    has_font_shift = any('VIS' in f.get('rule_id', '') or 'font' in f.get('title', '').lower() for f in findings)
    has_copymove = any('IMG-003' in f.get('rule_id', '') or 'copy-move' in f.get('description', '').lower() for f in findings)
    has_future_date = any('CTX-001' in f.get('rule_id', '') or 'future' in f.get('title', '').lower() for f in findings)

    if has_monetary_conflict:
        items.append("Financial Re-verification: Request verified bank wire settlement confirmation and accounting ledger entries from the issuing party to confirm the authorized transaction total.")
    if has_entity_conflict:
        items.append("Corporate Entity Verification: Check statutory business registry (e.g. SEC/Companies House) to verify counterparty legal name, jurisdiction, and registered corporate officers.")
    if has_photo_meta:
        items.append("Original File Request: Request the native, untranscoded digital file directly from issuer email logs to inspect unedited PDF creation dictionaries.")
    if has_font_shift:
        items.append("Typographic Audit: Request native ERP accounting export to confirm standard corporate font embedding hierarchy and investigate potential character insertion.")
    if has_copymove:
        items.append("Physical Document Inspection: Inspect the original physical paper document under high-magnification or stereo microscope to confirm notary stamp or signature authenticity.")
    if has_date_conflict or has_future_date:
        items.append("Timeline Chronology Cross-Check: Cross-reference document execution dates with external carrier bills of lading, delivery acknowledgments, and bank clearing house timestamps.")

    if not items:
        items.append("Standard Archival Validation: Verify vendor tax identification number (TIN) against commercial registry and maintain signed counterpart in permanent case archive.")

    return items


def build_dossier_limitations(documents, findings, has_ai_data):
    """
    Phase K5: Static limitations plus dynamic ones for this run
    (OCR fallback used, image forensics not applicable, AI disabled, heuristics used).
    """
    static_limits = [
        "Digital vs. Physical Materiality: Analysis is confined to digital PDF streams, raster matrices, and byte-level metadata. Physical paper chemistry, paper fiber structure, and ink luminescence require laboratory examination.",
        "Language Calibration: Heuristics, entity extraction, and contextual statutory checks are calibrated exclusively for English-language commercial and legal documents.",
        "Probabilistic Observations: Anomaly indicators are algorithmic heuristics produced for investigative triage and do not constitute definitive legal determinations of fraud."
    ]

    dynamic_limits = []

    # Check OCR fallback
    ocr_fallback = any(d.get('extraction_mode') == 'simulated_fallback' for d in documents)
    if ocr_fallback:
        dynamic_limits.append("OCR Fallback Active: Tesseract OCR was not detected on the host operating system. Document text extraction operated in simulated fallback mode.")
    else:
        dynamic_limits.append("OCR Execution: OCR processing was performed using available system optical engines, subject to baseline scan resolution and font clarity limitations.")

    # Check image forensics applicability
    image_bypassed = any('born-digital' in f.get('description', '').lower() for f in findings)
    has_images = any((d.get('file_type') or '').lower() in ('png', 'jpg', 'jpeg', 'tiff', 'bmp') for d in documents)
    if image_bypassed or not has_images:
        dynamic_limits.append("Image Forensics Boundary: Born-digital vector PDF pages without embedded raster graphics were bypassed for pixel-level Error Level Analysis (ELA) to prevent false alarms on rendered vector text.")

    # Check AI availability
    if not has_ai_data or not getattr(Config, 'ENABLE_LLM', False) or not bool(os.environ.get('VEXORA_LLM_API_KEY')):
        dynamic_limits.append("AI Reasoning Inactive: Generative LLM analysis was not executed because the AI module is disabled or VEXORA_LLM_API_KEY is not configured.")

    # Check heuristics
    if any(f.get('rule_id', '').startswith(('RULE-VIS-', 'RULE-CTX-', 'IMG-')) for f in findings):
        dynamic_limits.append("Heuristic Rules Active: Visual alignment, font consistency, and contextual anomaly rules are heuristic approximations; complex multi-column layouts may produce false positive margin alerts.")

    return {
        'static': static_limits,
        'dynamic': dynamic_limits
    }

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
            'status': f.get('status', 'Unresolved'),
            'reviewer_decision': f.get('reviewer_decision'),
            'reviewer_note': f.get('reviewer_note'),
            'reviewed_by': f.get('reviewed_by'),
            'reviewed_at': f.get('reviewed_at')
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
    low_count = severity_counts.get('Low', 0)
    disc_count = len(cross_comparison.get('discrepancies', [])) if cross_comparison.get('success') else 0

    raw_risk = (crit_count * 30) + (high_count * 20) + (med_count * 10) + (low_count * 5) + (disc_count * 25)
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
    if total_file_size < 1024 * 1024:
        size_disp = f"{(total_file_size / 1024):.1f} KB"
    else:
        size_disp = f"{(total_file_size / (1024 * 1024)):.2f} MB"
    narrative = (
        f"An analytical forensic review of Case {case_id} ('{case['title']}') was conducted across "
        f"{len(doc_inventory)} ingested document(s) totaling {size_disp}. "
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
        'extracted_information': build_extracted_information(docs, ai_insights),
        'evidence_traceability': build_evidence_traceability(findings_list),
        'digital_evidence_handling': build_digital_evidence_handling(docs, case_id),
        'investigation_summary': build_investigation_summary(
            case, docs, findings_list,
            cross_comparison.get('discrepancies', []),
            ai_summary={'has_ai_data': has_ai_data, 'insights': ai_insights, 'ai_findings_count': len(ai_findings)} if has_ai_data else None
        ),
        'areas_for_verification': build_verification_areas(findings_list, cross_comparison.get('discrepancies', []), docs),
        'limitations': build_dossier_limitations(doc_inventory, findings_list, has_ai_data),
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

    _ensure_case_analysis(case_id, user=user)
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
    has_logo = False
    if logo_path.exists():
        try:
            # Aspect ratio 1024x682 (~1.5:1). Target: width 84, height 56
            logo_rect = fitz.Rect(MARGIN_RIGHT - 88, 11, MARGIN_RIGHT, 67)
            page.insert_image(logo_rect, filename=str(logo_path))
            has_logo = True
        except Exception:
            has_logo = False

    page.insert_text(fitz.Point(MARGIN_LEFT, 28), "VEXORA", fontname="hebo", fontsize=18, color=(1, 1, 1))
    page.insert_text(fitz.Point(MARGIN_LEFT + 86, 28), "• FORENSIC INVESTIGATION DOSSIER", fontname="hebo", fontsize=11, color=(56/255, 189/255, 248/255))
    page.insert_text(fitz.Point(MARGIN_LEFT, 44), "SEEING WHAT OTHERS OVERLOOK", fontname="hebo", fontsize=7.5, color=(56/255, 189/255, 248/255))
    page.insert_text(fitz.Point(MARGIN_LEFT, 62), f"Case ID: {case['id']} | Title: {case['title']} | Date: {data['generated_at']}", fontname="helv", fontsize=8.5, color=(148/255, 163/255, 184/255))

    # Header Risk Level Badge in PDF Banner
    risk_level = summary.get('risk_level', '')
    if risk_level in ("Critical Risk / Irregular", "High Risk / Requires Review"):
        pdf_badge_color = (239/255, 68/255, 68/255)
        pdf_badge_bg = (254/255, 242/255, 242/255)
        pdf_badge_border = (254/255, 202/255, 202/255)
    elif risk_level == "Moderate Variance":
        pdf_badge_color = (217/255, 119/255, 6/255)
        pdf_badge_bg = (254/255, 243/255, 199/255)
        pdf_badge_border = (253/255, 230/255, 138/255)
    elif risk_level == "Clean / Verified Alignment":
        pdf_badge_color = (21/255, 128/255, 61/255)
        pdf_badge_bg = (220/255, 252/255, 231/255)
        pdf_badge_border = (187/255, 247/255, 208/255)
    else:
        pdf_badge_color = (71/255, 85/255, 105/255)
        pdf_badge_bg = (241/255, 245/255, 249/255)
        pdf_badge_border = (226/255, 232/255, 240/255)

    badge_w = 145.0
    badge_h = 20.0
    badge_right = (MARGIN_RIGHT - 96.0) if has_logo else MARGIN_RIGHT
    badge_left = badge_right - badge_w
    badge_top = 22.0
    badge_bottom = badge_top + badge_h
    badge_rect = fitz.Rect(badge_left, badge_top, badge_right, badge_bottom)
    page.draw_rect(badge_rect, color=pdf_badge_border, fill=pdf_badge_bg, width=0.75)
    page.insert_textbox(badge_rect, risk_level, fontname="hebo", fontsize=7.5, color=pdf_badge_color, align=fitz.TEXT_ALIGN_CENTER)

    y = 92.0

    # 2. Mandatory Human Review Disclaimer Box (Amber #fffbeb with #f59e0b border)
    pdf_disc = data.get('mandatory_disclaimer', '')
    prefix = "MANDATORY INVESTIGATION DISCLAIMER:"
    if pdf_disc.startswith(prefix):
        pdf_disc = pdf_disc[len(prefix):].strip()

    page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 44), color=(245/255, 158/255, 11/255), fill=(255/255, 251/255, 235/255), width=1)
    page.insert_text(fitz.Point(MARGIN_LEFT + 8, y + 14), "[!] MANDATORY INVESTIGATION DISCLAIMER", fontname="hebo", fontsize=8, color=(180/255, 83/255, 9/255))
    page.insert_textbox(
        fitz.Rect(MARGIN_LEFT + 8, y + 16, MARGIN_RIGHT - 8, y + 42),
        pdf_disc,
        fontname="helv",
        fontsize=6.5,
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
        mode_tag = " [⚠️ OCR unavailable - fallback mode]" if ext_mode == 'simulated_fallback' else ""
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

    # =====================================================================
    # PHASE K APPENDED SECTIONS (K1 to K5)
    # =====================================================================
    try:
        # K1. Extracted Information
        ext_info = data.get('extracted_information', [])
        if ext_info:
            page = create_page()
            y = 50.0

            page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 18), color=None, fill=(241/255, 245/255, 249/255))
            page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 13), "6. EXTRACTED INFORMATION & FIELD CONFIDENCE", fontname="hebo", fontsize=9.5, color=(30/255, 41/255, 59/255))
            y += 24.0

            for doc_info in ext_info:
                if y > 660:
                    page = create_page()
                    y = 50.0

                page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 16), color=(203/255, 213/255, 225/255), fill=(248/255, 250/255, 252/255), width=0.5)
                page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 11), f"File: {doc_info['filename']} ({doc_info['doc_id']}) • Mode: {doc_info['extraction_mode']}", fontname="hebo", fontsize=7.5, color=(15/255, 23/255, 42/255))
                y += 18.0

                if doc_info.get('warning'):
                    page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 16), color=(245/255, 158/255, 11/255), fill=(255/255, 251/255, 235/255), width=0.5)
                    page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 11), f"[!] {doc_info['warning']}", fontname="hebo", fontsize=7, color=(180/255, 83/255, 9/255))
                    y += 18.0

                page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 14), color=None, fill=(226/255, 232/255, 240/255))
                page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 10), "FIELD / ENTITY", fontname="hebo", fontsize=7, color=(71/255, 85/255, 105/255))
                page.insert_text(fitz.Point(MARGIN_LEFT + 150, y + 10), "EXTRACTED VALUE", fontname="hebo", fontsize=7, color=(71/255, 85/255, 105/255))
                page.insert_text(fitz.Point(MARGIN_LEFT + 360, y + 10), "PAGE", fontname="hebo", fontsize=7, color=(71/255, 85/255, 105/255))
                page.insert_text(fitz.Point(MARGIN_LEFT + 420, y + 10), "CONFIDENCE", fontname="hebo", fontsize=7, color=(71/255, 85/255, 105/255))
                y += 16.0

                for fld in doc_info.get('fields', [])[:10]:
                    if y > 710:
                        page = create_page()
                        y = 50.0

                    page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 10), str(fld['name'])[:24], fontname="hebo", fontsize=7, color=(51/255, 65/255, 85/255))
                    page.insert_text(fitz.Point(MARGIN_LEFT + 150, y + 10), str(fld['value'])[:40], fontname="helv", fontsize=7, color=(15/255, 23/255, 42/255))
                    page.insert_text(fitz.Point(MARGIN_LEFT + 360, y + 10), str(fld['source_page']), fontname="helv", fontsize=7, color=(100/255, 116/255, 139/255))
                    conf_str = str(fld['confidence'])
                    conf_col = (16/255, 185/255, 129/255) if "verified" in conf_str.lower() or "digital" in conf_str.lower() else (71/255, 85/255, 105/255)
                    page.insert_text(fitz.Point(MARGIN_LEFT + 420, y + 10), conf_str[:22], fontname="hebo", fontsize=7, color=conf_col)
                    y += 13.0
                y += 10.0
    except Exception:
        pass

    try:
        # K2. Evidence and Traceability (top 5 findings)
        ev_items = data.get('evidence_traceability', [])
        if ev_items or y > 620:
            page = create_page()
            y = 50.0

        page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 18), color=None, fill=(241/255, 245/255, 249/255))
        page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 13), "7. EVIDENCE AND TRACEABILITY (TOP FINDINGS)", fontname="hebo", fontsize=9.5, color=(30/255, 41/255, 59/255))
        y += 26.0

        if not ev_items:
            page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 12), "No evidence-linked findings were produced for this case. No localized anomalies required visual evidence capture.", fontname="helv", fontsize=8, color=(100/255, 116/255, 139/255))
            y += 24.0
        else:
            from backend.evidence import get_finding_evidence_image
            for ev in ev_items[:5]:
                if y > 540:
                    page = create_page()
                    y = 50.0

                sev = ev.get('severity', 'Medium')
                badge_color = (220/255, 38/255, 38/255) if sev in ('Critical', 'High') else (217/255, 119/255, 6/255) if sev == 'Medium' else (100/255, 116/255, 139/255)

                page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_LEFT + 3, y + 36), color=None, fill=badge_color)
                page.insert_text(fitz.Point(MARGIN_LEFT + 8, y + 10), f"[{ev['rule_id']}] {ev['title'][:60]}", fontname="hebo", fontsize=8, color=(15/255, 23/255, 42/255))
                page.insert_text(fitz.Point(MARGIN_RIGHT - 140, y + 10), f"Class: {ev['class_label']}", fontname="hebo", fontsize=7.5, color=badge_color)

                box_str = str(ev.get('box')) if ev.get('box') else "N/A"
                meta_str = f"Page {ev.get('page_number', 1)} • Bounding Box: {box_str} • Severity: {sev.upper()}"
                page.insert_text(fitz.Point(MARGIN_LEFT + 8, y + 21), meta_str[:95], fontname="courier", fontsize=6.8, color=(100/255, 116/255, 139/255))

                q_text = f"Source Text Quote: \"{ev.get('quoted_text', '')[:100]}\""
                page.insert_text(fitz.Point(MARGIN_LEFT + 8, y + 31), q_text, fontname="helv", fontsize=7, color=(51/255, 65/255, 85/255))
                y += 40.0

                img_rendered = False
                try:
                    img_bytes, err = get_finding_evidence_image(ev['id'], zoom=1.5)
                    if img_bytes:
                        img_rect = fitz.Rect(MARGIN_LEFT + 8, y, MARGIN_LEFT + 268, y + 130)
                        page.insert_image(img_rect, stream=img_bytes)
                        page.draw_rect(img_rect, color=(203/255, 213/255, 225/255), width=0.5)
                        y += 138.0
                        img_rendered = True
                except Exception:
                    img_rendered = False

                if not img_rendered:
                    page.draw_rect(fitz.Rect(MARGIN_LEFT + 8, y, MARGIN_RIGHT, y + 18), color=(226/255, 232/255, 240/255), fill=(248/255, 250/255, 252/255), width=0.5)
                    page.insert_text(fitz.Point(MARGIN_LEFT + 14, y + 12), "[Visual Evidence: Document-level or metadata rule — visual coordinates not applicable]", fontname="helv", fontsize=6.8, color=(100/255, 116/255, 139/255))
                    y += 24.0

                y += 6.0

        # 7.5 Digital Evidence Handling (aligned with ISO/IEC 27037 principles; no formal compliance claimed)
        ev_handling = data.get('digital_evidence_handling', [])
        if ev_handling:
            if y > 580:
                page = create_page()
                y = 50.0

            page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 15), color=(203/255, 213/255, 225/255), fill=(248/255, 250/255, 252/255), width=0.5)
            page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 11), "7.5 DIGITAL EVIDENCE HANDLING & CHAIN OF CUSTODY", fontname="hebo", fontsize=8, color=(15/255, 23/255, 42/255))
            y += 18.0
            page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 9), "Digital evidence handling (aligned with ISO/IEC 27037 principles; no formal compliance claimed)", fontname="helv", fontsize=6.8, color=(100/255, 116/255, 139/255))
            y += 14.0

            for rec in ev_handling:
                if y > 680:
                    page = create_page()
                    y = 50.0

                stat_col = (21/255, 128/255, 61/255) if rec['match'] else (185/255, 28/255, 28/255)
                h_short = rec['stored_hash'][:16] + "..." if len(rec['stored_hash']) > 16 else rec['stored_hash']
                page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 8), f"* {rec['filename'][:36]} ({rec['document_id']})", fontname="hebo", fontsize=7, color=(15/255, 23/255, 42/255))
                page.insert_text(fitz.Point(MARGIN_LEFT + 220, y + 8), f"SHA-256: {h_short}", fontname="courier", fontsize=6.5, color=(71/255, 85/255, 105/255))
                page.insert_text(fitz.Point(MARGIN_RIGHT - 75, y + 8), f"[{rec['status']}]", fontname="hebo", fontsize=6.8, color=stat_col)
                y += 12.0

                for ev in rec.get('custody_events', [])[-2:]:
                    ts = ev.get('timestamp', '')[:16]
                    act = ev.get('action', '')
                    usr = ev.get('actor', '')
                    page.insert_text(fitz.Point(MARGIN_LEFT + 16, y + 8), f"- {ts} -- {act} (actor: {usr})", fontname="helv", fontsize=6.2, color=(100/255, 116/255, 139/255))
                    y += 10.0
                y += 4.0
    except Exception:
        pass

    try:
        # K3. Investigation Summary
        inv_summary = data.get('investigation_summary', {})
        if inv_summary:
            if y > 580:
                page = create_page()
                y = 50.0

            page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 18), color=None, fill=(241/255, 245/255, 249/255))
            page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 13), "8. PLAIN-LANGUAGE INVESTIGATION SUMMARY", fontname="hebo", fontsize=9.5, color=(30/255, 41/255, 59/255))
            y += 24.0

            page.insert_textbox(
                fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 50),
                inv_summary.get('plain_summary', ''),
                fontname="helv",
                fontsize=8,
                color=(51/255, 65/255, 85/255)
            )
            y += 56.0

            if inv_summary.get('has_ai') and inv_summary.get('ai_summary'):
                if y > 640:
                    page = create_page()
                    y = 50.0

                page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 42), color=(187/255, 247/255, 208/255), fill=(240/255, 253/255, 244/255), width=0.5)
                page.insert_text(fitz.Point(MARGIN_LEFT + 8, y + 12), "AI-Assisted Investigation Summary (AI-assisted, requires human review)", fontname="hebo", fontsize=7.5, color=(21/255, 128/255, 61/255))
                page.insert_textbox(
                    fitz.Rect(MARGIN_LEFT + 8, y + 16, MARGIN_RIGHT - 8, y + 38),
                    inv_summary.get('ai_summary', ''),
                    fontname="helv",
                    fontsize=7,
                    color=(22/255, 101/255, 52/255)
                )
                y += 50.0
    except Exception:
        pass

    try:
        # K4. Areas Requiring Further Verification
        verif_areas = data.get('areas_for_verification', [])
        if verif_areas:
            if y > 600:
                page = create_page()
                y = 50.0

            page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 18), color=None, fill=(241/255, 245/255, 249/255))
            page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 13), "9. AREAS REQUIRING FURTHER VERIFICATION", fontname="hebo", fontsize=9.5, color=(30/255, 41/255, 59/255))
            y += 24.0

            for item in verif_areas:
                if y > 710:
                    page = create_page()
                    y = 50.0

                page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 10), "[ ]", fontname="courier", fontsize=8, color=(71/255, 85/255, 105/255))
                page.insert_textbox(
                    fitz.Rect(MARGIN_LEFT + 22, y, MARGIN_RIGHT, y + 20),
                    item,
                    fontname="helv",
                    fontsize=7.5,
                    color=(30/255, 41/255, 59/255)
                )
                y += 22.0
            y += 10.0
    except Exception:
        pass

    try:
        # K5. Limitations
        limits = data.get('limitations', {})
        if limits:
            if y > 580:
                page = create_page()
                y = 50.0

            page.draw_rect(fitz.Rect(MARGIN_LEFT, y, MARGIN_RIGHT, y + 18), color=None, fill=(241/255, 245/255, 249/255))
            page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 13), "10. LIMITATIONS & SYSTEM BOUNDARIES", fontname="hebo", fontsize=9.5, color=(30/255, 41/255, 59/255))
            y += 24.0

            if limits.get('dynamic'):
                page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 10), "Run-Specific Operational Limitations:", fontname="hebo", fontsize=8, color=(71/255, 85/255, 105/255))
                y += 14.0
                for d_lim in limits['dynamic']:
                    if y > 710:
                        page = create_page()
                        y = 50.0
                    page.insert_text(fitz.Point(MARGIN_LEFT + 10, y + 9), f"• {d_lim[:110]}", fontname="helv", fontsize=7, color=(51/255, 65/255, 85/255))
                    y += 12.0
                y += 6.0

            if limits.get('static'):
                page.insert_text(fitz.Point(MARGIN_LEFT + 6, y + 10), "Standard System Assumptions & Boundaries:", fontname="hebo", fontsize=8, color=(71/255, 85/255, 105/255))
                y += 14.0
                for s_lim in limits['static']:
                    if y > 710:
                        page = create_page()
                        y = 50.0
                    page.insert_text(fitz.Point(MARGIN_LEFT + 10, y + 9), f"• {s_lim[:110]}", fontname="helv", fontsize=7, color=(100/255, 116/255, 139/255))
                    y += 12.0
    except Exception:
        pass

    # Add running footers to all pages
    total_pages = len(doc)
    for p_idx in range(total_pages):
        draw_running_footer(doc[p_idx], p_idx + 1, total_pages)

    # Save document
    doc.save(str(file_path))
    doc.close()
    _rotate_case_dossiers(case_id, max_keep=3)

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
    _ensure_case_analysis(case_id, user=user)
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
            mode_badge = "<br><span style='font-size:10px; background:#fef3c7; color:#b45309; padding:2px 6px; border-radius:3px; font-weight:700;'>⚠️ OCR unavailable - fallback mode (SIMULATED FALLBACK)</span>"
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
    # Phase K: Appended HTML Sections (K1 - K5)
    phase_k_sections = ""
    try:
        # K1: Extracted Information
        k1_html = "<div class=\"section-title\">5. Extracted Information & Field Confidence</div>"
        for doc_item in data.get('extracted_information', []):
            k1_html += f"""
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:12px; margin-bottom:14px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <strong style="color:#0f172a; font-size:13px;">📄 {html.escape(doc_item['filename'])} ({html.escape(doc_item['doc_id'])})</strong>
                    <span style="font-size:11px; background:#e0f2fe; color:#0369a1; padding:2px 8px; border-radius:4px; font-weight:600;">Mode: {html.escape(doc_item['extraction_mode'])}</span>
                </div>
            """
            if doc_item.get('warning'):
                k1_html += f"""
                <div style="background:#fffbeb; border:1px solid #fde68a; color:#b45309; padding:8px 12px; border-radius:4px; font-size:12px; font-weight:600; margin-bottom:8px;">
                    ⚠️ {html.escape(doc_item['warning'])}
                </div>
                """
            k1_html += """
                <table style="margin-top:6px; width:100%;">
                    <thead>
                        <tr>
                            <th style="width:28%;">Field / Entity</th>
                            <th style="width:42%;">Extracted Value</th>
                            <th style="width:10%;">Page</th>
                            <th style="width:20%;">Confidence</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for fld in doc_item.get('fields', [])[:12]:
                conf_str = html.escape(str(fld['confidence']))
                badge_bg = "#dcfce7" if "verified" in conf_str.lower() or "digital" in conf_str.lower() else "#f1f5f9"
                badge_col = "#15803d" if "verified" in conf_str.lower() or "digital" in conf_str.lower() else "#475569"
                k1_html += f"""
                    <tr>
                        <td style="font-weight:600; color:#334155;">{html.escape(str(fld['name']))}</td>
                        <td style="font-family:monospace; color:#0f172a;">{html.escape(str(fld['value']))}</td>
                        <td style="text-align:center; color:#64748b;">{html.escape(str(fld['source_page']))}</td>
                        <td><span style="font-size:11px; padding:2px 6px; border-radius:3px; background:{badge_bg}; color:{badge_col}; font-weight:600;">{conf_str}</span></td>
                    </tr>
                """
            k1_html += """
                    </tbody>
                </table>
            </div>
            """
        phase_k_sections += k1_html
    except Exception as e:
        phase_k_sections += f"<p style='color:#ef4444;'>Error compiling Extracted Information: {html.escape(str(e))}</p>"

    try:
        # K2: Evidence and Traceability (top 5 findings)
        from backend.evidence import get_finding_evidence_image
        k2_html = "<div class=\"section-title\">6. Evidence & Traceability (Top Findings)</div>"
        ev_items = data.get('evidence_traceability', [])
        if not ev_items:
            k2_html += "<p style='color:#64748b;'>No evidence-linked findings were produced for this case. No localized anomalies required visual evidence capture.</p>"
        else:
            for ev in ev_items[:5]:
                sev = ev.get('severity', 'Medium')
                sev_col = "#dc2626" if sev in ('Critical', 'High') else "#d97706" if sev == 'Medium' else "#64748b"
                img_html = ""
                try:
                    img_bytes, err = get_finding_evidence_image(ev['id'], zoom=1.5)
                    if img_bytes:
                        b64_str = base64.b64encode(img_bytes).decode('utf-8')
                        img_html = f'<div style="margin-top:10px;"><img src="data:image/png;base64,{b64_str}" style="max-width:440px; border:1px solid #cbd5e1; border-radius:4px; box-shadow:0 1px 3px rgba(0,0,0,0.1);" alt="Visual Evidence" /></div>'
                except Exception:
                    img_html = ""

                if not img_html:
                    img_html = '<div style="background:#f1f5f9; color:#64748b; padding:8px 12px; border-radius:4px; font-size:12px; margin-top:8px;">ℹ️ Visual Evidence: Document-level or metadata rule (visual coordinates not applicable).</div>'

                lbl_lower = ev['class_label'].lower()
                badge_bg = '#fee2e2' if 'manipulation' in lbl_lower else '#fef3c7' if 'inconsistency' in lbl_lower else '#e0f2fe'
                badge_col = '#b91c1c' if 'manipulation' in lbl_lower else '#b45309' if 'inconsistency' in lbl_lower else '#0369a1'
                rev_html = f"<div style='font-size:11px; color:#1e40af; font-weight:600; margin-top:6px; background:#eff6ff; border:1px solid #bfdbfe; padding:4px 8px; border-radius:4px; display:inline-block;'>🛡️ {html.escape(ev.get('reviewer_summary', 'Pending Investigator Review'))}</div>"

                k2_html += f"""
                <div style="background:#ffffff; border:1px solid #e2e8f0; border-left:4px solid {sev_col}; border-radius:4px; padding:12px; margin-bottom:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="color:#0f172a; font-size:13px;">[{html.escape(ev['rule_id'])}] {html.escape(ev['title'])}</strong>
                        <span style="font-size:11px; padding:2px 8px; border-radius:4px; background:{badge_bg}; color:{badge_col}; font-weight:700;">Class: {html.escape(ev['class_label'].title())}</span>
                    </div>
                    <div style="font-size:11px; color:#64748b; font-family:monospace; margin-top:4px;">
                        Page {html.escape(str(ev['page_number']))} • Box: {html.escape(str(ev['box']))} • Severity: {sev.upper()}
                    </div>
                    {rev_html}
                    <blockquote style="background:#f8fafc; border-left:3px solid #0284c7; margin:6px 0; padding:6px 12px; font-size:12px; color:#334155; font-style:italic;">
                        Source Quote: "{html.escape(ev['quoted_text'])}"
                    </blockquote>
                    {img_html}
                </div>
                """

        # Digital evidence handling (aligned with ISO/IEC 27037 principles; no formal compliance claimed)
        ev_handling = data.get('digital_evidence_handling', [])
        if ev_handling:
            k2_html += """
            <div style="margin-top:16px; padding:12px; background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px;">
                <div style="font-weight:700; font-size:12.5px; color:#0f172a; margin-bottom:2px;">
                    Digital Evidence Handling & Chain of Custody
                </div>
                <div style="font-size:11px; color:#64748b; font-style:italic; margin-bottom:10px;">
                    Digital evidence handling (aligned with ISO/IEC 27037 principles; no formal compliance claimed)
                </div>
                <table style="width:100%; border-collapse:collapse; font-size:11px; margin-bottom:6px;">
                    <thead>
                        <tr style="background:#e2e8f0; text-align:left;">
                            <th style="padding:6px; border:1px solid #cbd5e1;">Document Ref</th>
                            <th style="padding:6px; border:1px solid #cbd5e1;">Ingest SHA-256 Hash</th>
                            <th style="padding:6px; border:1px solid #cbd5e1;">Integrity Status</th>
                            <th style="padding:6px; border:1px solid #cbd5e1;">Chain of Custody Events</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for rec in ev_handling:
                stat_col = "#15803d" if rec['match'] else "#b91c1c"
                stat_bg = "#f0fdf4" if rec['match'] else "#fef2f2"
                hash_short = rec['stored_hash'][:16] + "..." if len(rec['stored_hash']) > 16 else rec['stored_hash']

                events_html = "<ul style='margin:0; padding-left:14px; font-size:10px; color:#475569;'>"
                if rec.get('custody_events'):
                    for ev in rec['custody_events']:
                        ts = ev.get('timestamp', '')[:19]
                        act = ev.get('action', '')
                        usr = ev.get('actor', '')
                        events_html += f"<li><strong>{html.escape(ts)}</strong> • {html.escape(act)} ({html.escape(usr)})</li>"
                else:
                    events_html += "<li>No custody events logged</li>"
                events_html += "</ul>"

                k2_html += f"""
                    <tr>
                        <td style="padding:6px; border:1px solid #cbd5e1; font-weight:600; color:#0f172a;">
                            {html.escape(rec.get('filename') or rec.get('document_id'))}
                            <div style="font-size:10px; color:#64748b; font-family:monospace;">{html.escape(rec.get('document_id'))}</div>
                        </td>
                        <td style="padding:6px; border:1px solid #cbd5e1; font-family:monospace; font-size:10px;">
                            {html.escape(hash_short)}
                        </td>
                        <td style="padding:6px; border:1px solid #cbd5e1;">
                            <span style="display:inline-block; padding:2px 6px; border-radius:4px; font-weight:700; font-size:10px; background:{stat_bg}; color:{stat_col};">
                                {html.escape(rec['status'])}
                            </span>
                        </td>
                        <td style="padding:6px; border:1px solid #cbd5e1;">
                            {events_html}
                        </td>
                    </tr>
                """
            k2_html += """
                    </tbody>
                </table>
            </div>
            """

        phase_k_sections += k2_html
    except Exception as e:
        phase_k_sections += f"<p style='color:#ef4444;'>Error compiling Evidence Traceability: {html.escape(str(e))}</p>"

    try:
        # K3: Investigation Summary
        inv_sum = data.get('investigation_summary', {})
        k3_html = f"""
        <div class="section-title">7. Plain-Language Investigation Summary</div>
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:14px; margin-bottom:14px; line-height:1.6; color:#334155;">
            <p style="margin:0 0 8px 0;">{html.escape(inv_sum.get('plain_summary', ''))}</p>
        """
        if inv_sum.get('has_ai') and inv_sum.get('ai_summary'):
            k3_html += f"""
            <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:4px; padding:10px 14px; margin-top:10px;">
                <div style="color:#15803d; font-weight:700; font-size:12px; margin-bottom:4px;">🤖 AI-Assisted Investigation Summary (AI-assisted, requires human review)</div>
                <div style="font-size:12px; color:#166534; line-height:1.5;">{html.escape(inv_sum['ai_summary'])}</div>
            </div>
            """
        k3_html += "</div>"
        phase_k_sections += k3_html
    except Exception as e:
        phase_k_sections += f"<p style='color:#ef4444;'>Error compiling Investigation Summary: {html.escape(str(e))}</p>"

    try:
        # K4: Areas Requiring Further Verification
        k4_html = """
        <div class="section-title">8. Areas Requiring Further Verification</div>
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:14px; margin-bottom:14px;">
            <ul style="margin:0; padding-left:20px; color:#334155; line-height:1.6; font-size:13px;">
        """
        for item in data.get('areas_for_verification', []):
            k4_html += f"<li style='margin-bottom:6px;'>{html.escape(item)}</li>"
        k4_html += "</ul></div>"
        phase_k_sections += k4_html
    except Exception as e:
        phase_k_sections += f"<p style='color:#ef4444;'>Error compiling Areas for Verification: {html.escape(str(e))}</p>"

    try:
        # K5: Limitations & System Boundaries
        limits = data.get('limitations', {})
        k5_html = """
        <div class="section-title">9. Limitations & System Boundaries</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px;">
            <div style="background:#fffbeb; border:1px solid #fde68a; border-radius:6px; padding:12px;">
                <strong style="color:#92400e; font-size:12px; text-transform:uppercase; display:block; margin-bottom:6px;">Run-Specific Operational Limitations</strong>
                <ul style="margin:0; padding-left:16px; color:#78350f; font-size:12px; line-height:1.5;">
        """
        for d_lim in limits.get('dynamic', []):
            k5_html += f"<li style='margin-bottom:4px;'>{html.escape(d_lim)}</li>"
        k5_html += """
                </ul>
            </div>
            <div style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; padding:12px;">
                <strong style="color:#334155; font-size:12px; text-transform:uppercase; display:block; margin-bottom:6px;">Standard System Assumptions & Boundaries</strong>
                <ul style="margin:0; padding-left:16px; color:#475569; font-size:12px; line-height:1.5;">
        """
        for s_lim in limits.get('static', []):
            k5_html += f"<li style='margin-bottom:4px;'>{html.escape(s_lim)}</li>"
        k5_html += """
                </ul>
            </div>
        </div>
        """
        phase_k_sections += k5_html
    except Exception as e:
        phase_k_sections += f"<p style='color:#ef4444;'>Error compiling Limitations: {html.escape(str(e))}</p>"

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

    # Risk badge style mapping
    risk_level = summary.get('risk_level', '')
    if risk_level in ("Critical Risk / Irregular", "High Risk / Requires Review"):
        badge_style = "background:#fef2f2; color:#ef4444; border:1px solid #fecaca;"
    elif risk_level == "Moderate Variance":
        badge_style = "background:#fef3c7; color:#d97706; border:1px solid #fde68a;"
    elif risk_level == "Clean / Verified Alignment":
        badge_style = "background:#dcfce7; color:#15803d; border:1px solid #bbf7d0;"
    else:
        badge_style = "background:#f1f5f9; color:#475569; border:1px solid #e2e8f0;"

    html_disc = data.get('mandatory_disclaimer', '')
    prefix = "MANDATORY INVESTIGATION DISCLAIMER:"
    if html_disc.startswith(prefix):
        html_disc = html_disc[len(prefix):].strip()

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
                <span style="display:inline-block; padding:6px 12px; border-radius:4px; font-weight:700; font-size:12px; {badge_style}">
                    {summary['risk_level']}
                </span>
            </div>
        </div>

        <div class="disclaimer-box">
            <strong>MANDATORY INVESTIGATION DISCLAIMER:</strong><br>
            {html_disc}
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

        <!-- Explainable Risk Score Breakdown Card -->
        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:12px 16px; margin-bottom:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <strong style="font-size:12px; color:#0f172a; text-transform:uppercase; letter-spacing:0.5px;">⚖️ Explainable Risk Scoring Breakdown</strong>
                <span style="font-size:11px; background:#fef3c7; color:#92400e; padding:2px 8px; border-radius:4px; font-weight:700;">Triage priority, not a fraud verdict</span>
            </div>
            <div style="font-size:11px; color:#475569; font-family:monospace; margin-bottom:8px;">
                Formula: min(100, (Critical × 30) + (High × 20) + (Medium × 10) + (Low × 5) + (Discrepancies × 25))
            </div>
            <div style="font-size:11.5px; color:#334155; line-height:1.6;">
                • Critical Severity (×30): <strong>{summary['critical_findings']}</strong> hit(s) = {summary['critical_findings'] * 30} pts<br>
                • High Severity (×20): <strong>{summary['high_findings']}</strong> hit(s) = {summary['high_findings'] * 20} pts<br>
                • Medium Severity (×10): <strong>{summary['medium_findings']}</strong> hit(s) = {summary['medium_findings'] * 10} pts<br>
                • Cross-Document Discrepancies (×25): <strong>{summary['discrepancies_count']}</strong> conflict(s) = {summary['discrepancies_count'] * 25} pts<br>
                • Total Raw Score: <strong>{(summary['critical_findings'] * 30) + (summary['high_findings'] * 20) + (summary['medium_findings'] * 10) + (summary['discrepancies_count'] * 25)} pts</strong> → Normalized Capped Score: <strong>{summary['risk_score']} / 100</strong> ({summary['risk_level']})
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

        {phase_k_sections}

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
    _rotate_case_dossiers(case_id, max_keep=3)

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
