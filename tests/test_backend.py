"""
VEXORA — Automated Backend & Database Test Suite
Tests SQLite database operations, REST API routes, input validation,
audit logging, and user authentication using an isolated in-memory database.
"""

import unittest
import json
import os
from pathlib import Path
from backend.app import create_app
from backend.config import TestConfig
from backend.database import get_db, init_db, seed_data, query_db

class VexoraBackendTestCase(unittest.TestCase):
    """Test suite covering core backend and database operations."""

    def setUp(self):
        """Prepares a fresh isolated Flask client and clean test SQLite database."""
        test_db = Path(TestConfig.DATABASE)
        if test_db.exists():
            try:
                test_db.unlink()
            except Exception:
                pass

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        """Cleans up the test database file after each test execution."""
        test_db = Path(TestConfig.DATABASE)
        if test_db.exists():
            try:
                test_db.unlink()
            except Exception:
                pass

    def test_health_check(self):
        """Verifies the /api/health endpoint returns 200 OK and healthy status."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertTrue(data['database']['connected'])

    def test_system_stats(self):
        """Verifies dashboard telemetry metrics aggregation from SQLite."""
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        stats = data['data']
        self.assertIn('total_cases', stats)
        self.assertIn('active_cases', stats)
        self.assertIn('total_documents', stats)
        self.assertIn('high_risk_rate_percent', stats)
        self.assertGreaterEqual(stats['total_cases'], 1)

    def test_list_cases(self):
        """Verifies listing cases with optional filters."""
        # Unfiltered list
        response = self.client.get('/api/cases')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['count'], 1)

        # Filter by priority
        crit_res = self.client.get('/api/cases?priority=Critical')
        self.assertEqual(crit_res.status_code, 200)
        crit_data = crit_res.get_json()
        for c in crit_data['data']:
            self.assertEqual(c['priority'], 'Critical')

    def test_create_and_retrieve_case(self):
        """Verifies creating an investigation case and retrieving it with associated details."""
        new_case_payload = {
            'title': 'Test Forensic Investigation Alpha',
            'type': 'Financial Fraud',
            'priority': 'Critical',
            'status': 'Active',
            'investigator': 'Dr. Alex Turner',
            'description': 'Automated test investigation for verifying persistence.'
        }
        create_res = self.client.post(
            '/api/cases',
            data=json.dumps(new_case_payload),
            content_type='application/json'
        )
        self.assertEqual(create_res.status_code, 201)
        created_data = create_res.get_json()
        self.assertTrue(created_data['success'])
        case_id = created_data['data']['id']
        self.assertTrue(case_id.startswith('CAS-'))

        # Retrieve specific case
        get_res = self.client.get(f'/api/cases/{case_id}')
        self.assertEqual(get_res.status_code, 200)
        retrieved_data = get_res.get_json()
        self.assertEqual(retrieved_data['data']['title'], new_case_payload['title'])
        self.assertEqual(retrieved_data['data']['priority'], 'Critical')

    def test_case_input_validation(self):
        """Verifies strict input validation rejecting empty or invalid payloads."""
        # Empty title
        bad_title_payload = {
            'title': '   ',
            'type': 'Financial Fraud',
            'priority': 'High',
            'status': 'Active'
        }
        res1 = self.client.post('/api/cases', data=json.dumps(bad_title_payload), content_type='application/json')
        self.assertEqual(res1.status_code, 400)
        self.assertIn('title', res1.get_json()['error'].lower())

        # Invalid priority
        bad_priority_payload = {
            'title': 'Valid Case Title Here',
            'type': 'Financial Fraud',
            'priority': 'SuperUrgent',  # Invalid enum
            'status': 'Active'
        }
        res2 = self.client.post('/api/cases', data=json.dumps(bad_priority_payload), content_type='application/json')
        self.assertEqual(res2.status_code, 400)
        self.assertIn('priority', res2.get_json()['error'].lower())

    def test_update_and_delete_case(self):
        """Verifies updating case status and subsequent deletion."""
        # Create case first
        create_res = self.client.post(
            '/api/cases',
            data=json.dumps({
                'title': 'Case To Be Updated',
                'type': 'Contract Tampering',
                'priority': 'Medium',
                'status': 'Active',
                'investigator': 'Elena Rostova'
            }),
            content_type='application/json'
        )
        case_id = create_res.get_json()['data']['id']

        # Update case
        update_res = self.client.put(
            f'/api/cases/{case_id}',
            data=json.dumps({'status': 'Solved', 'priority': 'Low'}),
            content_type='application/json'
        )
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.get_json()['data']['status'], 'Solved')

        # Delete case
        del_res = self.client.delete(f'/api/cases/{case_id}')
        self.assertEqual(del_res.status_code, 200)

        # Confirm 404 on get
        not_found_res = self.client.get(f'/api/cases/{case_id}')
        self.assertEqual(not_found_res.status_code, 404)

    def test_document_registration(self):
        """Verifies registering a document record and associating it with a case."""
        doc_payload = {
            'case_id': 'CAS-2026-0891',
            'filename': 'Test_Evidence_Invoice.pdf',
            'file_type': 'pdf',
            'file_size': 1048576,
            'category': 'Invoice',
            'classification_confidence': 96.5,
            'status': 'Pending'
        }
        res = self.client.post('/api/documents', data=json.dumps(doc_payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data['success'])
        doc_id = data['data']['id']

        # Retrieve document
        get_res = self.client.get(f'/api/documents/{doc_id}')
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.get_json()['data']['filename'], 'Test_Evidence_Invoice.pdf')

    def test_findings_creation_and_listing(self):
        """Verifies creating and querying forensic findings."""
        finding_payload = {
            'case_id': 'CAS-2026-0891',
            'title': 'Test Compression Artifact Inconsistency',
            'severity': 'High',
            'category': 'Compression Anomaly',
            'description': 'Discrepant quantization tables discovered in JPEG stream.',
            'confidence': 91.2
        }
        res = self.client.post('/api/findings', data=json.dumps(finding_payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.get_json()['success'])

        # List findings
        list_res = self.client.get('/api/findings?case_id=CAS-2026-0891')
        self.assertEqual(list_res.status_code, 200)
        self.assertGreaterEqual(list_res.get_json()['count'], 1)

    def test_audit_logs_retrieval(self):
        """Verifies that system events generate immutable audit records."""
        res = self.client.get('/api/audit-logs')
        self.assertEqual(res.status_code, 200)
        logs = res.get_json()['data']
        self.assertIsInstance(logs, list)
        self.assertGreaterEqual(len(logs), 1)

    def test_user_auth_flow(self):
        """Verifies user registration, password hashing, and login authentication."""
        # Register new analyst
        reg_payload = {
            'username': 'agent.smith',
            'email': 'smith@vexora.internal',
            'password': 'SecurePassword@123',
            'role': 'Digital Forensics Analyst',
            'badge_number': 'VEX-999'
        }
        reg_res = self.client.post('/api/auth/register', data=json.dumps(reg_payload), content_type='application/json')
        self.assertEqual(reg_res.status_code, 201)

        # Duplicate registration should return 409 Conflict
        dup_res = self.client.post('/api/auth/register', data=json.dumps(reg_payload), content_type='application/json')
        self.assertEqual(dup_res.status_code, 409)

        # Successful login
        login_payload = {
            'username': 'agent.smith',
            'password': 'SecurePassword@123'
        }
        login_res = self.client.post('/api/auth/login', data=json.dumps(login_payload), content_type='application/json')
        self.assertEqual(login_res.status_code, 200)
        self.assertTrue(login_res.get_json()['success'])

        # Failed login with bad password
        bad_login_payload = {
            'username': 'agent.smith',
            'password': 'WrongPassword123'
        }
        bad_login_res = self.client.post('/api/auth/login', data=json.dumps(bad_login_payload), content_type='application/json')
        self.assertEqual(bad_login_res.status_code, 401)

    def test_upload_single_pdf(self):
        """Verifies single PDF upload, SHA-256 hash generation, classification, and disk storage."""
        import io
        dummy_pdf_content = b"%PDF-1.4 mock content invoice test subtotal VAT payment details %%EOF"
        data = {
            'case_id': 'CAS-2026-0891',
            'file': (io.BytesIO(dummy_pdf_content), 'Apex_Vendor_Invoice_INV99.pdf')
        }
        res = self.client.post('/api/documents/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        res_data = res.get_json()
        self.assertTrue(res_data['success'])
        self.assertEqual(res_data['count'], 1)
        doc = res_data['data'][0]
        self.assertTrue(doc['id'].startswith('DOC-'))
        self.assertEqual(doc['filename'], 'Apex_Vendor_Invoice_INV99.pdf')
        self.assertEqual(doc['category'], 'Invoice')
        self.assertGreaterEqual(doc['classification_confidence'], 90.0)
        self.assertTrue(len(doc['file_hash']) == 64)  # SHA-256 hex length

    def test_upload_multiple_files(self):
        """Verifies batch upload of multiple documents in a single HTTP request."""
        import io
        doc1 = (io.BytesIO(b"%PDF-1.4 contract agreement terms %%EOF"), 'Partnership_Agreement.pdf')
        doc2 = (io.BytesIO(b"\x89PNG\r\n\x1a\n mock customs declaration image data"), 'Customs_Manifest_Port.png')
        data = {
            'case_id': 'CAS-2026-0888',
            'files': [doc1, doc2]
        }
        res = self.client.post('/api/documents/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        res_data = res.get_json()
        self.assertTrue(res_data['success'])
        self.assertEqual(res_data['count'], 2)
        categories = [d['category'] for d in res_data['data']]
        self.assertIn('Contract', categories)
        self.assertIn('Customs Declaration', categories)

    def test_upload_unsupported_file_type(self):
        """Verifies rejection of unsupported file extensions with HTTP 400."""
        import io
        data = {
            'file': (io.BytesIO(b"MZ executable binary payload"), 'malicious_tool.exe')
        }
        res = self.client.post('/api/documents/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        res_data = res.get_json()
        self.assertFalse(res_data['success'])
        self.assertIn('unsupported', res_data['error'].lower())

    def test_upload_empty_file(self):
        """Verifies rejection of empty (0-byte) files."""
        import io
        data = {
            'file': (io.BytesIO(b""), 'empty_invoice.pdf')
        }
        res = self.client.post('/api/documents/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        self.assertIn('empty', res.get_json()['error'].lower())

    def test_duplicate_filename_handling(self):
        """Verifies that uploading duplicate filenames preserves both with unique IDs and disk paths."""
        import io
        pdf_bytes = b"%PDF-1.4 mock content %%EOF"
        data1 = {'file': (io.BytesIO(pdf_bytes), 'Standard_Invoice.pdf')}
        res1 = self.client.post('/api/documents/upload', data=data1, content_type='multipart/form-data')
        self.assertEqual(res1.status_code, 201)
        doc1 = res1.get_json()['data'][0]

        data2 = {'file': (io.BytesIO(pdf_bytes), 'Standard_Invoice.pdf')}
        res2 = self.client.post('/api/documents/upload', data=data2, content_type='multipart/form-data')
        self.assertEqual(res2.status_code, 201)
        doc2 = res2.get_json()['data'][0]

        self.assertNotEqual(doc1['id'], doc2['id'])
        self.assertNotEqual(doc1['file_path'], doc2['file_path'])

    def test_download_and_delete_document(self):
        """Verifies streaming document download and subsequent deletion."""
        import io
        pdf_content = b"%PDF-1.4 Download stream verification sample %%EOF"
        data = {'file': (io.BytesIO(pdf_content), 'Download_Test_Document.pdf')}
        res = self.client.post('/api/documents/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        doc_id = res.get_json()['data'][0]['id']

        # Download document
        dl_res = self.client.get(f'/api/documents/{doc_id}/download')
        self.assertEqual(dl_res.status_code, 200)
        self.assertEqual(dl_res.data, pdf_content)
        dl_res.close()  # Close stream to release Windows file handle

        # Delete document
        del_res = self.client.delete(f'/api/documents/{doc_id}')
        self.assertEqual(del_res.status_code, 200)

        # Confirm 404
        dl_404 = self.client.get(f'/api/documents/{doc_id}/download')
        self.assertEqual(dl_404.status_code, 404)

if __name__ == '__main__':
    unittest.main()

