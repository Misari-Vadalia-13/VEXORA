"""
VEXORA — V2 Phase I Unit & Integration Tests: Live LLM Stabilization & Configuration
Verifies:
1. Configurable Model Name (DEFAULT_MODELS dict, VEXORA_LLM_MODEL env/config override).
2. Bad / unserved model name returns clear error message without crashing.
3. Strict anti-hallucination substring verification drops ungrounded claims and fields.
4. POST /api/system/ai-test returns expected keys, provider, model, latency, and never leaks keys.
5. GET /api/documents/<doc_id>/ai-insights retrieves stored insights.
6. tools/demo_ai.py exits cleanly with code 0 when no API key is configured.
"""

import os
import sys
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from backend.config import Config, TestConfig
from backend.app import create_app
from backend.database import init_db
from backend.models import create_case, create_document, get_ai_insights_by_document
from backend.llm import (
    DEFAULT_MODELS,
    get_model_name,
    get_last_llm_error,
    set_last_llm_error,
    test_ai_connection,
    extract_fields_llm,
    contextual_crosscheck,
    verify_source_quote,
    AI_DISCLAIMER
)


class TestConfigurableModelAndErrorHandling(unittest.TestCase):
    """Tests configurable model selection, default dictionary, and clear error reporting."""

    def test_default_models_per_provider(self):
        """Verifies default model per provider matches expected defaults."""
        self.assertEqual(DEFAULT_MODELS.get('gemini'), 'gemini-1.5-flash')
        self.assertEqual(DEFAULT_MODELS.get('openai'), 'gpt-4o-mini')
        self.assertIn('claude-3-haiku', DEFAULT_MODELS.get('claude'))

        # Without override, get_model_name returns provider default
        with patch.object(Config, 'VEXORA_LLM_MODEL', ''):
            with patch.dict(os.environ, {'VEXORA_LLM_MODEL': ''}):
                self.assertEqual(get_model_name('gemini'), 'gemini-1.5-flash')
                self.assertEqual(get_model_name('openai'), 'gpt-4o-mini')
                self.assertEqual(get_model_name('claude'), 'claude-3-haiku-20240307')

    def test_configured_model_override(self):
        """Verifies VEXORA_LLM_MODEL overrides default model for any provider."""
        custom_model = "gemini-2.5-flash-experimental"
        with patch.object(Config, 'VEXORA_LLM_MODEL', custom_model):
            self.assertEqual(get_model_name('gemini'), custom_model)
            self.assertEqual(get_model_name('openai'), custom_model)

    @patch('backend.llm.requests.post')
    def test_bad_model_name_returns_clear_error_gemini(self, mock_post):
        """Verifies HTTP 404 / model-not-found produces a clear helpful error message without crashing."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = json.dumps({
            "error": {
                "code": 404,
                "message": "models/deprecated-model is not found for API version v1beta",
                "status": "NOT_FOUND"
            }
        })
        mock_post.return_value = mock_resp

        with patch.object(Config, 'ENABLE_LLM', True):
            with patch.object(Config, 'VEXORA_LLM_API_KEY', 'valid-test-key-12345'):
                with patch.object(Config, 'VEXORA_LLM_PROVIDER', 'gemini'):
                    with patch.object(Config, 'VEXORA_LLM_MODEL', 'deprecated-model'):
                        res = test_ai_connection()
                        self.assertFalse(res['ok'])
                        self.assertIn("deprecated-model", res['error'])
                        self.assertIn("not found", res['error'].lower())
                        self.assertIn("VEXORA_LLM_MODEL", res['error'])
                        # Never leak secret key
                        self.assertNotIn("valid-test-key-12345", json.dumps(res))

    @patch('backend.llm.requests.post')
    def test_bad_model_name_returns_clear_error_openai(self, mock_post):
        """Verifies OpenAI 404 model not found returns clear error to set VEXORA_LLM_MODEL."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = '{"error": {"message": "The model `gpt-old` does not exist", "type": "invalid_request_error"}}'
        mock_post.return_value = mock_resp

        with patch.object(Config, 'ENABLE_LLM', True):
            with patch.object(Config, 'VEXORA_LLM_API_KEY', 'sk-test-key-99999'):
                with patch.object(Config, 'VEXORA_LLM_PROVIDER', 'openai'):
                    with patch.object(Config, 'VEXORA_LLM_MODEL', 'gpt-old'):
                        res = test_ai_connection()
                        self.assertFalse(res['ok'])
                        self.assertIn("gpt-old", res['error'])
                        self.assertIn("VEXORA_LLM_MODEL", res['error'])
                        self.assertNotIn("sk-test-key-99999", json.dumps(res))


class TestUngroundedClaimsDropped(unittest.TestCase):
    """Verifies that ungrounded quotes in extraction and crosscheck are dropped."""

    @patch('backend.llm.call_llm')
    def test_contextual_crosscheck_drops_ungrounded_quote(self, mock_call):
        """A claim whose source quote is not in the text must be dropped."""
        doc_text = "Acme Consulting invoice INV-100 totals $25,000.00 dated 2026-05-01."
        mock_call.return_value = {
            "inconsistencies": [
                {
                    "title": "Grounded Observation",
                    "document_id": "DOC-1",
                    "severity": "Medium",
                    "description": "Invoice totals $25,000.00.",
                    "source_quote": "totals $25,000.00",
                    "recommendation": "Review"
                },
                {
                    "title": "Hallucinated Mismatch",
                    "document_id": "DOC-1",
                    "severity": "High",
                    "description": "Payment was sent to shell company in Cayman Islands.",
                    "source_quote": "Cayman Islands Account 889900",  # NOT in doc_text!
                    "recommendation": "Review"
                }
            ]
        }

        docs = [{'id': 'DOC-1', 'filename': 'inv.pdf', 'category': 'Invoice', 'extracted_text': doc_text}]
        findings = contextual_crosscheck(docs)

        # Only the grounded finding is accepted
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['title'], "[AI] Grounded Observation")
        self.assertIn("totals $25,000.00", findings[0]['evidence'])

    @patch('backend.llm.call_llm')
    def test_extract_fields_llm_drops_ungrounded_and_keeps_grounded(self, mock_call):
        """Fields with hallucinated quotes are dropped into dropped_fields."""
        doc_text = "Vendor: CyberDyne Systems. Invoice Number: CS-884. Subtotal: $15,000.00."
        mock_call.return_value = {
            "vendor": {
                "value": "CyberDyne Systems",
                "confidence": 0.95,
                "source_quote": "CyberDyne Systems"
            },
            "invoice_number": {
                "value": "CS-884",
                "confidence": 0.99,
                "source_quote": "CS-884"
            },
            "subtotal": {
                "value": "15000.00",
                "confidence": 0.90,
                "source_quote": "$15,000.00"
            },
            "tax": {
                "value": "5000.00",
                "confidence": 0.80,
                "source_quote": "Tax Amount: $5,000.00"  # Hallucinated!
            }
        }

        res = extract_fields_llm(doc_text, doc_type="Invoice")
        self.assertIsNotNone(res)
        self.assertTrue(res['success'])

        # Grounded fields preserved
        self.assertIn('vendor', res['fields'])
        self.assertIn('invoice_number', res['fields'])
        self.assertIn('subtotal', res['fields'])

        # Ungrounded tax dropped
        self.assertNotIn('tax', res['fields'])
        dropped_names = [d['field'] for d in res['dropped_fields']]
        self.assertIn('tax', dropped_names)


class TestAiEndpoints(unittest.TestCase):
    """Verifies POST /api/system/ai-test and GET /api/documents/<doc_id>/ai-insights."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="vexora_phase_i_test_")
        cls.test_db = os.path.join(cls.test_dir, "phase_i.db")
        cls.test_uploads = os.path.join(cls.test_dir, "uploads")
        cls.test_reports = os.path.join(cls.test_dir, "reports")
        os.makedirs(cls.test_uploads, exist_ok=True)
        os.makedirs(cls.test_reports, exist_ok=True)

        class PhaseITestConfig(TestConfig):
            DATABASE = cls.test_db
            UPLOAD_FOLDER = cls.test_uploads
            REPORTS_FOLDER = cls.test_reports
            TESTING = True
            ENABLE_LLM = False
            VEXORA_LLM_API_KEY = ''

        cls.app = create_app(PhaseITestConfig)
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            init_db(cls.test_db)

    def test_ai_test_endpoint_when_disabled_returns_expected_keys(self):
        """When disabled, returns ok=False with provider, model, latency_ms and no secret leak."""
        resp = self.client.post('/api/system/ai-test')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('ok', data)
        self.assertFalse(data['ok'])
        self.assertIn('provider', data)
        self.assertIn('model', data)
        self.assertIn('latency_ms', data)
        self.assertIn('error', data)
        self.assertNotIn('key', str(data).lower())
        self.assertNotIn('secret', str(data).lower())

    @patch('backend.llm.test_ai_connection')
    def test_ai_test_endpoint_mock_success(self, mock_test):
        """When active, returns ok=True with latency and provider."""
        mock_test.return_value = {
            'ok': True,
            'provider': 'gemini',
            'model': 'gemini-1.5-flash',
            'latency_ms': 214.5,
            'response_sample': 'OK',
            'disclaimer': AI_DISCLAIMER
        }
        resp = self.client.post('/api/system/ai-test')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['provider'], 'gemini')
        self.assertEqual(data['model'], 'gemini-1.5-flash')
        self.assertGreater(data['latency_ms'], 0)

    def test_document_ai_insights_endpoint(self):
        """GET /api/documents/<id>/ai-insights returns list of insights for document."""
        with self.app.app_context():
            case = create_case({
                'title': 'Insights Case',
                'type': 'Audit',
                'priority': 'Medium',
                'status': 'Active',
                'investigator': 'Auditor',
                'description': 'Test'
            })
            doc = create_document({
                'case_id': case['id'],
                'filename': 'test.pdf',
                'file_type': 'pdf',
                'file_size': 100,
                'file_path': os.path.join(self.test_uploads, 'test.pdf'),
                'category': 'Invoice',
                'status': 'Pending'
            })

        resp = self.client.get(f"/api/documents/{doc['id']}/ai-insights")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['document_id'], doc['id'])
        self.assertIsInstance(data['data'], list)

        # Non-existent document returns 404
        self.assertEqual(self.client.get("/api/documents/NON_EXISTENT_ID/ai-insights").status_code, 404)


class TestCliDemoAi(unittest.TestCase):
    """Verifies that tools/demo_ai.py exits cleanly with code 0 when no key is set."""

    def test_demo_ai_exits_0_when_no_key_configured(self):
        env = dict(os.environ)
        env.pop('VEXORA_LLM_API_KEY', None)
        env.pop('GEMINI_API_KEY', None)
        env.pop('OPENAI_API_KEY', None)
        env['ENABLE_LLM'] = 'false'

        proc = subprocess.run(
            [sys.executable, 'tools/demo_ai.py'],
            capture_output=True,
            text=True,
            env=env
        )

        self.assertEqual(proc.returncode, 0)
        self.assertIn("AI not configured, skipped", proc.stdout)


if __name__ == '__main__':
    unittest.main()
