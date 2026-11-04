"""
VEXORA — Unit Tests for Cross-Document Intelligence (Stage 5)
Verifies:
1. Enhanced entity normalization (Pvt Ltd, Private Limited, AG, SA, BV, NV, multi-word suffixes).
2. Jaccard token similarity calculation and near-duplicate document variant detection.
3. Chronological timeline synthesis across procurement documents (POs, Invoices, Bank Statements).
4. Sequence anomaly detection: pre-dated invoices and pre-invoice payments.
5. API endpoint GET /api/cases/<case_id>/timeline.
"""

import json
import os
import shutil
import tempfile
import unittest

from backend.app import create_app
from backend.config import Config, TestConfig
from backend.database import init_db
from backend.models import create_case, create_document, save_document_extraction
from backend.comparator import (
    calculate_jaccard_token_similarity,
    compare_two_documents
)
from backend.correlator import (
    CORPORATE_SUFFIXES,
    normalize_party_name,
    fuzzy_party_similarity,
    build_case_timeline,
    build_case_relationship_graph
)


class TestCrossDocumentIntelligence(unittest.TestCase):
    """Test suite for Stage 5 Cross-Document Intelligence enhancements."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="vexora_test_crossdoc_")
        cls.test_db = os.path.join(cls.test_dir, "test.db")
        cls.uploads_dir = os.path.join(cls.test_dir, "uploads")
        cls.reports_dir = os.path.join(cls.test_dir, "reports")
        os.makedirs(cls.uploads_dir, exist_ok=True)
        os.makedirs(cls.reports_dir, exist_ok=True)

        class CustomConfig(TestConfig):
            DATABASE = cls.test_db
            UPLOAD_FOLDER = cls.uploads_dir
            REPORTS_FOLDER = cls.reports_dir
            TESTING = True
            ENABLE_CORRELATOR = True

        cls.app = create_app(CustomConfig)
        with cls.app.app_context():
            init_db(cls.test_db)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_party_normalization_compound_and_international_suffixes(self):
        """Verifies party normalization strips multi-word and international corporate suffixes."""
        # Multi-word suffix phrases
        norm1 = normalize_party_name("Apex Logistics Pvt Ltd")
        norm2 = normalize_party_name("Apex Logistics Private Limited")
        self.assertEqual(norm1, norm2)
        self.assertEqual(norm1, "apex logistics")

        # Singapore / British Commonwealth designations
        norm3 = normalize_party_name("Zenith Global Pte Ltd")
        self.assertEqual(norm3, "zenith")

        # European suffixes (AG, SA, BV)
        self.assertEqual(normalize_party_name("Novartis AG"), "novartis")
        self.assertEqual(normalize_party_name("Renault SA"), "renault")
        self.assertEqual(normalize_party_name("Philips BV"), "philips")

        # Fuzzy matching equivalence
        is_match, ratio = fuzzy_party_similarity("Vexora Analytics Pvt Ltd", "Vexora Analytics Private Limited")
        self.assertTrue(is_match)
        self.assertEqual(ratio, 1.0)

    def test_02_jaccard_token_similarity_clean_vs_cloned(self):
        """Verifies Jaccard token similarity accurately distinguishes cloned templates from distinct documents."""
        text_a = """
        Commercial Invoice #INV-2026-101
        Date: January 15, 2026
        Bill To: Orion Enterprises Ltd
        Description: Enterprise Cloud Migration Consulting Services
        Hourly Rate: $250.00 | Hours: 120
        Subtotal: $30,000.00 | Tax: $2,400.00
        Total Amount: $32,400.00
        Payment Terms: Net 30 Days via Wire Transfer
        """

        # Cloned template with minor value changes
        text_b = """
        Commercial Invoice #INV-2026-101
        Date: January 18, 2026
        Bill To: Orion Enterprises Ltd
        Description: Enterprise Cloud Migration Consulting Services
        Hourly Rate: $250.00 | Hours: 140
        Subtotal: $35,000.00 | Tax: $2,800.00
        Total Amount: $37,800.00
        Payment Terms: Net 30 Days via Wire Transfer
        """

        # Completely unrelated bank statement
        text_unrelated = """
        Official Banking Statement
        Account No: 9876-5432-10
        Month: August 2025
        Atm Withdrawal: $400.00
        Direct Deposit Payroll: $5,200.00
        Utility Gas Payment: $115.50
        Ending Available Balance: $14,920.00
        """

        jaccard_cloned = calculate_jaccard_token_similarity(text_a, text_b)
        jaccard_diff = calculate_jaccard_token_similarity(text_a, text_unrelated)

        self.assertGreaterEqual(jaccard_cloned, 0.78)
        self.assertLess(jaccard_diff, 0.20)

    def test_03_near_duplicate_detection_in_comparator(self):
        """Verifies compare_two_documents flags near-duplicate document variants when Jaccard >= 0.78."""
        with self.app.app_context():
            case = create_case({
                'title': 'Near Duplicate Case',
                'type': 'Procurement Fraud',
                'priority': 'High',
                'status': 'Active',
                'investigator': 'Dr. Turner',
                'description': 'Near duplicate testing case.'
            })

            text_base = "Standard Master Supply Agreement between Acme Corp and Veridian LLC totaling $50,000.00."
            text_clone = "Standard Master Supply Agreement between Acme Corp and Veridian LLC totaling $65,000.00."

            create_document({
                'id': 'DOC-ND-01',
                'case_id': case['id'],
                'filename': 'Contract_Agreement_V1.pdf',
                'file_type': 'pdf',
                'file_size': 2048,
                'file_path': 'uploads/doc1.pdf',
                'file_hash': 'hash_aaa_111',
                'category': 'Contract'
            })
            save_document_extraction('DOC-ND-01', {'full_text': text_base, 'entities': {}})

            create_document({
                'id': 'DOC-ND-02',
                'case_id': case['id'],
                'filename': 'Contract_Agreement_V2.pdf',
                'file_type': 'pdf',
                'file_size': 2048,
                'file_path': 'uploads/doc2.pdf',
                'file_hash': 'hash_bbb_222',
                'category': 'Contract'
            })
            save_document_extraction('DOC-ND-02', {'full_text': text_clone, 'entities': {}})

            res = compare_two_documents('DOC-ND-01', 'DOC-ND-02')
            self.assertTrue(res['success'])
            matrix = res['alignment_matrix']
            near_dup_row = next((r for r in matrix if r['attribute'] == 'Document Content Near-Duplicate'), None)
            self.assertIsNotNone(near_dup_row)
            self.assertEqual(near_dup_row['status'], 'Conflict')
            self.assertIn("Near-Duplicate Document Variant", near_dup_row['verdict'])

    def test_04_chronological_timeline_synthesis_and_anomalies(self):
        """Verifies build_case_timeline sorts events and detects sequence order violations."""
        with self.app.app_context():
            case = create_case({
                'title': 'Timeline Anomaly Case',
                'type': 'Financial Audit',
                'priority': 'High',
                'status': 'Active',
                'investigator': 'Dr. Turner',
                'description': 'Testing timeline anomalies.'
            })

            # Document 1: Purchase Order dated 2026-02-15
            po_text = "Purchase Order PO-7789 dated 2026-02-15 for Industrial Turbines totaling $120,000.00."
            create_document({
                'id': 'DOC-TL-PO',
                'case_id': case['id'],
                'filename': 'PO_7789.pdf',
                'file_type': 'pdf',
                'file_size': 1024,
                'file_path': 'uploads/po.pdf',
                'file_hash': 'h_po',
                'category': 'Purchase Order'
            })
            save_document_extraction('DOC-TL-PO', {
                'full_text': po_text,
                'entities': {'dates': [{'value': '2026-02-15'}], 'monetary_values': [{'value': '$120,000.00'}]}
            })

            # Document 2: Invoice PRE-DATED to 2026-02-01 (14 days before PO authorized!)
            inv_text = "Tax Invoice INV-4412 dated 2026-02-01 Total Amount: $120,000.00."
            create_document({
                'id': 'DOC-TL-INV',
                'case_id': case['id'],
                'filename': 'Invoice_4412.pdf',
                'file_type': 'pdf',
                'file_size': 1024,
                'file_path': 'uploads/inv.pdf',
                'file_hash': 'h_inv',
                'category': 'Invoice'
            })
            save_document_extraction('DOC-TL-INV', {
                'full_text': inv_text,
                'entities': {'dates': [{'value': '2026-02-01'}], 'monetary_values': [{'value': '$120,000.00'}]}
            })

            # Document 3: Bank Statement with payment on 2026-02-28
            bank_text = "Bank Statement Period Feb 2026. Settlement: 2026-02-28 Wire Debit $120,000.00."
            create_document({
                'id': 'DOC-TL-BANK',
                'case_id': case['id'],
                'filename': 'Bank_Feb2026.pdf',
                'file_type': 'pdf',
                'file_size': 1024,
                'file_path': 'uploads/bank.pdf',
                'file_hash': 'h_bank',
                'category': 'Bank Statement'
            })
            save_document_extraction('DOC-TL-BANK', {
                'full_text': bank_text,
                'entities': {'dates': [{'value': '2026-02-28'}], 'monetary_values': [{'value': '$120,000.00'}]}
            })

            timeline = build_case_timeline(case['id'])
            self.assertTrue(timeline['success'])
            self.assertEqual(len(timeline['events']), 3)

            # Events must be chronologically ordered (2026-02-01, 2026-02-15, 2026-02-28)
            dates = [e['date'] for e in timeline['events']]
            self.assertEqual(dates, ['2026-02-01', '2026-02-15', '2026-02-28'])

            # Pre-dated invoice anomaly must be detected
            self.assertGreaterEqual(len(timeline['anomalies']), 1)
            anomaly = next((a for a in timeline['anomalies'] if a['type'] == 'pre_dated_invoice'), None)
            self.assertIsNotNone(anomaly)
            self.assertEqual(anomaly['severity'], 'High')
            self.assertIn("Invoice Predates Purchase Order Authorization", anomaly['title'])

    def test_05_api_case_timeline_endpoint(self):
        """Verifies GET /api/cases/<case_id>/timeline returns 200 and structured timeline data."""
        with self.app.app_context():
            case = create_case({
                'title': 'API Timeline Case',
                'type': 'Procurement Audit',
                'priority': 'Medium',
                'status': 'Active',
                'investigator': 'Dr. Turner',
                'description': 'API timeline testing case.'
            })

        resp = self.client.get(f"/api/cases/{case['id']}/timeline")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertIn('events', data)
        self.assertIn('anomalies', data)
        self.assertIn('summary', data)


if __name__ == '__main__':
    unittest.main()
