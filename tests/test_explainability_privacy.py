"""
VEXORA — Unit Tests for AI Explainability & Privacy Guardrails (Stage 6)
Verifies:
1. Extended PII masking (IBANs, Payment Cards, National Identity numbers).
2. Resilient JSON block recovery (trailing commas, conversational wrapping).
3. Schema compliance and safe defaults in explain_finding.
4. Anti-hallucination source quote enforcement in contextual cross-checking.
"""

import json
import unittest
from unittest.mock import patch, MagicMock

from backend.llm import (
    redact_text_for_llm,
    verify_source_quote,
    _parse_json_block,
    explain_finding,
    contextual_crosscheck,
    AI_DISCLAIMER
)


class TestExplainabilityAndPrivacy(unittest.TestCase):
    """Test suite for Stage 6 AI reasoning, privacy masking, and anti-hallucination rules."""

    def test_01_extended_pii_redaction(self):
        """Verifies IBAN, credit card, Aadhaar, SSN, and email masking."""
        text = (
            "Wire $50,000 to IBAN GB29XFRM12345678901234 or charge card 4111-2222-3333-4444. "
            "Customer Aadhaar card is 4567 8901 2345. Social Security: 123-45-6789. "
            "Contact accounts@apexcorp.com or 555-019-2831."
        )
        redacted = redact_text_for_llm(text)

        self.assertNotIn("GB29XFRM12345678901234", redacted)
        self.assertIn("[REDACTED_IBAN]", redacted)

        self.assertNotIn("4111-2222-3333-4444", redacted)
        self.assertIn("[REDACTED_CARD]", redacted)

        self.assertNotIn("4567 8901 2345", redacted)
        self.assertIn("[REDACTED_AADHAAR]", redacted)

        self.assertNotIn("123-45-6789", redacted)
        self.assertIn("[REDACTED_SSN]", redacted)

        self.assertNotIn("accounts@apexcorp.com", redacted)
        self.assertIn("[REDACTED_EMAIL]", redacted)

    def test_02_json_block_recovery_trailing_commas_and_wrapping(self):
        """Verifies _parse_json_block parses JSON with trailing commas and conversational wrapper text."""
        # Case A: Trailing comma in dict and list
        malformed_json = '{\n  "status": "success",\n  "items": ["apple", "orange",],\n}'
        parsed_a = _parse_json_block(malformed_json)
        self.assertIsNotNone(parsed_a)
        self.assertEqual(parsed_a.get("status"), "success")
        self.assertEqual(len(parsed_a.get("items")), 2)

        # Case B: Embedded JSON with leading conversational preamble and markdown fence
        preamble_json = """
        Here is the forensic evaluation in requested JSON format:
        ```json
        {
          "finding": "RULE-VIS-001",
          "confidence": 0.85,
        }
        ```
        Hope this analysis assists your investigation!
        """
        parsed_b = _parse_json_block(preamble_json)
        self.assertIsNotNone(parsed_b)
        self.assertEqual(parsed_b.get("finding"), "RULE-VIS-001")
        self.assertEqual(parsed_b.get("confidence"), 0.85)

    @patch('backend.models.log_audit')
    @patch('backend.llm.call_llm')
    def test_03_explain_finding_strict_schema_and_fallbacks(self, mock_llm, mock_audit):
        """Verifies explain_finding returns well-formed schema even when model returns minimal fields."""
        # Model returns partial response without innocent hypotheses
        mock_llm.return_value = {
            "explanation": "This text span exhibits different font metrics compared to surrounding content.",
            "innocent_hypotheses": [],
            "next_verification_step": ""
        }

        finding = {
            'id': 'FND-001',
            'rule_id': 'RULE-VIS-001',
            'title': 'Discrepant Font Family Detected',
            'description': 'Two disparate fonts used on same line.',
            'evidence': 'Font Arial vs Times'
        }

        result = explain_finding(finding, nearby_text="Invoice text snippet")
        self.assertIsNotNone(result)
        self.assertEqual(result['finding_id'], 'FND-001')
        self.assertEqual(result['rule_id'], 'RULE-VIS-001')
        self.assertTrue(len(result['explanation']) > 10)
        # Verify fallback innocent hypothesis populated
        self.assertTrue(len(result['innocent_hypotheses']) >= 1)
        # Verify fallback next verification step populated
        self.assertTrue(len(result['next_verification_step']) > 5)
        # Verify mandatory disclaimer
        self.assertEqual(result['disclaimer'], AI_DISCLAIMER)

    @patch('backend.models.log_audit')
    @patch('backend.llm.call_llm')
    def test_04_contextual_crosscheck_drops_hallucinated_findings(self, mock_llm, mock_audit):
        """Verifies contextual_crosscheck drops findings whose source quotes cannot be verified."""
        mock_llm.return_value = {
            "inconsistencies": [
                {
                    "title": "Legitimate Grounded Inconsistency",
                    "document_id": "DOC-01",
                    "severity": "High",
                    "description": "Invoice amount does not match PO total.",
                    "source_quote": "Grand Total: $45,000.00",
                    "recommendation": "Inspect bank transfer."
                },
                {
                    "title": "Hallucinated Phantom Inconsistency",
                    "document_id": "DOC-01",
                    "severity": "High",
                    "description": "Ghost company mentioned.",
                    "source_quote": "Offshore Cayman Island Shell Account #999",
                    "recommendation": "Check corporate registry."
                }
            ]
        }

        doc = {
            'id': 'DOC-01',
            'filename': 'Invoice_Apex.pdf',
            'extracted_text': "INVOICE #101. Grand Total: $45,000.00. Payment Terms: Net 30."
        }

        findings = contextual_crosscheck([doc])
        # Only the grounded finding should be preserved; phantom finding dropped
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f['title'], "[AI] Legitimate Grounded Inconsistency")
        self.assertEqual(f['evidence_class'], 'Inconsistency')
        self.assertIn(AI_DISCLAIMER, f['description'])
        self.assertIn("Grand Total: $45,000.00", f['evidence'])

    def test_05_verify_source_quote_edge_cases(self):
        """Tests strict source quote verification against edge cases."""
        doc_text = "Standard Procurement Order PO-2026-991. Total Amount Due: $1,450,200.00. Vendor: Acme Global Ltd."

        # Exact match
        self.assertTrue(verify_source_quote("Total Amount Due: $1,450,200.00", doc_text))

        # Normalized whitespace & case
        self.assertTrue(verify_source_quote("  total   amount   due:   $1,450,200.00  ", doc_text))

        # Punctuation variations
        self.assertTrue(verify_source_quote("Total Amount Due 145020000", doc_text))

        # Hallucinated quote
        self.assertFalse(verify_source_quote("Kickback to Secret Account $500,000", doc_text))

        # Empty / None inputs
        self.assertFalse(verify_source_quote("", doc_text))
        self.assertFalse(verify_source_quote(None, doc_text))
        self.assertFalse(verify_source_quote("Total Amount", ""))

    def test_06_call_llm_missing_api_key_and_disabled_flag(self):
        """call_llm returns None gracefully when feature is disabled or key is absent."""
        from backend.config import Config
        from backend.llm import call_llm

        orig_enabled = getattr(Config, 'ENABLE_LLM', False)
        orig_key = getattr(Config, 'VEXORA_LLM_API_KEY', '')

        try:
            # 1. Disabled via config
            Config.ENABLE_LLM = False
            Config.VEXORA_LLM_API_KEY = "dummy-key"
            self.assertIsNone(call_llm("test prompt"))

            # 2. Enabled but missing key
            Config.ENABLE_LLM = True
            Config.VEXORA_LLM_API_KEY = ""
            with patch.dict('os.environ', {'VEXORA_LLM_API_KEY': '', 'GEMINI_API_KEY': '', 'OPENAI_API_KEY': ''}):
                self.assertIsNone(call_llm("test prompt"))
        finally:
            Config.ENABLE_LLM = orig_enabled
            Config.VEXORA_LLM_API_KEY = orig_key

    @patch('backend.llm.requests.post')
    def test_07_call_llm_http_401_invalid_key_handling(self, mock_post):
        """call_llm handles 401 Unauthorized without crashing and sets sanitized error."""
        from backend.config import Config
        from backend.llm import call_llm, get_last_llm_error

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = '{"error": {"message": "API key not valid. Please pass a valid API key."}}'
        mock_post.return_value = mock_resp

        orig_enabled = getattr(Config, 'ENABLE_LLM', False)
        orig_key = getattr(Config, 'VEXORA_LLM_API_KEY', '')
        try:
            Config.ENABLE_LLM = True
            Config.VEXORA_LLM_API_KEY = "invalid-test-key"
            result = call_llm("Analyze this document")
            self.assertIsNone(result)
            err = get_last_llm_error() or ""
            self.assertIn("401", err)
        finally:
            Config.ENABLE_LLM = orig_enabled
            Config.VEXORA_LLM_API_KEY = orig_key

    @patch('backend.llm.requests.post')
    def test_08_call_llm_http_429_rate_limit_handling(self, mock_post):
        """call_llm handles HTTP 429 Rate Limit cleanly without throwing exceptions."""
        from backend.config import Config
        from backend.llm import call_llm, get_last_llm_error

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = '{"error": {"message": "Resource has been exhausted (e.g. check quota)."}}'
        mock_post.return_value = mock_resp

        orig_enabled = getattr(Config, 'ENABLE_LLM', False)
        orig_key = getattr(Config, 'VEXORA_LLM_API_KEY', '')
        try:
            Config.ENABLE_LLM = True
            Config.VEXORA_LLM_API_KEY = "valid-test-key"
            result = call_llm("Analyze this document")
            self.assertIsNone(result)
            err = get_last_llm_error() or ""
            self.assertIn("429", err)
        finally:
            Config.ENABLE_LLM = orig_enabled
            Config.VEXORA_LLM_API_KEY = orig_key

    @patch('backend.llm.requests.post')
    def test_09_call_llm_timeout_handling(self, mock_post):
        """call_llm catches requests.exceptions.Timeout and returns None gracefully."""
        import requests
        from backend.config import Config
        from backend.llm import call_llm

        mock_post.side_effect = requests.exceptions.Timeout("Request timed out after 30s")

        orig_enabled = getattr(Config, 'ENABLE_LLM', False)
        orig_key = getattr(Config, 'VEXORA_LLM_API_KEY', '')
        try:
            Config.ENABLE_LLM = True
            Config.VEXORA_LLM_API_KEY = "valid-test-key"
            result = call_llm("Analyze this document")
            self.assertIsNone(result)
        finally:
            Config.ENABLE_LLM = orig_enabled
            Config.VEXORA_LLM_API_KEY = orig_key

    def test_10_ai_status_telemetry_reporting(self):
        """get_ai_status accurately reports provider configuration without leaking keys."""
        from backend.config import Config
        from backend.llm import get_ai_status

        orig_enabled = getattr(Config, 'ENABLE_LLM', False)
        orig_key = getattr(Config, 'VEXORA_LLM_API_KEY', '')
        try:
            Config.ENABLE_LLM = True
            Config.VEXORA_LLM_API_KEY = "secret-super-key-99999"
            status = get_ai_status()

            self.assertIn('enabled', status)
            self.assertTrue(status['enabled'])
            self.assertIn('provider', status)
            self.assertIn('model', status)
            self.assertTrue(status['has_api_key'])
            # Verify key itself is NEVER leaked in telemetry
            status_str = json.dumps(status)
            self.assertNotIn("secret-super-key-99999", status_str)
        finally:
            Config.ENABLE_LLM = orig_enabled
            Config.VEXORA_LLM_API_KEY = orig_key


if __name__ == '__main__':
    unittest.main()

