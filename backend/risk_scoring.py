"""
VEXORA — Explainable Case Risk Scoring Engine
Hackathon Innovation Module: Provides full mathematical explainability for case-level
forensic triage. Replaces opaque black-box scoring with deterministic, additive weights:

- Critical finding: 30 pts each
- High finding: 20 pts each
- Medium finding: 10 pts each
- Low finding: 5 pts each
- Cross-document discrepancy: 25 pts each
- Normalized & capped at 100.

Mandatory Audit Principle:
"Triage priority, not a fraud verdict" — Algorithmic anomaly scores indicate investigative
priority for human inspection and do NOT represent definitive determinations of fraud.
"""

import json
from backend.models import get_case_by_id, get_all_documents, get_all_findings
from backend.comparator import compare_case_documents

WEIGHT_CRITICAL = 30
WEIGHT_HIGH = 20
WEIGHT_MEDIUM = 10
WEIGHT_LOW = 5
WEIGHT_DISCREPANCY = 25

DISCLAIMER_TEXT = "Triage priority, not a fraud verdict"
FORMULA_TEXT = "score = min(100, (critical * 30) + (high * 20) + (medium * 10) + (low * 5) + (discrepancies * 25))"


def calculate_case_risk_score(case_id):
    """
    Computes an explainable, deterministic forensic risk score (0-100) for a case.
    Returns complete mathematical breakdown, contributing items, and human-in-the-loop disclaimer.
    """
    case = get_case_by_id(case_id)
    if not case:
        raise ValueError(f"Case '{case_id}' not found.")

    docs = get_all_documents(case_id=case_id)
    findings = get_all_findings(case_id=case_id)

    # Cross-document discrepancies
    discrepancies = []
    if len(docs) >= 2:
        try:
            comp_res = compare_case_documents(case_id)
            if isinstance(comp_res, dict) and comp_res.get('success'):
                discrepancies = comp_res.get('discrepancies', [])
        except Exception:
            discrepancies = []

    crit_findings = [f for f in findings if f.get('severity') == 'Critical']
    high_findings = [f for f in findings if f.get('severity') == 'High']
    med_findings = [f for f in findings if f.get('severity') == 'Medium']
    low_findings = [f for f in findings if f.get('severity') == 'Low']

    crit_count = len(crit_findings)
    high_count = len(high_findings)
    med_count = len(med_findings)
    low_count = len(low_findings)
    disc_count = len(discrepancies)

    crit_subtotal = crit_count * WEIGHT_CRITICAL
    high_subtotal = high_count * WEIGHT_HIGH
    med_subtotal = med_count * WEIGHT_MEDIUM
    low_subtotal = low_count * WEIGHT_LOW
    disc_subtotal = disc_count * WEIGHT_DISCREPANCY

    raw_score = crit_subtotal + high_subtotal + med_subtotal + low_subtotal + disc_subtotal
    final_score = min(raw_score, 100)

    # Risk level classification
    if len(docs) == 0:
        risk_level = "Unassessed / Empty Case"
    elif final_score >= 70 or crit_count > 0:
        risk_level = "Critical Risk / Irregular"
    elif final_score >= 40 or high_count > 0:
        risk_level = "High Risk / Requires Review"
    elif final_score >= 20 or med_count > 0:
        risk_level = "Moderate Variance"
    elif final_score > 0:
        risk_level = "Low Risk / Minor Observations"
    else:
        risk_level = "Clean / Verified Alignment"

    breakdown = [
        {
            'category': 'Critical Findings',
            'severity': 'Critical',
            'weight_each': WEIGHT_CRITICAL,
            'count': crit_count,
            'subtotal': crit_subtotal,
            'items': [{'id': f['id'], 'title': f['title'], 'rule_id': f.get('rule_id'), 'doc_id': f.get('document_id')} for f in crit_findings]
        },
        {
            'category': 'High Severity Findings',
            'severity': 'High',
            'weight_each': WEIGHT_HIGH,
            'count': high_count,
            'subtotal': high_subtotal,
            'items': [{'id': f['id'], 'title': f['title'], 'rule_id': f.get('rule_id'), 'doc_id': f.get('document_id')} for f in high_findings]
        },
        {
            'category': 'Medium Severity Findings',
            'severity': 'Medium',
            'weight_each': WEIGHT_MEDIUM,
            'count': med_count,
            'subtotal': med_subtotal,
            'items': [{'id': f['id'], 'title': f['title'], 'rule_id': f.get('rule_id'), 'doc_id': f.get('document_id')} for f in med_findings]
        },
        {
            'category': 'Low Severity Findings',
            'severity': 'Low',
            'weight_each': WEIGHT_LOW,
            'count': low_count,
            'subtotal': low_subtotal,
            'items': [{'id': f['id'], 'title': f['title'], 'rule_id': f.get('rule_id'), 'doc_id': f.get('document_id')} for f in low_findings]
        },
        {
            'category': 'Cross-Document Discrepancies',
            'severity': 'Discrepancy',
            'weight_each': WEIGHT_DISCREPANCY,
            'count': disc_count,
            'subtotal': disc_subtotal,
            'items': [{
                'attribute': d.get('attribute') or d.get('field') or 'Attribute Discrepancy',
                'explanation': d.get('explanation') or d.get('message') or '',
                'doc_a': d.get('doc_a_filename') or d.get('doc_a_id'),
                'doc_b': d.get('doc_b_filename') or d.get('doc_b_id')
            } for d in discrepancies]
        }
    ]

    total_findings = len(findings)
    explanation = (
        f"Case risk score of {final_score}/100 computed from {total_findings} finding(s) "
        f"({crit_count} Critical, {high_count} High, {med_count} Medium, {low_count} Low) and "
        f"{disc_count} cross-document discrepancy(ies). This metric reflects investigative triage "
        f"priority, not a legal or confirmed fraud determination."
    )

    return {
        'case_id': case_id,
        'case_title': case.get('title', ''),
        'risk_score': final_score,
        'raw_score': raw_score,
        'capped_at_100': raw_score > 100,
        'risk_level': risk_level,
        'formula': FORMULA_TEXT,
        'weights': {
            'critical': WEIGHT_CRITICAL,
            'high': WEIGHT_HIGH,
            'medium': WEIGHT_MEDIUM,
            'low': WEIGHT_LOW,
            'discrepancy': WEIGHT_DISCREPANCY
        },
        'counts': {
            'critical': crit_count,
            'high': high_count,
            'medium': med_count,
            'low': low_count,
            'discrepancies': disc_count,
            'total_findings': total_findings,
            'document_count': len(docs)
        },
        'breakdown': breakdown,
        'disclaimer': DISCLAIMER_TEXT,
        'explanation': explanation
    }
