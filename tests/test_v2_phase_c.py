"""
VEXORA — V2 Phase C Unit & Integration Tests: LLM Reasoning & Explainability Layer
Verifies:
1. PII Redaction (email, phone, long digits)
2. Source quote verification and anti-hallucination dropping
3. Mocked LLM responses for extraction, explanation, and cross-checking
4. Graceful degradation when disabled or key is missing
5. Endpoints: /api/system/ai-status, /api/documents/<id>/ai-extract, /api/findings/<id>/explain, /api/cases/<id>/ai-crosscheck
6. Persistence in ai_insights table and audit trail logging
7. Optional AI summary in dossier reports
"""

import os
import json
import time
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from backend.app import create_app
from backend.config import Config, TestConfig
from backend.database import init_db
from backend.models import (
    create_case,
    create_document,
    create_finding,
    get_ai_insights_by_document,
    get_ai_insights_by_case,
    get_audit_logs
)
from backend.llm import (
    redact_text_for_llm,
    verify_source_quote,
    extract_fields_llm,
    explain_finding,
    contextual_crosscheck,
    get_ai_status,
    AI_DISCLAIMER
)
from backend.reporter import generate_case_dossier_data, generate_dossier_html, generate_dossier_pdf


class TestPIIRedactionAndQuoteVerification(unittest.TestCase):
    """Unit tests for privacy masking and quote grounding verification."""

    def test_pii_redaction_masks_sensitive_data(self):
        sample = (
            "Contact vendor at billing@apexprocurement.com or sales@apex.org. "
            "Call +1-800-555-0199 or 212-555-9876 immediately. "
            "Remit wire transfer to IBAN 12345678901234567890 or account 987654321012. "
            "Total Invoice Amount: $450,000.00 dated 2026-10-18."
        )
        redacted = redact_text_for_llm(sample)

        self.assertNotIn("billing@apexprocurement.com", redacted)
        self.assertNotIn("sales@apex.org", redacted)
        self.assertIn("[REDACTED_EMAIL]", redacted)

        self.assertNotIn("+1-800-555-0199", redacted)
        self.assertNotIn("212-555-9876", redacted)
        self.assertIn("[REDACTED_PHONE]", redacted)

        self.assertNotIn("12345678901234567890", redacted)
        self.assertNotIn("987654321012", redacted)
        self.assertIn("[REDACTED_DIGITS]", redacted)

        # General text and amount should remain intact
        self.assertIn("Total Invoice Amount", redacted)
        self.assertIn("$450,000.00", redacted)

    def test_verify_source_quote_exact_and_case_insensitive(self):
        doc_text = "INVOICE #INV-9921 from Apex Global Ltd for Consultation Services totaling $45,000.00."

        # Exact match
        self.assertTrue(verify_source_quote("Apex Global Ltd", doc_text))
        # Case insensitive
        self.assertTrue(verify_source_quote("apex global ltd", doc_text))
        # Punctuation/whitespace variation
        self.assertTrue(verify_source_quote("Consultation Services", doc_text))

    def test_verify_source_quote_detects_hallucinations(self):
        doc_text = "Standard delivery order with no offshore subsidiary mentioned."

        # Hallucinated company name
        self.assertFalse(verify_source_quote("Shell Company Ltd", doc_text))
        # Hallucinated monetary figure
        self.assertFalse(verify_source_quote("$9,950,000.00", doc_text))
        # Empty/None
        self.assertFalse(verify_source_quote("", doc_text))
        self.assertFalse(verify_source_quote(None, doc_text))


class TestLLMFeaturesWithMocking(unittest.TestCase):
    """Tests LLM feature workflows with controlled mock responses."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="vexora_phase_c_test_")
        cls.test_db = os.path.join(cls.test_dir, "phase_c.db")
        cls.test_uploads = os.path.join(cls.test_dir, "uploads")
        cls.test_reports = os.path.join(cls.test_dir, "reports")
        os.makedirs(cls.test_uploads, exist_ok=True)
        os.makedirs(cls.test_reports, exist_ok=True)

        class PhaseCTestConfig(TestConfig):
            DATABASE = cls.test_db
            UPLOAD_FOLDER = cls.test_uploads
            REPORTS_FOLDER = cls.test_reports
            TESTING = True
            ENABLE_LLM = True
            VEXORA_LLM_PROVIDER = 'gemini'
            VEXORA_LLM_API_KEY = 'mock_api_key_for_testing_12345'
            VEXORA_LLM_REDACT = True

        cls.config_class = PhaseCTestConfig
        cls.app = create_app(PhaseCTestConfig)
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            init_db(cls.test_db)

    def _create_case(self, title="Test Case"):
        return create_case({
            'title': title,
            'type': 'Financial Audit',
            'priority': 'High',
            'status': 'Active',
            'investigator': 'Lead Reviewer',
            'description': 'Phase C test case'
        })

    def _create_doc(self, case_id, filename="sample.pdf", text=""):
        fpath = os.path.join(self.test_uploads, filename)
        with open(fpath, 'w') as f:
            f.write(text or "Dummy file content")
        return create_document({
            'case_id': case_id,
            'filename': filename,
            'file_type': 'pdf',
            'file_size': 1024,
            'file_path': fpath,
            'file_hash': 'mock_hash',
            'extracted_text': text,
            'category': 'Invoice',
            'status': 'Pending'
        })

    @patch('backend.llm.call_llm')
    def test_extract_fields_llm_anti_hallucination(self, mock_call):
        """Verifies that grounded fields are saved and ungrounded fields are dropped."""
        doc_text = "Invoice #INV-2026-991 from Veridian Dynamics Inc. Subtotal: $10,000.00. Total Due: $10,000.00."

        # Model response has 1 grounded field (Veridian Dynamics Inc) and 1 hallucinated field (Apex Offshore)
        mock_call.return_value = {
            "vendor": {
                "value": "Veridian Dynamics Inc",
                "confidence": 0.98,
                "source_quote": "Veridian Dynamics Inc"
            },
            "invoice_number": {
                "value": "INV-2026-991",
                "confidence": 0.99,
                "source_quote": "INV-2026-991"
            },
            "parties": [
                {
                    "role": "intermediary",
                    "name": "Apex Offshore Banking Corp",
                    "source_quote": "Apex Offshore Banking Corp"  # NOT in doc_text!
                }
            ]
        }

        with self.app.app_context():
            case = self._create_case("Extraction Case")
            doc = self._create_doc(case['id'], "inv.pdf", doc_text)

            res = extract_fields_llm(doc_text, doc_type="Invoice", document_id=doc['id'])

            self.assertIsNotNone(res)
            self.assertTrue(res['success'])
            # Grounded fields preserved
            self.assertIn("vendor", res['fields'])
            self.assertEqual(res['fields']['vendor']['value'], "Veridian Dynamics Inc")
            self.assertIn("invoice_number", res['fields'])

            # Ungrounded field dropped
            self.assertNotIn("parties", res['fields'])
            self.assertEqual(len(res['dropped_fields']), 1)
            self.assertEqual(res['dropped_fields'][0]['field'], "parties")

            # Check database table ai_insights
            insights = get_ai_insights_by_document(doc['id'])
            self.assertGreaterEqual(len(insights), 1)
            self.assertEqual(insights[0]['insight_type'], 'field_extraction')

    @patch('backend.llm.call_llm')
    def test_explain_finding(self, mock_call):
        """Verifies plain-language finding explanation with innocent hypotheses."""
        mock_call.return_value = {
            "explanation": "The font discrepancy in the subtotal row requires human scrutiny due to differing baseline resolutions.",
            "innocent_hypotheses": ["The accounting software upgraded its PDF export driver between invoice revisions."],
            "next_verification_step": "Request native XML invoice schema from ERP repository."
        }

        finding = {
            'id': 'FND-2026-999',
            'rule_id': 'RULE-VIS-001',
            'title': 'Discrepant Font Family Detected',
            'description': 'Subtotal rendered in Arial 300 DPI overlaid on Courier 150 DPI.',
            'evidence': 'Font Arial vs Courier',
            'severity': 'Medium'
        }

        with self.app.app_context():
            res = explain_finding(finding, nearby_text="Invoice Total: $50,000.00")
            self.assertIsNotNone(res)
            self.assertIn("font discrepancy", res['explanation'].lower())
            self.assertEqual(len(res['innocent_hypotheses']), 1)
            self.assertIn("upgrade", res['innocent_hypotheses'][0].lower())
            self.assertEqual(res['disclaimer'], AI_DISCLAIMER)

    @patch('backend.llm.call_llm')
    def test_contextual_crosscheck(self, mock_call):
        """Verifies multi-document cross-examination with quote grounding."""
        doc1_text = "Apex Purchase Order PO-101 states total value is $50,000.00."
        doc2_text = "Apex Delivery Manifest states delivered items value is $75,000.00."

        mock_call.return_value = {
            "inconsistencies": [
                {
                    "title": "Purchase Order and Delivery Manifest Value Mismatch",
                    "document_id": "DOC-A",
                    "severity": "High",
                    "description": "Purchase order PO-101 specifies $50,000.00 whereas delivery manifest specifies $75,000.00.",
                    "source_quote": "total value is $50,000.00",
                    "recommendation": "Confirm whether amendment addendum was executed."
                },
                {
                    "title": "Hallucinated Discrepancy",
                    "document_id": "DOC-A",
                    "severity": "Low",
                    "description": "Some imaginary conflict.",
                    "source_quote": "non existent quote here",
                    "recommendation": "None"
                }
            ]
        }

        docs = [
            {'id': 'DOC-A', 'filename': 'po.pdf', 'category': 'Purchase Order', 'extracted_text': doc1_text},
            {'id': 'DOC-B', 'filename': 'manifest.pdf', 'category': 'Manifest', 'extracted_text': doc2_text}
        ]

        with self.app.app_context():
            case = self._create_case("CrossCheck Case")
            findings = contextual_crosscheck(docs, case_id=case['id'])

            # Grounded finding preserved, hallucinated dropped
            self.assertEqual(len(findings), 1)
            f = findings[0]
            self.assertEqual(f['rule_id'], 'LLM-001')
            self.assertEqual(f['category'], 'Contextual Intelligence')
            self.assertEqual(f['evidence_class'], 'Inconsistency')
            self.assertIn("Purchase Order and Delivery Manifest", f['title'])
            self.assertIn(AI_DISCLAIMER, f['description'])


class TestGracefulDegradationAndEndpoints(unittest.TestCase):
    """Verifies that the system functions normally when AI is disabled or fails."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="vexora_phase_c_endpoints_")
        cls.test_db = os.path.join(cls.test_dir, "endpoints.db")
        cls.test_uploads = os.path.join(cls.test_dir, "uploads")
        cls.test_reports = os.path.join(cls.test_dir, "reports")
        os.makedirs(cls.test_uploads, exist_ok=True)
        os.makedirs(cls.test_reports, exist_ok=True)

        class DisabledAITestConfig(TestConfig):
            DATABASE = cls.test_db
            UPLOAD_FOLDER = cls.test_uploads
            REPORTS_FOLDER = cls.test_reports
            TESTING = True
            ENABLE_LLM = False  # Disabled by default
            VEXORA_LLM_API_KEY = ''

        cls.app = create_app(DisabledAITestConfig)
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            init_db(cls.test_db)

    def test_ai_status_endpoint_reports_disabled_without_secret_leak(self):
        resp = self.client.get('/api/system/ai-status')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data['enabled'])
        self.assertFalse(data['has_api_key'])
        self.assertIn('provider', data)
        self.assertIn('privacy_redaction_enabled', data)
        self.assertNotIn('api_key', data)
        self.assertNotIn('secret', str(data).lower())

    def test_endpoints_graceful_degradation_when_disabled(self):
        with self.app.app_context():
            case = create_case({
                'title': 'Disabled Case',
                'type': 'Audit',
                'priority': 'Medium',
                'status': 'Active',
                'investigator': 'Auditor',
                'description': 'Test'
            })
            doc = create_document({
                'case_id': case['id'],
                'filename': 'clean.pdf',
                'file_type': 'pdf',
                'file_size': 100,
                'file_path': os.path.join(self.test_uploads, 'clean.pdf'),
                'category': 'Invoice',
                'status': 'Pending'
            })
            from backend.models import save_document_extraction
            save_document_extraction(doc['id'], {'full_text': 'Simple text without errors.', 'page_count': 1, 'total_words': 4})
            f = create_finding({
                'document_id': doc['id'],
                'rule_id': 'RULE-VIS-001',
                'title': 'Font Check',
                'severity': 'Low'
            })

        # 1. AI Extract returns graceful response
        resp_extract = self.client.post(f"/api/documents/{doc['id']}/ai-extract")
        self.assertEqual(resp_extract.status_code, 200)
        data_extract = resp_extract.get_json()
        self.assertFalse(data_extract['success'])
        self.assertIn("unavailable or disabled", data_extract['message'])

        # 2. AI Explain returns graceful response
        resp_explain = self.client.post(f"/api/findings/{f['id']}/explain")
        self.assertEqual(resp_explain.status_code, 200)
        data_explain = resp_explain.get_json()
        self.assertFalse(data_explain['success'])
        self.assertIn("unavailable or disabled", data_explain['message'])

        # 3. 404 for missing resources
        self.assertEqual(self.client.post("/api/documents/NON_EXISTENT/ai-extract").status_code, 404)
        self.assertEqual(self.client.post("/api/findings/NON_EXISTENT/explain").status_code, 404)
        self.assertEqual(self.client.post("/api/cases/NON_EXISTENT/ai-crosscheck").status_code, 404)

    def test_dossier_includes_ai_summary_when_ai_data_exists(self):
        with self.app.app_context():
            case = create_case({
                'title': 'AI Dossier Case',
                'type': 'Audit',
                'priority': 'High',
                'status': 'Active',
                'investigator': 'Lead Reviewer',
                'description': 'Case testing AI dossier section'
            })
            doc = create_document({
                'case_id': case['id'],
                'filename': 'invoice.pdf',
                'file_type': 'pdf',
                'file_size': 500,
                'file_path': os.path.join(self.test_uploads, 'invoice.pdf'),
                'extracted_text': 'Total $10,000.00',
                'category': 'Invoice',
                'status': 'Pending'
            })
            # Insert an LLM finding into the case
            create_finding({
                'case_id': case['id'],
                'document_id': doc['id'],
                'rule_id': 'LLM-001',
                'title': '[AI] Arithmetic Mismatch Detected',
                'severity': 'High',
                'category': 'Contextual Intelligence',
                'evidence_class': 'Inconsistency',
                'description': f'Invoice total differs from line item sum [{AI_DISCLAIMER}].',
                'evidence': 'Grounded quote: "Total $10,000.00"'
            })

            dossier_data = generate_case_dossier_data(case['id'])
            self.assertIsNotNone(dossier_data.get('ai_summary'))
            self.assertTrue(dossier_data['ai_summary']['has_ai_data'])
            self.assertEqual(dossier_data['ai_summary']['ai_findings_count'], 1)

            # HTML Dossier includes AI section
            html_report = generate_dossier_html(case['id'])
            with open(html_report['file_path'], 'r', encoding='utf-8') as f_html:
                html_text = f_html.read()
            self.assertIn("AI-Assisted Investigation Summary", html_text)
            self.assertIn(AI_DISCLAIMER, html_text)

            # PDF Dossier includes AI section
            time.sleep(1.05)
            pdf_report = generate_dossier_pdf(case['id'], user="Auditor")
            self.assertTrue(os.path.exists(pdf_report['file_path']))
            self.assertGreater(pdf_report['file_size'], 1000)


if __name__ == '__main__':
    unittest.main()
