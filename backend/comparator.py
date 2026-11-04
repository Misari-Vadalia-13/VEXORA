"""
VEXORA — Cross-Document Comparison & Evidence Mapping Engine (Phase 7)
Compares multiple documents across financial amounts, dates, identities,
counterparties, and identifiers to detect discrepancies and map evidence provenance.
"""

import os
import re
import json
import difflib
from datetime import datetime
from pathlib import Path

from backend.models import (
    get_document_by_id,
    get_all_documents,
    save_document_extraction,
    query_db,
    execute_db,
    log_audit
)
from backend.extractor import extract_document_content
from backend.analyzer import resolve_document_file_path

# =====================================================================
# Helper Utilities for Cross-Document Value Normalization
# =====================================================================

def parse_monetary_amount(raw_str):
    """Extracts numeric float value from currency string, e.g. '$4,850,000.50' -> 4850000.50."""
    if not raw_str:
        return None
    cleaned = re.sub(r'[^\d.]', '', raw_str)
    try:
        return float(cleaned)
    except ValueError:
        return None

def normalize_text(text):
    """Lowercases, trims, and strips punctuation for robust matching."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', text.lower())).strip()

def calculate_similarity(s1, s2):
    """Calculates SequenceMatcher ratio between two normalized strings (0.0 to 1.0)."""
    n1, n2 = normalize_text(s1), normalize_text(s2)
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0
    return difflib.SequenceMatcher(None, n1, n2).ratio()


def calculate_jaccard_token_similarity(text_a, text_b):
    """
    Computes Jaccard token similarity ratio between two document text strings.
    Formula: J(A, B) = |tokens(A) ∩ tokens(B)| / |tokens(A) ∪ tokens(B)|
    Ignores short punctuation and common stopwords.
    """
    if not text_a or not text_b:
        return 0.0

    stop_words = {
        'the', 'and', 'for', 'with', 'this', 'that', 'from', 'are', 'was',
        'were', 'will', 'have', 'has', 'had', 'been', 'each', 'any', 'all',
        'doc', 'pdf', 'page'
    }

    def tokenize(txt):
        words = re.findall(r'[a-zA-Z0-9]{3,}', str(txt).lower())
        return set(w for w in words if w not in stop_words)

    tokens_a = tokenize(text_a)
    tokens_b = tokenize(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = len(tokens_a.intersection(tokens_b))
    union = len(tokens_a.union(tokens_b))
    if union == 0:
        return 0.0

    return round(intersection / float(union), 4)

# =====================================================================
# 1. Pairwise Document Comparison Engine
# =====================================================================

def compare_two_documents(doc_a_id, doc_b_id, user="System"):
    """
    Performs deep cross-document comparison between Document A and Document B.
    Evaluates:
    - Monetary amounts & transaction balances
    - Chronological dates & execution timelines
    - Legal counterparty & person identities
    - Identifiers & statutory reference codes
    - Cryptographic hash duplicates
    """
    if doc_a_id == doc_b_id:
        return {
            'success': False,
            'error': "Cannot compare a document against itself. Please select two distinct documents."
        }

    doc_a = get_document_by_id(doc_a_id)
    doc_b = get_document_by_id(doc_b_id)

    if not doc_a:
        return {'success': False, 'error': f"Document A '{doc_a_id}' not found."}
    if not doc_b:
        return {'success': False, 'error': f"Document B '{doc_b_id}' not found."}

    # Ensure both documents have extraction data
    def get_or_extract(doc):
        data = None
        if doc.get('extracted_data'):
            try:
                data = json.loads(doc['extracted_data'])
            except Exception:
                data = None
        if not data:
            file_path = resolve_document_file_path(doc)
            if file_path and os.path.exists(file_path):
                data = extract_document_content(file_path)
                save_document_extraction(doc['id'], data, user=user)
        return data or {'entities': {}, 'metadata': {}, 'full_text': ''}

    data_a = get_or_extract(doc_a)
    data_b = get_or_extract(doc_b)

    entities_a = data_a.get('entities', {})
    entities_b = data_b.get('entities', {})

    alignment_matrix = []

    # 1. Exact Duplicate Document Check (SHA-256)
    if doc_a.get('file_hash') and doc_b.get('file_hash') and doc_a['file_hash'] == doc_b['file_hash']:
        alignment_matrix.append({
            'attribute': 'Cryptographic Integrity (SHA-256)',
            'val_a': doc_a['file_hash'][:16] + '...',
            'val_b': doc_b['file_hash'][:16] + '...',
            'page_a': 1,
            'page_b': 1,
            'status': 'Duplicate',
            'verdict': '🚨 IDENTICAL FILE DUPLICATE',
            'explanation': 'Both files share the identical cryptographic SHA-256 hash. Re-uploaded under distinct filenames.'
        })
    else:
        # Near-duplicate text similarity check via Jaccard token overlap
        txt_a = data_a.get('full_text') or doc_a.get('extracted_text') or ''
        txt_b = data_b.get('full_text') or doc_b.get('extracted_text') or ''
        jaccard_score = calculate_jaccard_token_similarity(txt_a, txt_b)
        if jaccard_score >= 0.78:
            alignment_matrix.append({
                'attribute': 'Document Content Near-Duplicate',
                'val_a': f"{len(txt_a.split())} words",
                'val_b': f"{len(txt_b.split())} words",
                'page_a': 1,
                'page_b': 1,
                'status': 'Conflict',
                'verdict': '⚠️ Near-Duplicate Document Variant',
                'explanation': (
                    f"Significant textual content overlap (Jaccard token similarity: {round(jaccard_score * 100, 1)}%) detected "
                    f"between distinct physical files. Strongly indicates a cloned invoice or contract template "
                    f"with altered line items, amounts, or parties (double-billing or substitution risk)."
                )
            })

    # 2. Priority 5 Upgrade: Structured Label-Aware Financial Comparison
    struct_a = data_a.get('structured_fields', {})
    struct_b = data_b.get('structured_fields', {})
    fin_a = struct_a.get('financials', {})
    fin_b = struct_b.get('financials', {})

    # Check grand totals if structured fields are present
    if fin_a.get('grand_total') is not None and fin_b.get('grand_total') is not None:
        tot_a = fin_a['grand_total']
        tot_b = fin_b['grand_total']
        if abs(tot_a - tot_b) < 0.02:
            alignment_matrix.append({
                'attribute': 'Normalized Grand Total',
                'val_a': f"${tot_a:,.2f}",
                'val_b': f"${tot_b:,.2f}",
                'page_a': 1,
                'page_b': 1,
                'status': 'Match',
                'verdict': '✓ Exact Grand Total Match',
                'explanation': f"Structured grand totals match identically (${tot_a:,.2f}) across both files."
            })
        else:
            diff = abs(tot_a - tot_b)
            pct = round((diff / max(tot_a, tot_b)) * 100, 1)
            alignment_matrix.append({
                'attribute': 'Normalized Grand Total',
                'val_a': f"${tot_a:,.2f}",
                'val_b': f"${tot_b:,.2f}",
                'page_a': 1,
                'page_b': 1,
                'status': 'Conflict',
                'verdict': '⚠️ Grand Total Discrepancy',
                'explanation': f"Financial variance of ${diff:,.2f} ({pct}%) detected between Document A (${tot_a:,.2f}) and Document B (${tot_b:,.2f})."
            })

    # Cross-document PO to Invoice or Bank Statement Sequence Anomaly Check
    dates_dict_a = struct_a.get('dates', {})
    dates_dict_b = struct_b.get('dates', {})
    type_a = struct_a.get('document_type', '')
    type_b = struct_b.get('document_type', '')

    if type_a == 'invoice' and type_b == 'bank_statement':
        inv_dt_str = dates_dict_a.get('issue_date')
        if inv_dt_str and data_b.get('entities', {}).get('dates'):
            try:
                from backend.correlator import parse_date_robust
                d_inv = parse_date_robust(inv_dt_str)
                for d_entry in data_b['entities']['dates']:
                    d_bank = parse_date_robust(d_entry['value'])
                    if d_inv and d_bank and d_bank < d_inv:
                        alignment_matrix.append({
                            'attribute': 'Cross-Document Chronology',
                            'val_a': f"Invoice: {inv_dt_str}",
                            'val_b': f"Bank: {d_entry['value']}",
                            'page_a': 1,
                            'page_b': d_entry.get('page', 1),
                            'status': 'Conflict',
                            'verdict': '⚠️ Pre-Invoice Settlement Anomaly',
                            'explanation': f"Bank record reflects transaction clearing ({d_entry['value']}) prior to invoice issue date ({inv_dt_str})."
                        })
                        break
            except Exception:
                pass

    # 2. General Monetary Values Comparison (Fallback / Supplementary)
    money_a = entities_a.get('monetary_values', [])
    money_b = entities_b.get('monetary_values', [])

    if money_a and money_b:
        # Compare highest monetary values (typically grand total or settlement amount)
        top_a = max(money_a, key=lambda m: parse_monetary_amount(m['value']) or 0.0)
        top_b = max(money_b, key=lambda m: parse_monetary_amount(m['value']) or 0.0)

        amt_a = parse_monetary_amount(top_a['value'])
        amt_b = parse_monetary_amount(top_b['value'])

        if amt_a and amt_b:
            if abs(amt_a - amt_b) < 0.01:
                alignment_matrix.append({
                    'attribute': 'Primary Monetary Value',
                    'val_a': top_a['value'],
                    'val_b': top_b['value'],
                    'page_a': top_a.get('page', 1),
                    'page_b': top_b.get('page', 1),
                    'status': 'Match',
                    'verdict': '✓ Exact Match',
                    'explanation': f"Stated figures match perfectly ({top_a['value']}) across both documents."
                })
            else:
                diff = abs(amt_a - amt_b)
                pct_diff = round((diff / max(amt_a, amt_b)) * 100, 1)
                alignment_matrix.append({
                    'attribute': 'Primary Monetary Value',
                    'val_a': top_a['value'],
                    'val_b': top_b['value'],
                    'page_a': top_a.get('page', 1),
                    'page_b': top_b.get('page', 1),
                    'status': 'Conflict',
                    'verdict': '⚠️ Monetary Mismatch',
                    'explanation': (
                        f"Financial disparity of ${diff:,.2f} ({pct_diff}% variance) detected between "
                        f"Document A ({top_a['value']}) and Document B ({top_b['value']})."
                    )
                })

    # 3. Dates & Timeline Comparison
    dates_a = entities_a.get('dates', [])
    dates_b = entities_b.get('dates', [])

    if dates_a and dates_b:
        # Cross check dates
        date_vals_a = {d['value']: d.get('page', 1) for d in dates_a}
        date_vals_b = {d['value']: d.get('page', 1) for d in dates_b}

        # Check for intersection
        shared_dates = set(date_vals_a.keys()) & set(date_vals_b.keys())
        if shared_dates:
            d_val = next(iter(shared_dates))
            alignment_matrix.append({
                'attribute': 'Transaction / Event Date',
                'val_a': d_val,
                'val_b': d_val,
                'page_a': date_vals_a[d_val],
                'page_b': date_vals_b[d_val],
                'status': 'Match',
                'verdict': '✓ Synchronized Date',
                'explanation': f"Chronological timestamp '{d_val}' is mutually affirmed in both records."
            })
        else:
            # Different dates present
            first_a = dates_a[0]
            first_b = dates_b[0]
            alignment_matrix.append({
                'attribute': 'Referenced Execution Date',
                'val_a': first_a['value'],
                'val_b': first_b['value'],
                'page_a': first_a.get('page', 1),
                'page_b': first_b.get('page', 1),
                'status': 'Mismatch',
                'verdict': '⚠️ Timeline Discrepancy',
                'explanation': f"Document A records date '{first_a['value']}' while Document B specifies '{first_b['value']}'. Timeline variance requires verification."
            })

    # 4. Legal Counterparties & Organizations Comparison
    orgs_a = [o['value'] for o in entities_a.get('organizations', [])]
    orgs_b = [o['value'] for o in entities_b.get('organizations', [])]

    if orgs_a and orgs_b:
        best_sim = 0.0
        best_pair = (orgs_a[0], orgs_b[0])

        from backend.correlator import fuzzy_party_similarity, normalize_party_name
        is_fuzzy_match = False
        for oa in orgs_a:
            for ob in orgs_b:
                sim = calculate_similarity(oa, ob)
                f_match, f_score = fuzzy_party_similarity(oa, ob)
                effective_score = max(sim, f_score)
                if effective_score > best_sim:
                    best_sim = effective_score
                    best_pair = (oa, ob)
                    is_fuzzy_match = f_match

        if best_sim >= 0.95:
            alignment_matrix.append({
                'attribute': 'Contracting Entity / Counterparty',
                'val_a': best_pair[0],
                'val_b': best_pair[1],
                'page_a': 1,
                'page_b': 1,
                'status': 'Match',
                'verdict': '✓ Counterparty Match',
                'explanation': f"Entity names '{best_pair[0]}' and '{best_pair[1]}' correspond with {int(best_sim * 100)}% token alignment."
            })
        elif best_sim >= 0.50:
            alignment_matrix.append({
                'attribute': 'Contracting Entity / Counterparty',
                'val_a': best_pair[0],
                'val_b': best_pair[1],
                'page_a': 1,
                'page_b': 1,
                'status': 'Conflict',
                'verdict': '⚠️ Counterparty Variance',
                'explanation': f"Similar but legally distinct entity names: '{best_pair[0]}' vs '{best_pair[1]}' ({int(best_sim * 100)}% similarity). Possible entity substitution."
            })
        else:
            alignment_matrix.append({
                'attribute': 'Contracting Entity / Counterparty',
                'val_a': best_pair[0],
                'val_b': best_pair[1],
                'page_a': 1,
                'page_b': 1,
                'status': 'Mismatch',
                'verdict': '⚠️ Disparate Entities',
                'explanation': f"Document A specifies '{best_pair[0]}' whereas Document B specifies '{best_pair[1]}'. Distinct organizations cited."
            })

    # 5. Persons / Signatories Comparison
    persons_a = [p['value'] for p in entities_a.get('persons', [])]
    persons_b = [p['value'] for p in entities_b.get('persons', [])]

    if persons_a and persons_b:
        shared_persons = set([normalize_text(p) for p in persons_a]) & set([normalize_text(p) for p in persons_b])
        if shared_persons:
            alignment_matrix.append({
                'attribute': 'Authorized Signatory / Person',
                'val_a': persons_a[0],
                'val_b': persons_b[0],
                'page_a': 1,
                'page_b': 1,
                'status': 'Match',
                'verdict': '✓ Signatory Verified',
                'explanation': f"Signatory '{persons_a[0]}' affirmed across both records."
            })
        else:
            sim = calculate_similarity(persons_a[0], persons_b[0])
            alignment_matrix.append({
                'attribute': 'Authorized Signatory / Person',
                'val_a': persons_a[0],
                'val_b': persons_b[0],
                'page_a': 1,
                'page_b': 1,
                'status': 'Mismatch' if sim < 0.8 else 'Conflict',
                'verdict': '⚠️ Signatory Discrepancy',
                'explanation': f"Signatory mismatch: '{persons_a[0]}' vs '{persons_b[0]}'."
            })

    # 6. Identifiers Comparison (Invoices, POs, Tax IDs)
    ids_a = [i['value'] for i in entities_a.get('identifiers', [])]
    ids_b = [i['value'] for i in entities_b.get('identifiers', [])]

    if ids_a and ids_b:
        shared_ids = set([i.upper() for i in ids_a]) & set([i.upper() for i in ids_b])
        if shared_ids:
            shared_id = next(iter(shared_ids))
            alignment_matrix.append({
                'attribute': 'Reference Identifier',
                'val_a': shared_id,
                'val_b': shared_id,
                'page_a': 1,
                'page_b': 1,
                'status': 'Match',
                'verdict': '✓ Correlated Reference',
                'explanation': f"Mutual statutory identifier '{shared_id}' connects both records into a verified evidentiary pair."
            })
        else:
            alignment_matrix.append({
                'attribute': 'Reference Identifier',
                'val_a': ids_a[0],
                'val_b': ids_b[0],
                'page_a': 1,
                'page_b': 1,
                'status': 'Mismatch',
                'verdict': '⚠️ Identifier Divergence',
                'explanation': f"Unlinked reference numbers: '{ids_a[0]}' vs '{ids_b[0]}'."
            })

    # If no overlapping entity categories were present
    if not alignment_matrix:
        alignment_matrix.append({
            'attribute': 'General Content Overlap',
            'val_a': f"{doc_a.get('category', 'Document')} ({data_a.get('total_words', 0)} words)",
            'val_b': f"{doc_b.get('category', 'Document')} ({data_b.get('total_words', 0)} words)",
            'page_a': 1,
            'page_b': 1,
            'status': 'Mismatch',
            'verdict': 'ℹ️ Disparate Document Types',
            'explanation': "Documents represent different domains with no direct overlapping financial, entity, or reference fields."
        })

    # Metrics computation
    matches_count = sum(1 for m in alignment_matrix if m['status'] == 'Match')
    conflicts_count = sum(1 for m in alignment_matrix if m['status'] in ('Conflict', 'Duplicate'))
    mismatches_count = sum(1 for m in alignment_matrix if m['status'] == 'Mismatch')
    total_comparisons = len(alignment_matrix)

    if conflicts_count > 0:
        verdict = 'High Discrepancy'
        risk_score = min(40 + (conflicts_count * 20), 100)
    elif mismatches_count > 0:
        verdict = 'Moderate Variance'
        risk_score = min(20 + (mismatches_count * 10), 60)
    else:
        verdict = 'Consistent Records'
        risk_score = 0

    comparison_id = f"CMP-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Cache / Persist comparison record in database
    try:
        execute_db(
            """
            INSERT INTO comparisons (id, case_id, doc_a_id, doc_b_id, discrepancies_count, matches_count, results_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                comparison_id,
                doc_a.get('case_id') or doc_b.get('case_id'),
                doc_a_id,
                doc_b_id,
                conflicts_count + mismatches_count,
                matches_count,
                json.dumps(alignment_matrix)
            )
        )
        log_audit(
            "DOCUMENTS_COMPARED",
            "comparison",
            comparison_id,
            f"Compared '{doc_a['filename']}' against '{doc_b['filename']}': {conflicts_count} conflicts, {matches_count} matches.",
            user
        )
    except Exception as e:
        # Table might not exist yet if before init_db migration
        pass

    return {
        'success': True,
        'comparison_id': comparison_id,
        'doc_a': {
            'id': doc_a['id'],
            'filename': doc_a['filename'],
            'category': doc_a.get('category'),
            'case_id': doc_a.get('case_id')
        },
        'doc_b': {
            'id': doc_b['id'],
            'filename': doc_b['filename'],
            'category': doc_b.get('category'),
            'case_id': doc_b.get('case_id')
        },
        'total_comparisons': total_comparisons,
        'matches_count': matches_count,
        'conflicts_count': conflicts_count,
        'mismatches_count': mismatches_count,
        'discrepancies_count': conflicts_count + mismatches_count,
        'verdict': verdict,
        'risk_score': risk_score,
        'alignment_matrix': alignment_matrix,
        'discrepancies': [m for m in alignment_matrix if m['status'] in ('Conflict', 'Mismatch', 'Duplicate')],
        'compared_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# =====================================================================
# 2. Case-Wide Multi-Document Comparison
# =====================================================================

def compare_case_documents(case_id, user="System"):
    """
    Compares all documents assigned to a given case.
    Detects cross-document monetary variances, date collisions, and duplicate identifiers.
    """
    docs = get_all_documents(case_id=case_id)
    if len(docs) < 2:
        return {
            'success': True,
            'case_id': case_id,
            'message': f"Case has {len(docs)} document(s). At least 2 documents are required for cross-comparison.",
            'comparisons_count': 0,
            'comparison_count': 0,
            'discrepancies': []
        }

    all_discrepancies = []
    comparisons_run = 0

    # Pairwise loop across documents
    n = len(docs)
    for i in range(n):
        for j in range(i + 1, n):
            doc_a = docs[i]
            doc_b = docs[j]
            cmp_res = compare_two_documents(doc_a['id'], doc_b['id'], user=user)
            if cmp_res.get('success'):
                comparisons_run += 1
                for item in cmp_res.get('alignment_matrix', []):
                    if item.get('status') in ('Conflict', 'Mismatch', 'Duplicate'):
                        all_discrepancies.append({
                            'doc_a_id': doc_a['id'],
                            'doc_a_filename': doc_a['filename'],
                            'doc_b_id': doc_b['id'],
                            'doc_b_filename': doc_b['filename'],
                            'attribute': item['attribute'],
                            'field': item['attribute'],
                            'val_a': item['val_a'],
                            'val_b': item['val_b'],
                            'page_a': item.get('page_a', 1),
                            'page_b': item.get('page_b', 1),
                            'verdict': item['verdict'],
                            'status': item['status'],
                            'explanation': item['explanation'],
                            'message': item['explanation']
                        })

    return {
        'success': True,
        'case_id': case_id,
        'documents_count': len(docs),
        'comparisons_run': comparisons_run,
        'discrepancies_count': len(all_discrepancies),
        'discrepancies': all_discrepancies
    }

# =====================================================================
# 3. Evidence Provenance Graph Mapping
# =====================================================================

def get_evidence_provenance_nodes(case_id=None):
    """
    Constructs transparent evidence graph nodes linking:
    Investigation Case -> Sourced Documents -> Forensic Findings -> Page BBoxes.
    """
    query = """
        SELECT f.*, d.filename AS doc_filename, d.file_type AS doc_type, c.title AS case_title
        FROM findings f
        LEFT JOIN documents d ON f.document_id = d.id
        LEFT JOIN cases c ON f.case_id = c.id
        WHERE 1=1
    """
    args = []
    if case_id:
        query += " AND f.case_id = ?"
        args.append(case_id)

    query += " ORDER BY f.created_at DESC"
    findings = query_db(query, args)

    nodes = []
    for idx, f in enumerate(findings):
        coords_str = f['coordinates']
        coords_display = ""
        if coords_str:
            try:
                coords = json.loads(coords_str) if isinstance(coords_str, str) else coords_str
                if isinstance(coords, list) and len(coords) == 4:
                    coords_display = f"Box [X0:{coords[0]}, Y0:{coords[1]}, X1:{coords[2]}, Y1:{coords[3]}]"
            except Exception:
                coords_display = str(coords_str)

        node = {
            'node_id': f"EV-NODE #{idx + 1:03d}",
            'finding_id': f['id'],
            'rule_id': f.get('rule_id') or 'RULE-FORENSIC',
            'title': f['title'],
            'severity': f['severity'],
            'status': f['status'],
            'category': f['category'],
            'document_id': f['document_id'],
            'document_filename': f['doc_filename'] or 'Unknown Document',
            'case_id': f['case_id'],
            'case_title': f['case_title'] or 'General Vault',
            'page_number': f['page_number'] or 1,
            'coordinates': coords_display,
            'evidence': f.get('evidence'),
            'description': f['description']
        }
        nodes.append(node)

    return nodes
