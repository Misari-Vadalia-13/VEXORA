"""
VEXORA — Cross-Document Correlation & Relationship Graph Engine (Phase F)
Implements:
1. Label-aware field matching (invoice totals, amount due, grand total).
2. Bank statement transaction and invoice payment matching.
3. Normalized fuzzy party similarity comparison using difflib.
4. Chronological date sequence conflict discovery.
5. Case relationship graph builder (nodes: documents, entities; edges: shared relations and conflicts).
Protected by feature flag: ENABLE_CORRELATOR.
"""

import os
import re
import json
import difflib
from datetime import datetime
from pathlib import Path

from backend.config import Config
from backend.models import (
    get_document_by_id,
    get_all_documents,
    query_db
)
from backend.ner import PATTERNS

# Regex patterns for label-aware financial totals
LABEL_TOTAL_PATTERNS = [
    r'(?i)(?:grand\s+total|total\s+amount|amount\s+due|balance\s+due|net\s+payable|invoice\s+total|total)[\s:]*([\$€£₹]?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
    r'(?i)(?:total|balance)[\s:]*([\$€£₹]?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
]

CORPORATE_SUFFIXES = {
    'inc', 'incorporated', 'llc', 'ltd', 'limited', 'corp', 'corporation',
    'gmbh', 'co', 'company', 'group', 'holdings', 'technologies', 'services', 'systems',
    'industries', 'enterprises', 'solutions', 'international', 'global', 'ventures', 'associates',
    'pvt', 'private', 'plc', 'llp', 'sa', 'ag', 'pte', 'bv', 'srl', 'sarl', 'nv', 'spa'
}


def parse_numeric_amount(val_str):
    """Converts a currency string into a clean float value."""
    if not val_str:
        return None
    cleaned = re.sub(r'[^\d.]', '', str(val_str))
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_party_name(name):
    """
    Strips corporate suffixes, compound legal forms (e.g. 'Pvt Ltd'), and punctuation
    for robust cross-document party name normalization.
    """
    if not name:
        return ""
    clean = re.sub(r'[^\w\s]', ' ', str(name).lower())
    clean = re.sub(r'\b(pvt\s+ltd|private\s+limited|pte\s+ltd|co\s+ltd|gmbh\s+&\s+co\s+kg)\b', '', clean)
    words = clean.split()
    meaningful = [w for w in words if w and w not in CORPORATE_SUFFIXES]
    return " ".join(meaningful) if meaningful else " ".join(words)


def fuzzy_party_similarity(name_a, name_b):
    """
    Computes SequenceMatcher ratio between two normalized party names.
    Returns (is_match, similarity_ratio).
    """
    norm_a = normalize_party_name(name_a)
    norm_b = normalize_party_name(name_b)
    if not norm_a or not norm_b:
        return (False, 0.0)
    if norm_a == norm_b:
        return (True, 1.0)
    words_a = set(norm_a.split())
    words_b = set(norm_b.split())
    if words_a and words_b and (words_a.issubset(words_b) or words_b.issubset(words_a)):
        overlap = len(words_a.intersection(words_b)) / max(len(words_a), len(words_b))
        if overlap >= 0.5:
            return (True, round(max(0.85, overlap), 2))
    ratio = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()
    return (ratio >= 0.80, round(ratio, 2))


def extract_labeled_invoice_totals(text):
    """
    Scans document text for monetary amounts explicitly labeled as totals or amounts due.
    Returns list of dicts: [{'label': 'Total Amount', 'amount': 15750.0, 'raw': '$15,750.00', 'context': '...'}]
    """
    if not text:
        return []
    results = []
    lines = text.split('\n')
    for line_idx, line in enumerate(lines):
        line_clean = line.strip()
        for pat in LABEL_TOTAL_PATTERNS:
            m = re.search(pat, line_clean)
            if m:
                raw_amt = m.group(1).strip()
                amt_num = parse_numeric_amount(raw_amt)
                if amt_num and amt_num > 0:
                    results.append({
                        'raw': raw_amt,
                        'amount': amt_num,
                        'line_number': line_idx + 1,
                        'context': line_clean[:120]
                    })
                break
    return results


def extract_bank_transactions(text):
    """
    Extracts debit/payment transactions from bank statements with their reference notes.
    """
    if not text:
        return []
    results = []
    lines = text.split('\n')
    for line_idx, line in enumerate(lines):
        line_clean = line.strip()
        # Look for invoice references (e.g. INV-001) or payment notes
        id_match = re.search(PATTERNS['identifier'], line_clean)
        money_match = re.search(PATTERNS['monetary'], line_clean)
        if money_match:
            raw_amt = money_match.group(0).strip()
            amt_num = parse_numeric_amount(raw_amt)
            if amt_num:
                results.append({
                    'raw': raw_amt,
                    'amount': amt_num,
                    'reference_id': id_match.group(0).strip() if id_match else None,
                    'line_number': line_idx + 1,
                    'context': line_clean[:120]
                })
    return results


def parse_date_robust(date_str):
    """Attempts standard date parsing across common ISO and business formats."""
    if not date_str:
        return None
    cleaned = date_str.strip().strip(',.;:')
    formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y",
        "%d-%m-%Y", "%m-%d-%Y", "%B %d, %Y", "%b %d, %Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def build_case_relationship_graph(case_id):
    """
    Constructs the forensic relationship graph for a case.
    Nodes: Ingested documents and shared forensic entities.
    Edges: Relationships (shared_invoice_id, shared_amount, shared_party, date_conflict).
    Each edge includes verbatim evidence text and page references.
    """
    docs = get_all_documents(case_id=case_id)
    if not docs:
        return {
            'success': True,
            'case_id': case_id,
            'nodes': [],
            'edges': [],
            'metrics': {'document_nodes': 0, 'entity_nodes': 0, 'total_edges': 0}
        }

    nodes = []
    edges = []
    seen_nodes = set()
    seen_edges = set()

    # 1. Register Document Nodes
    parsed_docs = []
    for d in docs:
        doc_node_id = f"doc_{d['id']}"
        nodes.append({
            'id': doc_node_id,
            'label': d['filename'],
            'type': 'document',
            'category': d.get('category') or 'General Document',
            'document_id': d['id'],
            'status': d.get('status') or 'Pending'
        })
        seen_nodes.add(doc_node_id)

        # Parse extracted entities and text
        ext_data = {}
        if d.get('extracted_data'):
            try:
                ext_data = json.loads(d['extracted_data']) if isinstance(d['extracted_data'], str) else d['extracted_data']
            except Exception:
                ext_data = {}

        full_text = d.get('extracted_text') or ext_data.get('full_text') or ''
        entities = ext_data.get('entities') or {}

        parsed_docs.append({
            'meta': d,
            'node_id': doc_node_id,
            'full_text': full_text,
            'entities': entities,
            'labeled_totals': extract_labeled_invoice_totals(full_text),
            'bank_txns': extract_bank_transactions(full_text)
        })

    # Helper to add entity nodes safely
    def add_entity_node(ent_id, label, entity_type):
        if ent_id not in seen_nodes:
            seen_nodes.add(ent_id)
            nodes.append({
                'id': ent_id,
                'label': label,
                'type': 'entity',
                'entity_type': entity_type
            })

    # Helper to add edges safely
    def add_edge(source, target, relation, evidence, page=1, confidence=1.0):
        edge_key = (source, target, relation)
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            edges.append({
                'source': source,
                'target': target,
                'relation': relation,
                'evidence': evidence,
                'page': page,
                'confidence': confidence
            })

    # 2. Extract Cross-Document Shared Entities & Correlations
    n_docs = len(parsed_docs)
    for i in range(n_docs):
        for j in range(i + 1, n_docs):
            doc_a = parsed_docs[i]
            doc_b = parsed_docs[j]

            # A. Shared Invoice / Reference Identifiers
            ids_a = {item['value'].strip() for item in doc_a['entities'].get('identifiers', []) if item.get('value')}
            ids_b = {item['value'].strip() for item in doc_b['entities'].get('identifiers', []) if item.get('value')}
            shared_ids = ids_a.intersection(ids_b)

            for shared_id in shared_ids:
                ent_node_id = f"ent_id_{re.sub(r'[^a-zA-Z0-9_]', '_', shared_id)}"
                add_entity_node(ent_node_id, shared_id, 'identifier')
                add_edge(doc_a['node_id'], ent_node_id, 'shared_invoice_id', f"Referenced in {doc_a['meta']['filename']}: '{shared_id}'")
                add_edge(doc_b['node_id'], ent_node_id, 'shared_invoice_id', f"Referenced in {doc_b['meta']['filename']}: '{shared_id}'")

            # B. Shared Financial Amounts & Labeled Totals
            totals_a = [t['amount'] for t in doc_a['labeled_totals']] or [parse_numeric_amount(m['value']) for m in doc_a['entities'].get('monetary_values', []) if parse_numeric_amount(m['value'])]
            totals_b = [t['amount'] for t in doc_b['labeled_totals']] or [parse_numeric_amount(m['value']) for m in doc_b['entities'].get('monetary_values', []) if parse_numeric_amount(m['value'])]

            for amt_a in totals_a:
                for amt_b in totals_b:
                    if amt_a and amt_b and abs(amt_a - amt_b) < 0.01:
                        amt_label = f"${amt_a:,.2f}"
                        ent_node_id = f"ent_amt_{int(amt_a * 100)}"
                        add_entity_node(ent_node_id, amt_label, 'monetary_value')
                        add_edge(doc_a['node_id'], ent_node_id, 'shared_amount', f"Total {amt_label} matches across documents")
                        add_edge(doc_b['node_id'], ent_node_id, 'shared_amount', f"Total {amt_label} matches across documents")

            # C. Shared / Fuzzy Counterparty & Organization Matching
            orgs_a = [o['value'] for o in doc_a['entities'].get('organizations', []) if o.get('value')]
            orgs_b = [o['value'] for o in doc_b['entities'].get('organizations', []) if o.get('value')]

            for o_a in orgs_a:
                for o_b in orgs_b:
                    is_match, score = fuzzy_party_similarity(o_a, o_b)
                    if is_match:
                        canon_label = o_a if len(o_a) >= len(o_b) else o_b
                        ent_node_id = f"ent_party_{re.sub(r'[^a-zA-Z0-9_]', '_', canon_label)}"
                        add_entity_node(ent_node_id, canon_label, 'organization')
                        add_edge(doc_a['node_id'], ent_node_id, 'shared_party', f"Party '{o_a}' (similarity: {score})", confidence=score)
                        add_edge(doc_b['node_id'], ent_node_id, 'shared_party', f"Party '{o_b}' (similarity: {score})", confidence=score)

            # D. Bank Statement Transaction to Invoice Matching
            if 'bank' in (doc_b['meta'].get('category') or '').lower() and 'invoice' in (doc_a['meta'].get('category') or '').lower():
                for txn in doc_b['bank_txns']:
                    if txn['reference_id'] and txn['reference_id'] in ids_a:
                        add_edge(
                            doc_b['node_id'],
                            doc_a['node_id'],
                            'bank_payment_match',
                            f"Bank transaction '{txn['context']}' matches Invoice '{txn['reference_id']}'",
                            page=txn.get('line_number', 1)
                        )

            # E. Near-Duplicate Document Variant (Jaccard Token Overlap)
            try:
                from backend.comparator import calculate_jaccard_token_similarity
                jaccard_sim = calculate_jaccard_token_similarity(doc_a['full_text'], doc_b['full_text'])
                if jaccard_sim >= 0.78 and doc_a['meta'].get('file_hash') != doc_b['meta'].get('file_hash'):
                    add_edge(
                        doc_a['node_id'],
                        doc_b['node_id'],
                        'near_duplicate_variant',
                        f"Near-duplicate template: {round(jaccard_sim * 100, 1)}% token overlap",
                        confidence=round(jaccard_sim, 2)
                    )
            except Exception:
                pass

            # F. Chronological Date Conflicts
            dates_a = [parse_date_robust(d['value']) for d in doc_a['entities'].get('dates', []) if parse_date_robust(d['value'])]
            dates_b = [parse_date_robust(d['value']) for d in doc_b['entities'].get('dates', []) if parse_date_robust(d['value'])]

            # If Invoice date occurs after settlement or payment date in Bank Statement
            if dates_a and dates_b:
                earliest_b = min(dates_b)
                latest_a = max(dates_a)
                if 'invoice' in (doc_a['meta'].get('category') or '').lower() and 'bank' in (doc_b['meta'].get('category') or '').lower():
                    if latest_a > earliest_b:
                        add_edge(
                            doc_a['node_id'],
                            doc_b['node_id'],
                            'date_conflict',
                            f"Chronological Anomaly: Invoice date ({latest_a.strftime('%Y-%m-%d')}) occurs AFTER Bank Statement date ({earliest_b.strftime('%Y-%m-%d')})"
                        )

    doc_node_count = sum(1 for n in nodes if n['type'] == 'document')
    entity_node_count = sum(1 for n in nodes if n['type'] == 'entity')

    return {
        'success': True,
        'case_id': case_id,
        'nodes': nodes,
        'edges': edges,
        'metrics': {
            'document_nodes': doc_node_count,
            'entity_nodes': entity_node_count,
            'total_edges': len(edges)
        }
    }


def build_case_timeline(case_id):
    """
    Synthesizes an ordered, cross-document chronological event timeline for all
    documents in a case. Correlates business sequence logic:
    - Purchase Order (PO) authorization
    - Commercial Invoice generation
    - Shipping / Delivery notes
    - Bank Statement / Payment settlement
    - Contract execution

    Identifies temporal sequence anomalies:
    1. Invoice issued before Purchase Order was authorized.
    2. Bank payment / settlement cleared before Invoice was issued.
    """
    docs = get_all_documents(case_id=case_id)
    if not docs:
        return {
            'success': True,
            'case_id': case_id,
            'events': [],
            'anomalies': [],
            'summary': 'No documents found for timeline synthesis.'
        }

    events = []
    anomalies = []
    doc_data = []

    for d in docs:
        ext = {}
        if d.get('extracted_data'):
            try:
                ext = json.loads(d['extracted_data']) if isinstance(d['extracted_data'], str) else d['extracted_data']
            except Exception:
                ext = {}
        full_text = d.get('extracted_text') or ext.get('full_text') or ''
        entities = ext.get('entities') or {}
        dates = [parse_date_robust(item['value']) for item in entities.get('dates', []) if parse_date_robust(item['value'])]
        totals = extract_labeled_invoice_totals(full_text)
        monetary = [t['amount'] for t in totals] or [parse_numeric_amount(m['value']) for m in entities.get('monetary_values', []) if parse_numeric_amount(m['value'])]
        top_amt = max(monetary) if monetary else None

        cat = (d.get('category') or 'General Document').lower()
        doc_data.append({
            'doc': d,
            'category': d.get('category') or 'General Document',
            'cat_clean': cat,
            'dates': dates,
            'amount': top_amt,
            'full_text': full_text
        })

        if dates:
            primary_date = min(dates)
            event_type = "Document Executed"
            if 'purchase order' in cat or 'po' in cat:
                event_type = "Purchase Order Authorized"
            elif 'invoice' in cat:
                event_type = "Invoice Issued"
            elif 'bank' in cat:
                event_type = "Payment Settled / Statement Recorded"
            elif 'contract' in cat or 'agreement' in cat:
                event_type = "Contract Agreement Executed"

            events.append({
                'date': primary_date.strftime('%Y-%m-%d'),
                'datetime_iso': primary_date.isoformat(),
                'document_id': d['id'],
                'document_name': d['filename'],
                'category': d.get('category') or 'General Document',
                'event_type': event_type,
                'amount': top_amt,
                'description': f"{d['filename']}: {event_type} on {primary_date.strftime('%Y-%m-%d')}" + (f" (Amount: ${top_amt:,.2f})" if top_amt else "")
            })

    # Sort events chronologically
    events.sort(key=lambda e: e['date'])

    # Cross-document sequence anomaly evaluation
    for i in range(len(doc_data)):
        for j in range(i + 1, len(doc_data)):
            d1 = doc_data[i]
            d2 = doc_data[j]
            if not d1['dates'] or not d2['dates']:
                continue

            date1 = min(d1['dates'])
            date2 = min(d2['dates'])

            # Case A: Invoice vs Purchase Order
            if 'invoice' in d1['cat_clean'] and ('purchase order' in d2['cat_clean'] or 'po' in d2['cat_clean']):
                inv_date, po_date = date1, date2
                inv_doc, po_doc = d1['doc'], d2['doc']
            elif 'invoice' in d2['cat_clean'] and ('purchase order' in d1['cat_clean'] or 'po' in d1['cat_clean']):
                inv_date, po_date = date2, date1
                inv_doc, po_doc = d2['doc'], d1['doc']
            else:
                inv_date, po_date = None, None

            if inv_date and po_date and inv_date < po_date:
                anomalies.append({
                    'type': 'pre_dated_invoice',
                    'severity': 'High',
                    'title': 'Invoice Predates Purchase Order Authorization',
                    'description': (
                        f"Invoice '{inv_doc['filename']}' ({inv_date.strftime('%Y-%m-%d')}) was issued before "
                        f"Purchase Order '{po_doc['filename']}' ({po_date.strftime('%Y-%m-%d')}) was authorized. "
                        f"Violates procurement control hierarchy."
                    ),
                    'document_a': inv_doc['filename'],
                    'document_b': po_doc['filename'],
                    'date_a': inv_date.strftime('%Y-%m-%d'),
                    'date_b': po_date.strftime('%Y-%m-%d')
                })

            # Case B: Bank Statement vs Invoice
            if 'bank' in d1['cat_clean'] and 'invoice' in d2['cat_clean']:
                bank_date, inv_date2 = date1, date2
                bank_doc, inv_doc2 = d1['doc'], d2['doc']
            elif 'bank' in d2['cat_clean'] and 'invoice' in d1['cat_clean']:
                bank_date, inv_date2 = date2, date1
                bank_doc, inv_doc2 = d2['doc'], d1['doc']
            else:
                bank_date, inv_date2 = None, None

            if bank_date and inv_date2 and bank_date < inv_date2:
                anomalies.append({
                    'type': 'pre_invoice_payment',
                    'severity': 'High',
                    'title': 'Bank Settlement Predates Invoice Issuance',
                    'description': (
                        f"Bank record '{bank_doc['filename']}' ({bank_date.strftime('%Y-%m-%d')}) settled payment "
                        f"prior to the issuance of Invoice '{inv_doc2['filename']}' ({inv_date2.strftime('%Y-%m-%d')})."
                    ),
                    'document_a': bank_doc['filename'],
                    'document_b': inv_doc2['filename'],
                    'date_a': bank_date.strftime('%Y-%m-%d'),
                    'date_b': inv_date2.strftime('%Y-%m-%d')
                })

    summary = f"Synthesized {len(events)} timeline events across {len(docs)} documents; {len(anomalies)} temporal anomalies discovered."
    return {
        'success': True,
        'case_id': case_id,
        'events': events,
        'anomalies': anomalies,
        'summary': summary
    }
