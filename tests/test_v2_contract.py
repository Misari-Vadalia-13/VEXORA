"""
VEXORA — V2 Contract Safety Net Test Suite
Verifies that all baseline Flask routes exist and return their documented response keys,
and that all baseline SQLite tables and columns exist according to docs/EXISTING_CONTRACT.md.
Must pass before and after every phase.
"""

import os
import unittest
import sqlite3
import tempfile
import shutil
from pathlib import Path

from backend.app import create_app
from backend.config import Config, TestConfig
from backend.database import init_db
from backend.analyzer import RULES, calculate_risk_assessment
from backend.ner import PATTERNS, extract_entities_from_text


class TestExistingContract(unittest.TestCase):
    """Verifies the core contract defined in docs/EXISTING_CONTRACT.md."""

    @classmethod
    def setUpClass(cls):
        # Create a dedicated temporary test directory and database
        cls.test_dir = tempfile.mkdtemp(prefix="vexora_contract_test_")
        cls.test_db = os.path.join(cls.test_dir, "contract_test.db")
        cls.test_uploads = os.path.join(cls.test_dir, "uploads")
        cls.test_reports = os.path.join(cls.test_dir, "reports")
        os.makedirs(cls.test_uploads, exist_ok=True)
        os.makedirs(cls.test_reports, exist_ok=True)

        class CustomContractConfig(TestConfig):
            DATABASE = cls.test_db
            UPLOAD_FOLDER = cls.test_uploads
            REPORTS_FOLDER = cls.test_reports
            TESTING = True

        cls.app = create_app(CustomContractConfig)
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            init_db(cls.test_db)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # =========================================================================
    # 1. Database Schema & Column Contract
    # =========================================================================

    def test_database_tables_and_columns_contract(self):
        """Verifies that all 7 required tables and their baseline columns exist in SQLite."""
        expected_schema = {
            'users': [
                'id', 'username', 'email', 'password_hash', 'role', 'badge_number', 'created_at'
            ],
            'cases': [
                'id', 'title', 'type', 'priority', 'status', 'investigator', 'description',
                'created_at', 'updated_at'
            ],
            'documents': [
                'id', 'case_id', 'filename', 'file_type', 'file_size', 'file_path', 'file_hash',
                'category', 'classification_confidence', 'status', 'extracted_text',
                'extracted_data', 'uploaded_by', 'uploaded_at'
            ],
            'findings': [
                'id', 'case_id', 'document_id', 'title', 'severity', 'category', 'description',
                'confidence', 'status', 'page_number', 'coordinates', 'rule_id', 'evidence',
                'created_at'
            ],
            'audit_logs': [
                'id', 'action', 'entity_type', 'entity_id', 'details', 'user', 'timestamp'
            ],
            'comparisons': [
                'id', 'case_id', 'doc_a_id', 'doc_b_id', 'discrepancies_count', 'matches_count',
                'results_json', 'created_at'
            ],
            'reports': [
                'id', 'case_id', 'title', 'file_path', 'file_format', 'file_size',
                'generated_by', 'created_at'
            ]
        }

        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()

        for table, expected_cols in expected_schema.items():
            cursor.execute(f"PRAGMA table_info({table})")
            columns_info = cursor.fetchall()
            self.assertTrue(len(columns_info) > 0, f"Table '{table}' must exist in SQLite schema.")

            actual_col_names = [col[1] for col in columns_info]
            for col in expected_cols:
                self.assertIn(
                    col,
                    actual_col_names,
                    f"Column '{col}' must exist in table '{table}'."
                )

        conn.close()

    # =========================================================================
    # 2. Flask Routes Existence Contract
    # =========================================================================

    def test_flask_routes_exist(self):
        """Verifies that all documented endpoints exist in the Flask application url map."""
        expected_endpoints = [
            'serve_index',
            'api_health',
            'api_stats',
            'api_system_diagnostics',
            'api_login',
            'api_register',
            'api_current_user',
            'api_list_cases',
            'api_create_case',
            'api_get_case',
            'api_update_case',
            'api_delete_case',
            'api_compare_case_documents',
            'api_get_case_dossier',
            'api_generate_case_report',
            'api_list_documents',
            'api_register_document',
            'api_get_document',
            'api_delete_document',
            'api_upload_documents',
            'api_extract_document',
            'api_get_extracted_document',
            'api_analyze_document',
            'api_get_document_findings',
            'api_download_document',
            'api_compare_documents',
            'api_evidence_graph',
            'api_list_findings',
            'api_create_finding',
            'api_get_finding',
            'api_update_finding',
            'api_list_reports',
            'api_get_report_metadata',
            'api_download_report',
            'api_view_report',
            'api_audit_logs',
            'api_export_audit_logs'
        ]

        registered_endpoints = set(self.app.view_functions.keys())
        for ep in expected_endpoints:
            self.assertIn(ep, registered_endpoints, f"Flask endpoint '{ep}' must be registered.")

    # =========================================================================
    # 3. Baseline GET Endpoints Response Keys Contract
    # =========================================================================

    def test_api_health_contract(self):
        """GET /api/health must return required contract keys."""
        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('status', data)
        self.assertIn('system', data)
        self.assertIn('version', data)
        self.assertIn('database', data)

    def test_api_stats_contract(self):
        """GET /api/stats must return success and data telemetry keys."""
        res = self.client.get('/api/stats')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('data', data)
        stats = data['data']
        for key in ['total_cases', 'active_cases', 'total_documents', 'total_findings', 'flagged_documents', 'critical_findings']:
            self.assertIn(key, stats)

    def test_api_system_diagnostics_contract(self):
        """GET /api/system/diagnostics must return diagnostics keys."""
        res = self.client.get('/api/system/diagnostics')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('status', data)
        self.assertIn('engine_version', data)
        self.assertIn('database', data)
        self.assertIn('storage', data)

    def test_api_cases_list_contract(self):
        """GET /api/cases must return success, count, and data list."""
        res = self.client.get('/api/cases')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('count', data)
        self.assertIn('data', data)
        self.assertIsInstance(data['data'], list)

    def test_api_documents_list_contract(self):
        """GET /api/documents must return success, count, and data list."""
        res = self.client.get('/api/documents')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('count', data)
        self.assertIn('data', data)
        self.assertIsInstance(data['data'], list)

    def test_api_findings_list_contract(self):
        """GET /api/findings must return success, count, and data list."""
        res = self.client.get('/api/findings')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('count', data)
        self.assertIn('data', data)
        self.assertIsInstance(data['data'], list)

    def test_api_reports_list_contract(self):
        """GET /api/reports must return success, count, and data list."""
        res = self.client.get('/api/reports')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('count', data)
        self.assertIn('data', data)
        self.assertIsInstance(data['data'], list)

    def test_api_audit_logs_contract(self):
        """GET /api/audit-logs must return success, count, and data list."""
        res = self.client.get('/api/audit-logs')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('count', data)
        self.assertIn('data', data)
        self.assertIsInstance(data['data'], list)

    def test_api_evidence_graph_contract(self):
        """GET /api/evidence-graph must return success, count, and data list."""
        res = self.client.get('/api/evidence-graph')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('count', data)
        self.assertIn('data', data)
        self.assertIsInstance(data['data'], list)

    def test_served_index_contract(self):
        """GET / and /index.html must serve frontend/index.html (not empty redirect)."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'VEXORA', res.data)
        self.assertIn(b'vexoraSidebar', res.data)
        self.assertIn(b'forensicFindingsFeed', res.data)

        res_html = self.client.get('/index.html')
        self.assertEqual(res_html.status_code, 200)
        self.assertIn(b'VEXORA', res_html.data)

    # =========================================================================
    # 4. Forensic Engine Rules & Entity Types Contract
    # =========================================================================

    def test_forensic_rules_contract(self):
        """All 10 baseline forensic rules must be present in analyzer.RULES."""
        expected_rule_ids = [
            'RULE-VIS-001', 'RULE-VIS-002', 'RULE-VIS-003', 'RULE-VIS-004', 'RULE-VIS-005',
            'RULE-CTX-001', 'RULE-CTX-002', 'RULE-CTX-003', 'RULE-CTX-004', 'RULE-CTX-005'
        ]
        for rid in expected_rule_ids:
            self.assertIn(rid, RULES, f"Rule ID '{rid}' must exist in analyzer.RULES dictionary.")
            rule = RULES[rid]
            for key in ['id', 'title', 'category', 'severity', 'confidence', 'recommendation']:
                self.assertIn(key, rule, f"Rule '{rid}' must contain attribute '{key}'.")

    def test_risk_assessment_calculation_contract(self):
        """calculate_risk_assessment must return expected keys and bounded scores."""
        assessment = calculate_risk_assessment([])
        self.assertEqual(assessment['risk_score'], 0)
        self.assertEqual(assessment['risk_level'], 'Clean / Verified')
        for key in ['risk_score', 'risk_level', 'severity_breakdown', 'summary']:
            self.assertIn(key, assessment)

    def test_ner_entity_categories_contract(self):
        """Entity extraction module must support all standard entity categories."""
        expected_categories = ['dates', 'monetary_values', 'organizations', 'persons', 'identifiers', 'emails']
        extracted = extract_entities_from_text("Sample invoice INV-100 on 2026-01-01 for $500.")
        for cat in expected_categories:
            self.assertIn(cat, extracted, f"Entity extraction result must include '{cat}'.")


if __name__ == '__main__':
    unittest.main()
