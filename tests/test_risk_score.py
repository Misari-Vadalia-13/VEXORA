"""
VEXORA — Phase 4 Unit Tests: Explainable Case Risk Scoring Engine
Tests deterministic, transparent risk scoring (0-100) with mathematical weights:
- Critical finding: 30 pts
- High finding: 20 pts
- Medium finding: 10 pts
- Low finding: 5 pts
- Cross-document discrepancy: 25 pts
- Capped at 100
- Mandatory disclaimer: "Triage priority, not a fraud verdict"
"""

import unittest
from backend.app import create_app
from backend.config import TestConfig
from backend.database import init_db, execute_db
from backend.models import create_case, create_finding, create_document
from backend.risk_scoring import (
    calculate_case_risk_score,
    WEIGHT_CRITICAL,
    WEIGHT_HIGH,
    WEIGHT_MEDIUM,
    WEIGHT_LOW,
    WEIGHT_DISCREPANCY,
    DISCLAIMER_TEXT,
    FORMULA_TEXT
)


class TestRiskScoring(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            init_db()

    def test_01_constants_and_weights(self):
        """Verify weights align with transparent additive rubric."""
        self.assertEqual(WEIGHT_CRITICAL, 30)
        self.assertEqual(WEIGHT_HIGH, 20)
        self.assertEqual(WEIGHT_MEDIUM, 10)
        self.assertEqual(WEIGHT_LOW, 5)
        self.assertEqual(WEIGHT_DISCREPANCY, 25)
        self.assertEqual(DISCLAIMER_TEXT, "Triage priority, not a fraud verdict")
        self.assertIn("min(100", FORMULA_TEXT)

    def test_02_empty_case_score(self):
        """Empty case yields score 0 and Unassessed status."""
        with self.app.app_context():
            case = create_case({'title': 'Empty Case Audit', 'type': 'Financial Fraud', 'priority': 'Medium'})
            res = calculate_case_risk_score(case['id'])
            self.assertEqual(res['risk_score'], 0)
            self.assertEqual(res['raw_score'], 0)
            self.assertFalse(res['capped_at_100'])
            self.assertEqual(res['risk_level'], "Unassessed / Empty Case")
            self.assertEqual(res['disclaimer'], DISCLAIMER_TEXT)

    def test_03_additive_severity_weights(self):
        """Test exact additive contribution of each finding severity."""
        with self.app.app_context():
            case = create_case({'title': 'Severity Weights Test', 'type': 'Tax Audit', 'priority': 'High'})
            doc = create_document({'case_id': case['id'], 'filename': 'sample.pdf', 'file_type': 'pdf', 'file_size': 1000})

            # 1 Critical: 30
            create_finding({
                'case_id': case['id'], 'document_id': doc['id'], 'severity': 'Critical',
                'title': 'Critical Patch', 'rule_id': 'RULE-VIS-001'
            })
            res = calculate_case_risk_score(case['id'])
            self.assertEqual(res['risk_score'], 30)
            self.assertEqual(res['raw_score'], 30)

            # + 1 High: 20 -> 50
            create_finding({
                'case_id': case['id'], 'document_id': doc['id'], 'severity': 'High',
                'title': 'High Baseline Disparity', 'rule_id': 'RULE-VIS-004'
            })
            res = calculate_case_risk_score(case['id'])
            self.assertEqual(res['risk_score'], 50)
            self.assertEqual(res['raw_score'], 50)

            # + 1 Medium: 10 -> 60
            create_finding({
                'case_id': case['id'], 'document_id': doc['id'], 'severity': 'Medium',
                'title': 'Medium Date Reversal', 'rule_id': 'RULE-CTX-003'
            })
            res = calculate_case_risk_score(case['id'])
            self.assertEqual(res['risk_score'], 60)
            self.assertEqual(res['raw_score'], 60)

            # + 1 Low: 5 -> 65
            create_finding({
                'case_id': case['id'], 'document_id': doc['id'], 'severity': 'Low',
                'title': 'Low Margin Shift', 'rule_id': 'RULE-DOC-001'
            })
            res = calculate_case_risk_score(case['id'])
            self.assertEqual(res['risk_score'], 65)
            self.assertEqual(res['raw_score'], 65)

    def test_04_score_capping_at_100(self):
        """When accumulated points exceed 100, score is capped at 100 with flag."""
        with self.app.app_context():
            case = create_case({'title': 'Capped Score Audit', 'type': 'Corporate Fraud', 'priority': 'Critical'})
            doc = create_document({'case_id': case['id'], 'filename': 'multi_tamper.pdf', 'file_type': 'pdf', 'file_size': 2000})

            # 4 Criticals = 4 * 30 = 120 points
            for i in range(4):
                create_finding({
                    'case_id': case['id'], 'document_id': doc['id'], 'severity': 'Critical',
                    'title': f'Tamper {i}', 'rule_id': f'RULE-VIS-00{i+1}'
                })

            res = calculate_case_risk_score(case['id'])
            self.assertEqual(res['raw_score'], 120)
            self.assertEqual(res['risk_score'], 100)
            self.assertTrue(res['capped_at_100'])
            self.assertEqual(res['risk_level'], "Critical Risk / Irregular")

    def test_05_cross_document_discrepancy_weight(self):
        """Cross-document discrepancy adds 25 points each."""
        import unittest.mock
        with self.app.app_context():
            case = create_case({'title': 'Discrepancy Score Test', 'type': 'Procurement Fraud', 'priority': 'High'})
            doc1 = create_document({'case_id': case['id'], 'filename': 'invoice_a.pdf', 'file_type': 'pdf', 'file_size': 1200})

            # 1 doc -> 0 discrepancies -> score 0
            res_before = calculate_case_risk_score(case['id'])
            self.assertEqual(res_before['risk_score'], 0)

            # Add doc2 and mock 2 discrepancies from comparison
            doc2 = create_document({'case_id': case['id'], 'filename': 'po_b.pdf', 'file_type': 'pdf', 'file_size': 1200})
            with unittest.mock.patch('backend.risk_scoring.compare_case_documents') as mock_comp:
                mock_comp.return_value = {
                    'success': True,
                    'discrepancies': [
                        {'attribute': 'Total Amount', 'message': '$10,000 vs $15,000', 'doc_a_filename': 'invoice_a.pdf', 'doc_b_filename': 'po_b.pdf'},
                        {'attribute': 'Vendor Name', 'message': 'Acme Inc vs Acme LLC', 'doc_a_filename': 'invoice_a.pdf', 'doc_b_filename': 'po_b.pdf'}
                    ]
                }
                res_after = calculate_case_risk_score(case['id'])
                # 2 discrepancies * 25 = 50 pts
                self.assertEqual(res_after['risk_score'], 50)
                self.assertEqual(res_after['counts']['discrepancies'], 2)
                self.assertEqual(res_after['raw_score'], 50)

    def test_06_api_endpoint(self):
        """API /api/cases/<id>/risk-score returns structured explainability payload."""
        with self.app.app_context():
            case = create_case({'title': 'API Route Test', 'type': 'General', 'priority': 'Medium'})
            doc = create_document({'case_id': case['id'], 'filename': 'doc.pdf', 'file_type': 'pdf', 'file_size': 500})
            create_finding({
                'case_id': case['id'], 'document_id': doc['id'], 'severity': 'High',
                'title': 'High Font Alert', 'rule_id': 'RULE-VIS-002'
            })

            resp = self.client.get(f"/api/cases/{case['id']}/risk-score")
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data['success'])
            risk_data = data['data']
            self.assertEqual(risk_data['risk_score'], 20)
            self.assertEqual(risk_data['disclaimer'], "Triage priority, not a fraud verdict")
            self.assertIn("breakdown", risk_data)
            self.assertEqual(len(risk_data['breakdown']), 5)


if __name__ == '__main__':
    unittest.main()
