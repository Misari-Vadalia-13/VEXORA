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
    'industries', 'enterprises', 'solutions', 'international', 'global', 'ventures', 'associates'
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
    """Strips corporate suffixes and punctuation for robust fuzzy matching."""
    if not name:
        return ""
    words = [re.sub(r'[^\w]', '', w.lower()) for w in str(name).split()]
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

            # E. Chronological Date Conflicts
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
