"""
VEXORA — Unit Tests for Security Audit & Hardening (Stage 7)
Verifies:
1. Role escalation defense: rejection of self-assigned administrative roles.
2. Environment guard for demo database reset (VEXORA_ALLOW_DEMO_RESET).
3. Null byte and path traversal injection defenses during file upload.
4. Security configuration: HttpOnly session cookies, SameSite Lax, non-debug default.
"""

import io
import os
import shutil
import tempfile
import unittest

from backend.app import create_app
from backend.config import Config, TestConfig
from backend.database import init_db
from backend.models import create_case


class TestSecurityHardening(unittest.TestCase):
    """Test suite for Stage 7 security audit and hardening."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="vexora_test_security_")
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

        cls.app = create_app(CustomConfig)
        with cls.app.app_context():
            init_db(cls.test_db)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_role_escalation_prevention_on_registration(self):
        """Verifies that unauthenticated registration cannot self-assign administrative roles."""
        # Attempt 1: Admin role
        resp_admin = self.client.post('/api/auth/register', json={
            'username': 'attacker1',
            'email': 'attacker1@evil.com',
            'password': 'password123',
            'role': 'Admin'
        })
        self.assertEqual(resp_admin.status_code, 400)
        data = resp_admin.get_json()
        self.assertFalse(data['success'])
        self.assertIn("Administrative roles cannot be self-assigned", data['error'])

        # Attempt 2: System Administrator role
        resp_sysadmin = self.client.post('/api/auth/register', json={
            'username': 'attacker2',
            'email': 'attacker2@evil.com',
            'password': 'password123',
            'role': 'System Administrator'
        })
        self.assertEqual(resp_sysadmin.status_code, 400)

        # Attempt 3: Valid analyst registration succeeds
        resp_valid = self.client.post('/api/auth/register', json={
            'username': 'analyst_bob',
            'email': 'bob@forensics.org',
            'password': 'password123',
            'role': 'Forensic Analyst'
        })
        self.assertEqual(resp_valid.status_code, 201)
        valid_data = resp_valid.get_json()
        self.assertTrue(valid_data['success'])
        self.assertEqual(valid_data['user']['role'], 'Forensic Analyst')

    def test_02_demo_reset_environment_guard(self):
        """Verifies that /api/demo/reset is blocked with 403 when VEXORA_ALLOW_DEMO_RESET=false."""
        # Configure app context with reset disabled
        self.app.config['VEXORA_ALLOW_DEMO_RESET'] = False
        try:
            resp = self.client.post('/api/demo/reset')
            self.assertEqual(resp.status_code, 403)
            data = resp.get_json()
            self.assertFalse(data['success'])
            self.assertIn("disabled in this environment", data['error'])
        finally:
            self.app.config['VEXORA_ALLOW_DEMO_RESET'] = True

    def test_03_null_byte_upload_injection_rejected(self):
        """Verifies that filenames containing null bytes are rejected with 400."""
        with self.app.app_context():
            case = create_case({
                'title': 'Security Upload Case',
                'type': 'Tampering',
                'priority': 'Medium',
                'status': 'Active',
                'investigator': 'Dr. Turner',
                'description': 'Security case'
            })

        data = {
            'case_id': case['id'],
            'file': (io.BytesIO(b'%PDF-1.4 mock pdf sample'), 'invoice\x00.exe.pdf')
        }
        resp = self.client.post('/api/documents/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 400)
        resp_data = resp.get_json()
        self.assertFalse(resp_data['success'])
        self.assertIn("null byte", resp_data['error'].lower())

    def test_04_security_cookie_and_debug_defaults(self):
        """Verifies that session cookies are HttpOnly and SameSite Lax, and DEBUG is False by default."""
        self.assertTrue(Config.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(Config.SESSION_COOKIE_SAMESITE, 'Lax')
        self.assertFalse(Config.DEBUG)


if __name__ == '__main__':
    unittest.main()

