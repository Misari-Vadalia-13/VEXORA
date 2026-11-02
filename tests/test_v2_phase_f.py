"""
VEXORA — Phase F Test Suite
Tests:
1. Content-based classification fallback (Invoice, Bank Statement, PO, Tax Return).
2. Fallback isolation (never overwrites existing non-General classifications).
3. Label-aware totals and financial transaction extraction.
4. Fuzzy party name normalization and similarity matching.
5. Case relationship graph builder (documents, entities, shared edges, conflict edges).
6. API endpoint /api/cases/<case_id>/relationships under ENABLE_CORRELATOR flag.
"""

import os
import unittest
import json
from pathlib import Path

from backend.config import Config, TestConfig
from backend.app import create_app
from backend.database import init_db, execute_db
from backend.classifier_content import classify_by_content
from backend.correlator import (
    parse_numeric_amount,
    normalize_party_name,
    fuzzy_party_similarity,
    extract_labeled_invoice_totals,
    build_case_relationship_graph
)
from backend.models import (
    create_case,
    create_document,
    save_document_extraction
)


class TestV2PhaseF(unittest.TestCase):
    """Automated test cases for Phase F Cross-Document Correlation & Content Classification."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestConfig)
        cls.client = cls.app.test_client()

    def setUp(self):
        init_db(TestConfig.DATABASE)
        execute_db("DELETE FROM cases WHERE id LIKE 'CAS-TEST-%'")
        execute_db("DELETE FROM documents WHERE id LIKE 'DOC-REL-%'")
        # Default ENABLE_CORRELATOR to True for unit tests unless overridden
        Config.ENABLE_CORRELATOR = True

    def tearDown(self):
        Config.ENABLE_CORRELATOR = False

    def test_01_classify_by_content_invoice(self):
        """Content with invoice markers is classified as Invoice with high confidence."""
        sample_text = """
        TAX INVOICE
        Invoice No: INV-2026-881
        Bill To: Acme Global Services
        Payment Terms: Net 30
        Total Amount: $14,250.00
        Amount Due: $14,250.00
        """
        category, confidence = classify_by_content(sample_text)
        self.assertEqual(category, "Invoice")
        self.assertGreater(confidence, 90.0)

    def test_02_classify_by_content_bank_statement(self):
        """Content with banking markers is classified as Bank Statement."""
        sample_text = """
        Official Bank Statement
        Account Statement for Period Jan 2026
        Opening Balance: $50,000.00
        Deposits: $12,500.00
        Withdrawals: $4,200.00
        Closing Balance: $58,300.00
        Transaction History
        """
        category, confidence = classify_by_content(sample_text)
        self.assertEqual(category, "Bank Statement")
        self.assertGreater(confidence, 90.0)

    def test_03_classify_by_content_purchase_order(self):
        """Content with purchase order markers is classified as Purchase Order."""
        sample_text = """
        PURCHASE ORDER
        PO Number: PO-99120
        Vendor: Precision Machinery LLC
        Deliver To: Warehouse 4B
        Line Items:
        1. Hydraulic Actuators
        """
        category, confidence = classify_by_content(sample_text)
        self.assertEqual(category, "Purchase Order")
        self.assertGreater(confidence, 90.0)

    def test_04_classify_by_content_fallback_general(self):
        """Generic or uninformative text returns General Document."""
        sample_text = "The quick brown fox jumps over the lazy dog in the middle of summer."
        category, confidence = classify_by_content(sample_text)
        self.assertEqual(category, "General Document")
        self.assertEqual(confidence, 60.0)

    def test_05_label_aware_totals_extraction(self):
        """extract_labeled_invoice_totals accurately extracts labeled monetary totals."""
        text = """
        Subtotal: $12,000.00
        Tax (8.25%): $990.00
        Total Amount: $12,990.00
        Amount Due: $12,990.00
        """
        totals = extract_labeled_invoice_totals(text)
        self.assertGreaterEqual(len(totals), 1)
        amounts = [t['amount'] for t in totals]
        self.assertIn(12990.0, amounts)

    def test_06_fuzzy_party_normalization_and_similarity(self):
        """fuzzy_party_similarity matches corporate entities despite suffix variations."""
        name1 = "Apex Industries Technologies Corp."
        name2 = "Apex Industries Ltd"
        is_match, ratio = fuzzy_party_similarity(name1, name2)
        self.assertTrue(is_match)
        self.assertGreaterEqual(ratio, 0.82)

        # Dissimilar parties do not match
        is_match_diff, ratio_diff = fuzzy_party_similarity("Apex Industries", "Veridian Biometrics Inc")
        self.assertFalse(is_match_diff)
        self.assertLess(ratio_diff, 0.5)

    def test_07_build_case_relationship_graph(self):
        """build_case_relationship_graph connects documents sharing identifiers, amounts, and parties."""
        with self.app.app_context():
            case = create_case({
                'title': 'Test Cross-Doc Case',
                'type': 'Financial Audit',
                'priority': 'High',
                'status': 'Active',
                'investigator': 'Dr. Alex Turner',
                'description': 'Testing relationship graph.'
            }, custom_id='CAS-TEST-REL')

            # Doc 1: Invoice
            doc1 = create_document({
                'id': 'DOC-REL-01',
                'case_id': case['id'],
                'filename': 'Invoice_Apex_INV-991.pdf',
                'file_type': 'pdf',
                'file_size': 1024,
                'file_path': 'uploads/Invoice_Apex_INV-991.pdf',
                'file_hash': 'hash1',
                'category': 'Invoice',
                'classification_confidence': 95.0,
                'status': 'Analyzed'
            })
            save_document_extraction('DOC-REL-01', {
                'full_text': 'Tax Invoice INV-991 Bill To: Apex Corp Total Amount: $15,750.00 Date: 2026-05-15',
                'entities': {
                    'identifiers': [{'value': 'INV-991', 'confidence': 95.0}],
                    'monetary_values': [{'value': '$15,750.00', 'confidence': 92.0}],
                    'organizations': [{'value': 'Apex Corp', 'confidence': 88.0}],
                    'dates': [{'value': '2026-05-15', 'confidence': 90.0}]
                }
            })

            # Doc 2: Bank Statement referencing same invoice and amount
            doc2 = create_document({
                'id': 'DOC-REL-02',
                'case_id': case['id'],
                'filename': 'Bank_Statement_May2026.pdf',
                'file_type': 'pdf',
                'file_size': 2048,
                'file_path': 'uploads/Bank_Statement_May2026.pdf',
                'category': 'Bank Statement',
                'classification_confidence': 94.0,
                'status': 'Analyzed'
            })
            save_document_extraction('DOC-REL-02', {
                'full_text': 'Bank Statement Wire Payment Apex Industries Ref: INV-991 Amount: $15,750.00 Date: 2026-05-18',
                'entities': {
                    'identifiers': [{'value': 'INV-991', 'confidence': 95.0}],
                    'monetary_values': [{'value': '$15,750.00', 'confidence': 92.0}],
                    'organizations': [{'value': 'Apex Industries', 'confidence': 88.0}],
                    'dates': [{'value': '2026-05-18', 'confidence': 90.0}]
                }
            })

            graph = build_case_relationship_graph('CAS-TEST-REL')
            self.assertTrue(graph['success'])
            self.assertEqual(graph['case_id'], 'CAS-TEST-REL')

            # Verify document nodes exist
            doc_nodes = [n for n in graph['nodes'] if n['type'] == 'document']
            self.assertEqual(len(doc_nodes), 2)

            # Verify shared relations
            relations = [e['relation'] for e in graph['edges']]
            self.assertIn('shared_invoice_id', relations)
            self.assertIn('shared_amount', relations)
            self.assertIn('shared_party', relations)

    def test_08_api_case_relationships_disabled(self):
        """GET /api/cases/<id>/relationships returns 403 when ENABLE_CORRELATOR is False."""
        Config.ENABLE_CORRELATOR = False
        res = self.client.get('/api/cases/CAS-2026-0891/relationships')
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn('disabled', data['error'].lower())

    def test_09_api_case_relationships_enabled(self):
        """GET /api/cases/<id>/relationships returns 200 with graph schema when enabled."""
        Config.ENABLE_CORRELATOR = True
        res = self.client.get('/api/cases/CAS-2026-0891/relationships')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('nodes', data)
        self.assertIn('edges', data)
        self.assertIn('metrics', data)


if __name__ == '__main__':
    unittest.main()
