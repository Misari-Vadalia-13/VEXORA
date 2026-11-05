"""
VEXORA — Explainability & Forensic Evidence Provenance Module
Implements the 3-part evidence structure:
1. "What we observed" (raw measurable facts: font name, coordinates, hash, color distance, arithmetic delta)
2. "Why it matters" (inconsistency / operational impact: arithmetic disparity, font shift mid-sentence)
3. "How sure we are" (confidence % + what would raise/lower it)
4. Suggested human verification step (exact manual validation action in Adobe Acrobat, ExifTool, or physical review)

Status Badges:
- "Observed" (factual observation, neutral)
- "Detected inconsistency" (rule mismatch, arithmetic error, date reversal)
- "Potential manipulation" (forensic anomaly, font mismatch, ELA patch, signature splice)
"""

import re
import json

def get_status_badge(finding):
    """
    Classifies a finding into one of three strict standardized labels:
    - 'Observed' (neutral factual observation)
    - 'Detected inconsistency' (relational/arithmetic/chronological mismatch)
    - 'Potential manipulation' (visual/structural tampering indicator)
    """
    if not finding or not isinstance(finding, dict):
        return "Observed"
        
    ev_class = str(finding.get('evidence_class') or '').strip().lower()
    if ev_class in ('potential manipulation', 'tampering', 'splice', 'forgery'):
        return "Potential manipulation"
    if ev_class in ('inconsistency', 'detected inconsistency', 'discrepancy', 'conflict'):
        return "Detected inconsistency"
    if ev_class in ('observation', 'observed', 'clean', 'info'):
        return "Observed"

    sev = str(finding.get('severity') or 'Medium').capitalize()
    rule_id = str(finding.get('rule_id') or '').upper()
    title = str(finding.get('title') or '').lower()
    cat = str(finding.get('category') or '').lower()

    if sev in ('Critical', 'High') or rule_id.startswith(('IMG-', 'PDF-001', 'PDF-002', 'PDF-004', 'RULE-VIS-')):
        return "Potential manipulation"
    if 'tamper' in title or 'alter' in title or 'patch' in title or 'splice' in title or 'clone' in title:
        return "Potential manipulation"

    if sev == 'Medium' or rule_id.startswith(('RULE-DOC-', 'RULE-CTX-', 'PDF-003')):
        return "Detected inconsistency"
    if 'mismatch' in title or 'discrepancy' in title or 'inconsisten' in title or 'reversal' in title:
        return "Detected inconsistency"

    return "Observed"


def format_explainable_finding(finding):
    """
    Generates a structured 3-part forensic evidence card with verification guidance.
    Uses deterministic rule definitions with measured coordinates and evidence traces.
    """
    if not finding or not isinstance(finding, dict):
        return {
            "status_badge": "Observed",
            "what_observed": "No measurable technical anomaly detected.",
            "why_it_matters": "Document primitive adheres to expected format baseline.",
            "how_sure": "90.0% confidence based on default parser heuristics.",
            "verification_step": "Inspect document visually to confirm baseline legibility."
        }

    status_badge = get_status_badge(finding)
    rule_id = str(finding.get('rule_id') or 'RULE-GEN-001').upper()
    title = finding.get('title') or 'Forensic Observation'
    desc = finding.get('description') or ''
    evidence = finding.get('evidence') or ''
    coords = finding.get('coordinates')
    page = finding.get('page_number', 1)

    raw_conf = finding.get('confidence')
    if raw_conf is not None:
        try:
            conf_pct = float(raw_conf) * 100.0 if float(raw_conf) <= 1.0 else float(raw_conf)
        except (ValueError, TypeError):
            conf_pct = 85.0
    else:
        conf_pct = 85.0

    # 1. WHAT WE OBSERVED (Raw measurable facts)
    coords_str = f" at bounding box [{coords}] on Page {page}" if coords else f" on Page {page}"
    if evidence:
        what_observed = f"{desc} Measured fact: {evidence}{coords_str}."
    else:
        what_observed = f"{desc}{coords_str}."

    # 2. WHY IT MATTERS (The inconsistency or risk consequence)
    if "font" in title.lower() or "vis-001" in rule_id.lower():
        why_it_matters = (
            "Divergence in typographic font families or sizing within the same structural column "
            "strongly indicates localized post-generation text insertion or value alteration."
        )
    elif "baseline" in title.lower() or "vis-004" in rule_id.lower():
        why_it_matters = (
            "Vertical baseline misalignment indicates characters or monetary figures were "
            "pasted or drawn in a separate rendering pass from the surrounding sentence."
        )
    elif "arithmetic" in title.lower() or "doc-001" in rule_id.lower():
        why_it_matters = (
            "The computed sum of line items or subtotal plus tax contradicts the stated grand total, "
            "indicating that financial figures were edited without recalculating dependent totals."
        )
    elif "date" in title.lower() or "timeline" in title.lower() or "ctx-003" in rule_id.lower() or "doc-002" in rule_id.lower():
        why_it_matters = (
            "Chronological sequence violation where dependent milestone dates (e.g., payment due date) "
            "precede originating execution dates, or execute in an impossible historical sequence."
        )
    elif "metadata" in title.lower() or "pdf-003" in rule_id.lower():
        why_it_matters = (
            "Document metadata headers contain signatures from consumer editing suites (e.g. iLovePDF, Photoshop) "
            "or divergent creation and modification timestamps, contrary to native enterprise billing generators."
        )
    elif "incremental" in title.lower() or "pdf-002" in rule_id.lower():
        why_it_matters = (
            "The PDF stream contains an appended cross-reference section (incremental update) modifying "
            "existing content objects after initial document finalization."
        )
    elif "image" in title.lower() or rule_id.startswith("IMG-"):
        why_it_matters = (
            "Pixel error level analysis (ELA) or localized noise frequency variance reveals that an image "
            "patch or stamp was spliced into this region from a different source."
        )
    elif "mandatory" in title.lower() or "ctx-001" in rule_id.lower():
        why_it_matters = (
            "Document lacks essential statutory or commercial identifiers required for auditability "
            "(such as purchase order reference, tax registration, or line-item breakdown)."
        )
    else:
        why_it_matters = f"Inconsistency in document logic or layout: {title} warrants verification."

    # 3. HOW SURE WE ARE (Confidence % + factors that raise or lower it)
    if status_badge == "Potential manipulation":
        factors = (
            f"{conf_pct:.1f}% confidence. "
            "Factors that would raise confidence: Matching raster compression artifacts or secondary metadata traces. "
            "Factors that would lower confidence: Non-standard enterprise print driver export or legitimate multi-author drafting."
        )
    elif status_badge == "Detected inconsistency":
        factors = (
            f"{conf_pct:.1f}% confidence. "
            "Factors that would raise confidence: Corroboration by cross-document bank statements or counterpart POs. "
            "Factors that would lower confidence: Non-standard line-item discount structures or unlisted tax exemptions."
        )
    else:
        factors = (
            f"{conf_pct:.1f}% confidence. "
            "Factors that would raise confidence: Multi-field cross-reference validation. "
            "Factors that would lower confidence: OCR transcription noise or low scan resolution."
        )

    # 4. SUGGESTED HUMAN VERIFICATION STEP
    if "font" in title.lower() or "vis-001" in rule_id.lower():
        verification_step = (
            f"Open original in Adobe Acrobat -> File -> Properties -> Fonts. "
            f"Inspect font list for embedded font outliers, or select text on Page {page} to verify font family properties."
        )
    elif "baseline" in title.lower() or "vis-004" in rule_id.lower():
        verification_step = (
            f"Zoom to 400% on Page {page} in a vector viewer. Use a digital ruler or guide to compare the bottom baseline "
            "of adjacent numerical characters against surrounding narrative text."
        )
    elif "arithmetic" in title.lower() or "doc-001" in rule_id.lower():
        verification_step = (
            "Perform manual ledger reconciliation: calculate (Subtotal + Applicable Tax - Stated Deductions) "
            "using an independent calculator and compare against the reported Grand Total figure."
        )
    elif "date" in title.lower() or "timeline" in title.lower():
        verification_step = (
            "Compare stated execution dates against external ERP / SWIFT / postal transmission records "
            "to establish the definitive chronological event sequence."
        )
    elif "metadata" in title.lower() or "pdf-003" in rule_id.lower() or "pdf-002" in rule_id.lower():
        verification_step = (
            "Run ExifTool or `pdfinfo -meta` in terminal to inspect raw XMP metadata, /Producer, /Creator, "
            "and trailer xref offsets for post-issuance modification records."
        )
    elif rule_id.startswith("IMG-"):
        verification_step = (
            f"Inspect high-resolution crop of Page {page} at 800% zoom under high contrast. "
            "Look for rectangular boundary halos, resampling blur, or quantization blocking artifacts."
        )
    else:
        verification_step = (
            f"Conduct side-by-side comparison against the counterpart document or verify authenticity directly "
            f"with the issuing entity ({finding.get('category', 'issuing authority')})."
        )

    return {
        "status_badge": status_badge,
        "what_observed": what_observed,
        "why_it_matters": why_it_matters,
        "how_sure": factors,
        "confidence_pct": round(conf_pct, 1),
        "verification_step": verification_step
    }
