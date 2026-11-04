"""
VEXORA — Evidence Integrity & Chain of Custody Unit Test Suite
Verifies ISO/IEC 27037-aligned digital evidence handling:
- Cryptographic SHA-256 verification (matching hash)
- Detection of post-ingest file tampering (mismatch)
- Graceful handling of missing evidence files on disk
- Chronological ordering and traceability of custody audit logs
"""

import io
import json
import unittest
from pathlib import Path
from backend.app import create_app
from backend.config import TestConfig


class VexoraIntegrityCustodyTestCase(unittest.TestCase):
    """Test suite covering Evidence Integrity & Chain of Custody endpoints."""

    def setUp(self):
        """Prepares an isolated test database and test client."""
        test_db = Path(TestConfig.DATABASE)
        if test_db.exists():
            try:
                test_db.unlink()
            except Exception:
                pass

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        """Cleans up the test database file after each test."""
        test_db = Path(TestConfig.DATABASE)
        if test_db.exists():
            try:
                test_db.unlink()
            except Exception:
                pass

    def _upload_test_doc(self, case_id="CAS-2026-0891", filename="Forensic_Invoice_Test.pdf", content=None):
        """Helper to upload a valid test document and return the doc dict."""
        if content is None:
            demo_file = Path(TestConfig.BASE_DIR) / "demo_dataset" / "genuine_01_invoice.pdf"
            if demo_file.exists():
                content = demo_file.read_bytes()
            else:
                try:
                    import pymupdf as fitz
                except ImportError:
                    import fitz
                doc = fitz.open()
                page = doc.new_page()
                page.insert_text((50, 50), "VEXORA Evidence Document Sample")
                content = doc.tobytes()
                doc.close()

        data = {
            'case_id': case_id,
            'user': 'Lead Forensic Investigator',
            'files': (io.BytesIO(content), filename)
        }
        res = self.client.post('/api/documents/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        res_json = res.get_json()
        self.assertTrue(res_json['success'])
        return res_json['data'][0]

    def test_integrity_check_matching_hash(self):
        """Verifies GET /api/documents/<id>/integrity confirms matching SHA-256 for untampered file."""
        doc = self._upload_test_doc(filename="Integrity_Clean_Doc.pdf")
        doc_id = doc['id']
        stored_hash = doc['file_hash']
        self.assertEqual(len(stored_hash), 64)

        # Execute integrity verification
        res = self.client.get(f'/api/documents/{doc_id}/integrity')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertTrue(data['success'])
        self.assertEqual(data['document_id'], doc_id)
        self.assertTrue(data['match'])
        self.assertEqual(data['status'], 'verified')
        self.assertEqual(data['stored_hash'].lower(), stored_hash.lower())
        self.assertEqual(data['current_hash'].lower(), stored_hash.lower())
        self.assertIn('checked_at', data)

        # Verify audit log recorded INTEGRITY_CHECK
        audit_res = self.client.get('/api/audit-logs')
        self.assertEqual(audit_res.status_code, 200)
        audit_data = audit_res.get_json()
        actions = [log['action'] for log in audit_data['data'] if log.get('entity_id') == doc_id]
        self.assertIn('INTEGRITY_CHECK', actions)

    def test_integrity_check_tampered_file(self):
        """Verifies GET /api/documents/<id>/integrity flags mismatch when file bytes are modified on disk."""
        doc = self._upload_test_doc(filename="Integrity_Tamper_Doc.pdf")
        doc_id = doc['id']
        stored_hash = doc['file_hash']

        # Find the physical file on disk
        file_path = Path(doc['file_path'])
        if not file_path.is_absolute():
            file_path = Path(TestConfig.BASE_DIR) / file_path
        if not file_path.exists():
            file_path = Path(TestConfig.UPLOAD_FOLDER) / Path(doc['file_path']).name

        self.assertTrue(file_path.exists(), f"Evidence file must exist on disk: {file_path}")

        # Tamper with file contents on disk
        with open(file_path, 'ab') as f:
            f.write(b"\n%% TAMPERED_INJECTED_PAYLOAD_BYTE_STREAM %%")

        # Execute integrity verification
        res = self.client.get(f'/api/documents/{doc_id}/integrity')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertTrue(data['success'])
        self.assertEqual(data['document_id'], doc_id)
        self.assertFalse(data['match'])
        self.assertEqual(data['status'], 'tampered')
        self.assertEqual(data['stored_hash'].lower(), stored_hash.lower())
        self.assertNotEqual(data['current_hash'].lower(), stored_hash.lower())

        # Cleanup tampered file
        try:
            file_path.unlink()
        except Exception:
            pass

    def test_integrity_check_missing_file(self):
        """Verifies GET /api/documents/<id>/integrity handles a missing file without crashing."""
        doc = self._upload_test_doc(filename="Integrity_Missing_Doc.pdf")
        doc_id = doc['id']

        # Remove physical file from disk to simulate loss of evidence file
        file_path = Path(doc['file_path'])
        if not file_path.is_absolute():
            file_path = Path(TestConfig.BASE_DIR) / file_path
        if not file_path.exists():
            file_path = Path(TestConfig.UPLOAD_FOLDER) / Path(doc['file_path']).name

        if file_path.exists():
            file_path.unlink()

        # Execute integrity verification
        res = self.client.get(f'/api/documents/{doc_id}/integrity')
        self.assertEqual(res.status_code, 404)
        data = res.get_json()

        self.assertFalse(data['success'])
        self.assertFalse(data['match'])
        self.assertEqual(data['status'], 'missing')
        self.assertIn('error', data)

        # Verify audit log recorded INTEGRITY_CHECK_FAILED
        audit_res = self.client.get('/api/audit-logs')
        self.assertEqual(audit_res.status_code, 200)
        audit_data = audit_res.get_json()
        actions = [log['action'] for log in audit_data['data'] if log.get('entity_id') == doc_id]
        self.assertIn('INTEGRITY_CHECK_FAILED', actions)

    def test_custody_endpoint_ordering(self):
        """Verifies GET /api/documents/<id>/custody returns chronological audit trail for the document."""
        doc = self._upload_test_doc(filename="Custody_Chronology_Doc.pdf")
        doc_id = doc['id']

        # Perform lifecycle operations
        self.client.post(f'/api/documents/{doc_id}/extract', data=json.dumps({'user': 'Investigator 1'}), content_type='application/json')
        self.client.post(f'/api/documents/{doc_id}/analyze', data=json.dumps({'user': 'Forensic Lead'}), content_type='application/json')
        self.client.get(f'/api/documents/{doc_id}/integrity')

        # Retrieve custody chain
        res = self.client.get(f'/api/documents/{doc_id}/custody')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertTrue(data['success'])
        self.assertEqual(data['document_id'], doc_id)
        self.assertEqual(data['stored_hash'], doc['file_hash'])
        self.assertGreaterEqual(data['count'], 4)
        events = data['events']
        self.assertGreaterEqual(len(events), 4)

        # Check chronological ordering: timestamps must be non-decreasing
        timestamps = [e['timestamp'] for e in events]
        self.assertEqual(timestamps, sorted(timestamps))

        # Check that expected lifecycle milestones appear
        actions = [e['action'] for e in events]
        self.assertIn('DOCUMENT_UPLOAD', actions)
        self.assertIn('DOCUMENT_EXTRACTED', actions)
        self.assertIn('DOCUMENT_ANALYZED', actions)
        self.assertIn('INTEGRITY_CHECK', actions)

        # Each event must have actor, action, timestamp, and details
        for ev in events:
            self.assertIn('actor', ev)
            self.assertIn('action', ev)
            self.assertIn('timestamp', ev)
            self.assertIn('details', ev)


if __name__ == '__main__':
    unittest.main()
