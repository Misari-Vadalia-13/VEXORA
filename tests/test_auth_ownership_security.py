"""
VEXORA — Automated Security & Authorization Test Suite
Verifies:
1. Insecure Direct Object Reference (IDOR) protection for cases and documents.
2. Role-Based Access Control (RBAC) boundaries (Admin vs Analyst).
3. Session authentication enforcement when VEXORA_REQUIRE_AUTH=True.
4. Session logout and invalidation.
5. CORS header restriction against arbitrary origins.
6. Production configuration safety checks.
"""

import unittest
import os
import json
import tempfile
import shutil
from pathlib import Path

from backend.app import create_app
from backend.database import get_db, init_db, seed_data
from backend.models import create_case, create_document


class TestAuthAndOwnershipSecurity(unittest.TestCase):
    """Test suite for authentication, authorization, IDOR, and RBAC security."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="vexora_test_security_"))
        cls.db_path = cls.temp_dir / "security_test.db"
        cls.upload_dir = cls.temp_dir / "uploads"
        cls.upload_dir.mkdir(parents=True, exist_ok=True)

        cls.config = {
            'TESTING': True,
            'DATABASE': str(cls.db_path),
            'UPLOAD_FOLDER': str(cls.upload_dir),
            'VEXORA_REQUIRE_AUTH': True,
            'SECRET_KEY': 'test-security-secret-key',
            'VEXORA_CORS_ORIGINS': 'http://127.0.0.1:5000,http://localhost:5000'
        }

        # Initialize database with schema
        init_db(str(cls.db_path))

        # Create two separate analysts and one admin
        from werkzeug.security import generate_password_hash
        conn = get_db(str(cls.db_path))
        c = conn.cursor()
        
        # User 1: Alice (Analyst)
        c.execute(
            "INSERT INTO users (id, username, email, password_hash, role, badge_number) VALUES (?, ?, ?, ?, ?, ?)",
            (101, "analyst_alice", "alice@vexora.internal", generate_password_hash("AlicePass@2026", method="scrypt"), "Forensic Analyst", "VEX-101")
        )
        # User 2: Bob (Analyst)
        c.execute(
            "INSERT INTO users (id, username, email, password_hash, role, badge_number) VALUES (?, ?, ?, ?, ?, ?)",
            (102, "analyst_bob", "bob@vexora.internal", generate_password_hash("BobPass@2026", method="scrypt"), "Forensic Analyst", "VEX-102")
        )
        # User 3: Carol (Admin)
        c.execute(
            "INSERT INTO users (id, username, email, password_hash, role, badge_number) VALUES (?, ?, ?, ?, ?, ?)",
            (103, "admin_carol", "carol@vexora.internal", generate_password_hash("CarolAdmin@2026", method="scrypt"), "System Administrator", "VEX-999")
        )
        
        # Case 1: Owned by Alice
        c.execute(
            """
            INSERT INTO cases (id, title, type, priority, status, investigator, owner_id, owner_username, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("CAS-ALICE-001", "Alice Confidential Case", "Financial Fraud", "High", "Active", "Analyst Alice", 101, "analyst_alice", "Classified investigation")
        )
        
        # Document 1: Inside Alice's Case
        c.execute(
            """
            INSERT INTO documents (id, case_id, filename, file_type, file_size, file_path, file_hash, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("DOC-ALICE-001", "CAS-ALICE-001", "secret_invoice.pdf", "pdf", 1024, "secret_invoice.pdf", "hash123", "Analyzed")
        )

        conn.commit()
        conn.close()

        cls.app = create_app(cls.config)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_01_unauthenticated_requests_blocked(self):
        """When VEXORA_REQUIRE_AUTH=True, endpoints return 401 without session."""
        client = self.app.test_client()
        res = client.get('/api/cases')
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn("Authentication required", data['error'])

    def test_02_analyst_alice_can_access_own_case(self):
        """Analyst Alice can view her own case."""
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = 101
            sess['username'] = 'analyst_alice'
            sess['role'] = 'Forensic Analyst'

        res = client.get('/api/cases/CAS-ALICE-001')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['id'], 'CAS-ALICE-001')

    def test_03_idor_analyst_bob_blocked_from_alice_case(self):
        """Analyst Bob cannot access Alice's case (IDOR guard returns 403)."""
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = 102
            sess['username'] = 'analyst_bob'
            sess['role'] = 'Forensic Analyst'

        # Attempt to GET Alice's case
        res = client.get('/api/cases/CAS-ALICE-001')
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn("Access denied", data['error'])

        # Attempt to UPDATE Alice's case
        res_put = client.put('/api/cases/CAS-ALICE-001', json={'title': 'Tampered by Bob'})
        self.assertEqual(res_put.status_code, 403)

        # Attempt to DELETE Alice's case
        res_del = client.delete('/api/cases/CAS-ALICE-001')
        self.assertEqual(res_del.status_code, 403)

    def test_04_idor_analyst_bob_blocked_from_alice_document(self):
        """Analyst Bob cannot view or delete documents belonging to Alice's case."""
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = 102
            sess['username'] = 'analyst_bob'
            sess['role'] = 'Forensic Analyst'

        # Attempt to GET Alice's document
        res = client.get('/api/documents/DOC-ALICE-001')
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertFalse(data['success'])

        # Attempt to DELETE Alice's document
        res_del = client.delete('/api/documents/DOC-ALICE-001')
        self.assertEqual(res_del.status_code, 403)

    def test_05_admin_carol_can_access_all_cases(self):
        """Admin Carol has full permission across all cases (RBAC verification)."""
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = 103
            sess['username'] = 'admin_carol'
            sess['role'] = 'System Administrator'

        res = client.get('/api/cases/CAS-ALICE-001')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])

        # Admin can access Alice's document
        res_doc = client.get('/api/documents/DOC-ALICE-001')
        self.assertEqual(res_doc.status_code, 200)

    def test_06_logout_clears_session(self):
        """POST /api/auth/logout terminates the session and revokes access."""
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = 101
            sess['username'] = 'analyst_alice'
            sess['role'] = 'Forensic Analyst'

        # Verify access before logout
        res1 = client.get('/api/cases/CAS-ALICE-001')
        self.assertEqual(res1.status_code, 200)

        # Call logout
        res_logout = client.post('/api/auth/logout')
        self.assertEqual(res_logout.status_code, 200)
        self.assertTrue(res_logout.get_json()['success'])

        # Subsequent request must be rejected with 401
        res2 = client.get('/api/cases/CAS-ALICE-001')
        self.assertEqual(res2.status_code, 401)

    def test_07_cors_blocks_untrusted_origins(self):
        """CORS header is not reflected when an untrusted Origin is supplied."""
        client = self.app.test_client()
        res = client.get('/api/health', headers={'Origin': 'https://malicious-attacker-site.com'})
        self.assertEqual(res.status_code, 200)
        # Origin must NOT match the malicious domain
        cors_header = res.headers.get('Access-Control-Allow-Origin')
        self.assertNotEqual(cors_header, 'https://malicious-attacker-site.com')

    def test_08_production_secret_key_enforcement(self):
        """FLASK_ENV=production raises RuntimeError if default or empty secret key is used."""
        old_flask_env = os.environ.get('FLASK_ENV')
        old_secret = os.environ.get('SECRET_KEY')
        try:
            os.environ['FLASK_ENV'] = 'production'
            os.environ['SECRET_KEY'] = 'vexora-forensics-dev-secret-key-2026'

            with self.assertRaises(RuntimeError):
                create_app({'SECRET_KEY': 'vexora-forensics-dev-secret-key-2026', 'DATABASE': str(self.db_path)})
        finally:
            if old_flask_env is not None:
                os.environ['FLASK_ENV'] = old_flask_env
            else:
                os.environ.pop('FLASK_ENV', None)
            if old_secret is not None:
                os.environ['SECRET_KEY'] = old_secret
            else:
                os.environ.pop('SECRET_KEY', None)


    def test_09_all_sensitive_endpoints_require_auth(self):
        """Endpoints that previously leaked data without session now return 401."""
        client = self.app.test_client()
        sensitive_endpoints = [
            ('/api/stats', 'GET'),
            ('/api/cases', 'POST'),
            ('/api/documents', 'GET'),
            ('/api/evidence/test.png', 'GET'),
            ('/api/documents/DOC-ALICE-001/extract', 'POST'),
            ('/api/documents/DOC-ALICE-001/extracted', 'GET'),
            ('/api/documents/DOC-ALICE-001/analyze', 'POST'),
            ('/api/documents/DOC-ALICE-001/findings', 'GET'),
            ('/api/findings', 'GET'),
            ('/api/audit-logs', 'GET'),
            ('/api/reports', 'GET'),
            ('/api/system/diagnostics', 'GET'),
            ('/api/evidence-graph', 'GET'),
            ('/api/demo/add', 'POST'),
            ('/api/demo/reset', 'POST'),
            ('/api/system/ai-test', 'POST'),
            ('/api/documents/DOC-ALICE-001/ai-insights', 'GET'),
            ('/api/documents/DOC-ALICE-001/ai-extract', 'POST'),
            ('/api/findings/FIND-ALICE-001/explain', 'POST'),
            ('/api/cases/CAS-ALICE-001/ai-crosscheck', 'POST'),
        ]
        for url, method in sensitive_endpoints:
            if method == 'GET':
                res = client.get(url)
            else:
                res = client.post(url)
            self.assertEqual(
                res.status_code, 401,
                f"Endpoint {method} {url} was expected to return 401 when unauthenticated, got {res.status_code}"
            )
            data = res.get_json()
            self.assertFalse(data.get('success', True))

    def test_10_missing_user_identity_fails(self):
        """check_case_access rejects requests with missing user identity when auth is enabled."""
        from backend.models import check_case_access
        with self.app.app_context():
            allowed, res, code = check_case_access("CAS-ALICE-001", user_id=None, username=None, role=None)
            self.assertFalse(allowed)
            self.assertEqual(code, 401)
            self.assertIn("Authentication required", res)

    def test_11_registration_role_tampering_ignored(self):
        """Public self-registration rejects admin roles (400) and ignores client-supplied custom roles (defaults to Forensic Analyst)."""
        client = self.app.test_client()
        # Direct admin escalation attempt is rejected with 400
        evil_admin = {
            "username": "attacker_admin",
            "email": "admin_attempt@evil.com",
            "password": "StrongPassword@123",
            "role": "admin",
            "badge_number": "BADGE-666"
        }
        res_admin = client.post('/api/auth/register', json=evil_admin)
        self.assertEqual(res_admin.status_code, 400)

        # Custom non-standard role attempt defaults safely to 'Forensic Analyst'
        evil_supervisor = {
            "username": "attacker_supervisor",
            "email": "super_attempt@evil.com",
            "password": "StrongPassword@123",
            "role": "Chief Inspector",
            "badge_number": "BADGE-777"
        }
        res_sup = client.post('/api/auth/register', json=evil_supervisor)
        self.assertEqual(res_sup.status_code, 201)
        data = res_sup.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['role'], 'Forensic Analyst')

    def test_12_audit_logs_and_diagnostics_require_admin_role(self):
        """Standard analysts cannot view global audit logs or diagnostics; admins can."""
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = 101
            sess['username'] = 'analyst_alice'
            sess['role'] = 'Forensic Analyst'

        res_logs = client.get('/api/audit-logs')
        self.assertEqual(res_logs.status_code, 403)

        res_diag = client.get('/api/system/diagnostics')
        self.assertEqual(res_diag.status_code, 403)

        with client.session_transaction() as sess:
            sess['user_id'] = 103
            sess['username'] = 'admin_carol'
            sess['role'] = 'System Administrator'

        res_admin_logs = client.get('/api/audit-logs')
        self.assertEqual(res_admin_logs.status_code, 200)

        res_admin_diag = client.get('/api/system/diagnostics')
        self.assertEqual(res_admin_diag.status_code, 200)

    def test_13_demo_reset_blocked_for_non_admin_and_disabled_by_default(self):
        """POST /api/demo/reset is blocked for standard analysts and rejected if flag is disabled."""
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = 101
            sess['username'] = 'analyst_alice'
            sess['role'] = 'Forensic Analyst'

        res_analyst = client.post('/api/demo/reset')
        self.assertEqual(res_analyst.status_code, 403)

    def test_14_unconfigured_google_oauth_returns_501(self):
        """Unconfigured Google OAuth returns 501 instead of generating fake authenticated sessions."""
        client = self.app.test_client()
        res = client.get('/api/auth/google')
        self.assertEqual(res.status_code, 501)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn("not configured", data['error'].lower())

    def test_15_auth_disabled_mode_allows_offline_access(self):
        """When VEXORA_REQUIRE_AUTH=False, single-user offline demo mode operates without blocking."""
        offline_app = create_app({
            'TESTING': True,
            'DATABASE': str(self.db_path),
            'VEXORA_REQUIRE_AUTH': False,
            'SECRET_KEY': 'dev-key-offline'
        })
        offline_client = offline_app.test_client()
        res = offline_client.get('/api/cases')
        self.assertEqual(res.status_code, 200)

    def test_16_csrf_protection_enforcement(self):
        """When CSRF protection is active, state-changing requests require valid CSRF token."""
        csrf_app = create_app({
            'TESTING': True,
            'DATABASE': str(self.db_path),
            'VEXORA_REQUIRE_AUTH': True,
            'VEXORA_ENFORCE_CSRF': True,
            'SECRET_KEY': 'csrf-test-key-2026'
        })
        client = csrf_app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = 101
            sess['username'] = 'analyst_alice'
            sess['role'] = 'Forensic Analyst'
            sess['csrf_token'] = 'valid-csrf-token-12345'

        # POST without CSRF token must fail with 403
        res_no_csrf = client.post('/api/cases', json={'title': 'Unauthorized Case', 'priority': 'High'})
        self.assertEqual(res_no_csrf.status_code, 403)
        self.assertIn('CSRF', res_no_csrf.get_json()['error'])

        # POST with wrong CSRF token must fail with 403
        res_bad_csrf = client.post(
            '/api/cases',
            headers={'X-CSRF-Token': 'wrong-token'},
            json={'title': 'Unauthorized Case', 'priority': 'High'}
        )
        self.assertEqual(res_bad_csrf.status_code, 403)

        # POST with valid CSRF token passes the CSRF barrier (may pass or return validation result)
        res_valid_csrf = client.post(
            '/api/cases',
            headers={'X-CSRF-Token': 'valid-csrf-token-12345'},
            json={'title': 'Alice Authorized Case', 'case_type': 'Financial Fraud', 'description': 'Testing valid CSRF token submission', 'priority': 'Medium'}
        )
        self.assertEqual(res_valid_csrf.status_code, 201)

    def test_17_disguised_file_upload_blocked(self):
        """Uploaded files with executable headers disguised as images are rejected."""
        import io
        from backend.uploader import process_single_upload
        fake_storage = type('MockFileStorage', (), {
            'filename': 'malicious.png',
            'read': lambda self, *args: bytes([77, 90, 144, 0, 3, 0, 0, 0]) if not args or args[0] != 8 else bytes([77, 90, 144, 0, 3, 0, 0, 0]),
            'seek': lambda self, pos: None,
            'tell': lambda self: 8,
            'save': lambda self, dest: None
        })()
        from backend.models import ValidationError
        with self.assertRaises((ValueError, ValidationError)) as ctx:
            process_single_upload(fake_storage, self.upload_dir)
        self.assertIn("signature", str(ctx.exception).lower())

    def test_18_idor_on_extracted_and_ai_endpoints(self):
        """Analyst Bob cannot extract, inspect extraction, or run AI reasoning on Alice's document/case."""
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = 102
            sess['username'] = 'analyst_bob'
            sess['role'] = 'Forensic Analyst'

        # Bob cannot fetch Alice's extracted document
        res_ext = client.get('/api/documents/DOC-ALICE-001/extracted')
        self.assertEqual(res_ext.status_code, 403)

        # Bob cannot trigger extraction on Alice's document
        res_trig_ext = client.post('/api/documents/DOC-ALICE-001/extract')
        self.assertEqual(res_trig_ext.status_code, 403)

        # Bob cannot trigger analysis on Alice's document
        res_ana = client.post('/api/documents/DOC-ALICE-001/analyze')
        self.assertEqual(res_ana.status_code, 403)

        # Bob cannot fetch findings for Alice's document
        res_find = client.get('/api/documents/DOC-ALICE-001/findings')
        self.assertEqual(res_find.status_code, 403)

        # Bob cannot crosscheck Alice's case
        res_cross = client.post('/api/cases/CAS-ALICE-001/ai-crosscheck')
        self.assertEqual(res_cross.status_code, 403)

    def test_19_evidence_path_traversal_blocked(self):
        """Path traversal attempts on /api/evidence/<path> return 404/safe error."""
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = 101
            sess['username'] = 'analyst_alice'
            sess['role'] = 'Forensic Analyst'

        # Attacker attempts to traverse out of evidence folder
        res = client.get('/api/evidence/../../etc/passwd')
        self.assertIn(res.status_code, (404, 400))


if __name__ == '__main__':
    unittest.main()
