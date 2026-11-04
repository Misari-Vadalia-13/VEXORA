"""
VEXORA — Automated Document Understanding & Arithmetic Logic Test Suite
Verifies:
1. Extraction and normalization of structured document fields (invoice numbers, dates, financials).
2. Detection of intra-document arithmetic calculation errors (RULE-DOC-001: Subtotal + Tax != Total).
3. Detection of chronological date reversals (RULE-CTX-003 / RULE-DOC-002: Due Date < Issue Date).
4. Detection of conflicting duplicate financial totals (RULE-DOC-004).
5. False positive control on mathematically genuine invoices.
"""

import unittest
from backend.ner import normalize_structured_document_fields
from backend.analyzer import analyze_contextual_rules


class TestDocumentUnderstanding(unittest.TestCase):
    """Test suite for structured entity normalization and intra-document business logic."""

    def test_01_structured_field_normalization(self):
        """Verifies normalization of invoice header, parties, and line items."""
        sample_invoice_text = (
            "COMMERCIAL INVOICE\n"
            "Invoice #: INV-2026-8812\n"
            "Invoice Date: 2026-03-10\n"
            "Payment Due: 2026-04-10\n"
            "Vendor: Apex Global Solutions Inc.\n"
            "Bill To: OmniCorp Logistics LLC\n"
            "Subtotal: $10,000.00\n"
            "Tax (5%): $500.00\n"
            "Grand Total: $10,500.00\n"
        )
        entities = {
            'identifiers': [{'value': 'INV-2026-8812', 'page': 1}],
            'dates': [{'value': '2026-03-10', 'page': 1}, {'value': '2026-04-10', 'page': 1}],
            'organizations': [{'value': 'Apex Global Solutions Inc.', 'page': 1}, {'value': 'OmniCorp Logistics LLC', 'page': 1}],
            'monetary_values': [{'value': '$10,000.00', 'page': 1}, {'value': '$500.00', 'page': 1}, {'value': '$10,500.00', 'page': 1}]
        }

        norm = normalize_structured_document_fields(sample_invoice_text, entities, category="Commercial Invoice")
        self.assertEqual(norm['document_type'], 'invoice')
        self.assertEqual(norm['identifiers'].get('invoice_number'), 'INV-2026-8812')
        self.assertEqual(norm['dates'].get('issue_date'), '2026-03-10')
        self.assertEqual(norm['dates'].get('due_date'), '2026-04-10')
        self.assertEqual(norm['financials']['subtotal'], 10000.0)
        self.assertEqual(norm['financials']['tax_amount'], 500.0)
        self.assertEqual(norm['financials']['grand_total'], 10500.0)
        self.assertTrue(norm['validation_flags']['arithmetic_consistent'])

    def test_02_arithmetic_discrepancy_rule_doc_001(self):
        """Verifies RULE-DOC-001 fires when Subtotal + Tax != Total."""
        tampered_invoice_text = (
            "TAX INVOICE\n"
            "Invoice #: INV-9901\n"
            "Subtotal: $10,000.00\n"
            "Tax: $500.00\n"
            "Grand Total: $12,500.00\n" # Discrepancy of $2,000
        )
        entities = {
            'identifiers': [{'value': 'INV-9901', 'page': 1}],
            'monetary_values': [{'value': '$10,000.00', 'page': 1}, {'value': '$500.00', 'page': 1}, {'value': '$12,500.00', 'page': 1}]
        }

        findings = analyze_contextual_rules("Commercial Invoice", tampered_invoice_text, {'entities': entities})
        rule_ids = [f['rule_id'] for f in findings]
        self.assertIn('RULE-DOC-001', rule_ids)
        doc_001_finding = next(f for f in findings if f['rule_id'] == 'RULE-DOC-001')
        self.assertIn("does not match stated Grand Total", doc_001_finding['description'])
        self.assertEqual(doc_001_finding['severity'], 'Critical')

    def test_03_clean_invoice_no_arithmetic_false_positive(self):
        """Verifies mathematically valid invoice produces zero arithmetic anomaly findings."""
        clean_invoice_text = (
            "TAX INVOICE\n"
            "Invoice #: INV-9902\n"
            "Invoice Date: 2026-02-01\n"
            "Due Date: 2026-02-28\n"
            "Subtotal: $4,500.00\n"
            "Tax: $450.00\n"
            "Grand Total: $4,950.00\n"
        )
        entities = {
            'identifiers': [{'value': 'INV-9902', 'page': 1}],
            'dates': [{'value': '2026-02-01', 'page': 1}, {'value': '2026-02-28', 'page': 1}],
            'organizations': [{'value': 'Apex Corp', 'page': 1}],
            'monetary_values': [{'value': '$4,500.00', 'page': 1}, {'value': '$450.00', 'page': 1}, {'value': '$4,950.00', 'page': 1}]
        }

        findings = analyze_contextual_rules("Commercial Invoice", clean_invoice_text, {'entities': entities})
        rule_ids = [f['rule_id'] for f in findings]
        self.assertNotIn('RULE-DOC-001', rule_ids)
        self.assertNotIn('RULE-DOC-004', rule_ids)

    def test_04_conflicting_duplicate_totals_rule_doc_004(self):
        """Verifies RULE-DOC-004 fires when document contains two conflicting grand totals."""
        conflicting_text = (
            "INVOICE SUMMARY\n"
            "Header Total: $10,000.00\n"
            "Item 1: $8,000.00\n"
            "Footer Balance Total: $14,500.00\n"
        )
        entities = {
            'identifiers': [{'value': 'INV-101', 'page': 1}],
            'monetary_values': [{'value': '$10,000.00', 'page': 1}, {'value': '$14,500.00', 'page': 1}]
        }

        findings = analyze_contextual_rules("Commercial Invoice", conflicting_text, {'entities': entities})
        rule_ids = [f['rule_id'] for f in findings]
        self.assertIn('RULE-DOC-004', rule_ids)
        doc_004_finding = next(f for f in findings if f['rule_id'] == 'RULE-DOC-004')
        self.assertIn("states contradictory grand total figures", doc_004_finding['description'])


    def test_05_chronological_inversion_rule_doc_002(self):
        """Verifies RULE-DOC-002 fires when payment due date precedes invoice issue date."""
        inverted_text = (
            "TAX INVOICE\n"
            "Invoice #: INV-2026-INVERT\n"
            "Invoice Date: 2026-03-15\n"
            "Due Date: 2026-02-15\n"  # Due date 1 month BEFORE invoice date!
            "Subtotal: $1,000.00\n"
            "Tax: $100.00\n"
            "Grand Total: $1,100.00\n"
        )
        entities = {
            'identifiers': [{'value': 'INV-2026-INVERT', 'page': 1}],
            'dates': [{'value': '2026-03-15', 'page': 1}, {'value': '2026-02-15', 'page': 1}],
            'monetary_values': [{'value': '$1,000.00', 'page': 1}, {'value': '$100.00', 'page': 1}, {'value': '$1,100.00', 'page': 1}]
        }
        findings = analyze_contextual_rules("Commercial Invoice", inverted_text, {'entities': entities})
        rule_ids = [f['rule_id'] for f in findings]
        self.assertIn('RULE-DOC-002', rule_ids)
        self.assertIn('RULE-CTX-003', rule_ids)

    def test_06_expired_identification_rule_doc_005(self):
        """Verifies RULE-DOC-005 fires on an expired identification document."""
        expired_id_text = (
            "STATE IDENTIFICATION CARD\n"
            "ID Number: DL-88991122\n"
            "Bearer: Jane Doe\n"
            "Date of Birth: 1988-06-12\n"
            "Issue Date: 2015-05-10\n"
            "Expiration Date: 2021-05-10\n"  # Expired in 2021
        )
        entities = {
            'identifiers': [{'value': 'DL-88991122', 'page': 1}],
            'dates': [{'value': '1988-06-12', 'page': 1}, {'value': '2015-05-10', 'page': 1}, {'value': '2021-05-10', 'page': 1}],
            'persons': [{'value': 'Jane Doe', 'page': 1}]
        }
        findings = analyze_contextual_rules("Identification Card", expired_id_text, {'entities': entities})
        rule_ids = [f['rule_id'] for f in findings]
        self.assertIn('RULE-DOC-005', rule_ids)

    def test_07_valid_identification_clean(self):
        """Verifies a non-expired identification card produces no expiration findings."""
        valid_id_text = (
            "NATIONAL PASSPORT\n"
            "Passport #: P98765432\n"
            "Bearer: John Smith\n"
            "Date of Birth: 1992-08-20\n"
            "Valid Thru: 2032-12-31\n"  # Valid in future
        )
        entities = {
            'identifiers': [{'value': 'P98765432', 'page': 1}],
            'dates': [{'value': '1992-08-20', 'page': 1}, {'value': '2032-12-31', 'page': 1}],
            'persons': [{'value': 'John Smith', 'page': 1}]
        }
        findings = analyze_contextual_rules("Passport", valid_id_text, {'entities': entities})
        rule_ids = [f['rule_id'] for f in findings]
        self.assertNotIn('RULE-DOC-005', rule_ids)


if __name__ == '__main__':
    unittest.main()

