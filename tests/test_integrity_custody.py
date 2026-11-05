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

    def test_audit_hash_chain_integrity(self):
        """Verifies cryptographic hash-chaining of audit logs (ISO/IEC 27037)."""
        from backend.models import log_audit, verify_audit_trail_integrity
        from backend.database import query_db

        with self.app.app_context():
            log_audit("TEST_ACTION_1", "case", "CAS-001", "Initial event", "Analyst 1")
            log_audit("TEST_ACTION_2", "document", "DOC-001", "Secondary event", "Analyst 2")
            log_audit("TEST_ACTION_3", "finding", "FND-001", "Tertiary event", "Analyst 3")

            is_valid, count, error = verify_audit_trail_integrity()
            self.assertTrue(is_valid, f"Audit chain should be valid, got error: {error}")
            self.assertGreaterEqual(count, 3)
            self.assertIsNone(error)

            # Inspect raw chain structure
            rows = query_db("SELECT id, prev_hash, event_hash FROM audit_logs ORDER BY id DESC LIMIT 3")
            self.assertEqual(len(rows), 3)
            # Row 0 prev_hash should equal Row 1 event_hash
            self.assertEqual(rows[0]['prev_hash'], rows[1]['event_hash'])
            self.assertEqual(rows[1]['prev_hash'], rows[2]['event_hash'])

    def test_audit_hash_chain_tamper_detection(self):
        """Verifies that unauthorized direct SQLite tampering breaks the hash chain."""
        from backend.models import log_audit, verify_audit_trail_integrity
        from backend.database import execute_db, query_db

        with self.app.app_context():
            log_audit("CHAIN_TEST_1", "case", "CAS-T1", "Event 1", "Investigator")
            log_audit("CHAIN_TEST_2", "case", "CAS-T1", "Event 2", "Investigator")
            log_audit("CHAIN_TEST_3", "case", "CAS-T1", "Event 3", "Investigator")

            # Tamper with Event 2 details in database without updating hash
            last_rows = query_db("SELECT id FROM audit_logs WHERE action = 'CHAIN_TEST_2'")
            self.assertTrue(len(last_rows) > 0)
            target_id = last_rows[0]['id']

            execute_db("UPDATE audit_logs SET details = 'MALICIOUS_TAMPERED_DETAILS' WHERE id = ?", (target_id,))

            is_valid, verified_count, error = verify_audit_trail_integrity()
            self.assertFalse(is_valid, "Tampered audit trail must fail verification")
            self.assertIn("Hash mismatch", error)

    def test_strict_ocr_data_separation(self):
        """Verifies strict data separation: extracted_text vs metadata vs visual observations."""
        import pymupdf as fitz
        from backend.extractor import extract_document_content
        import tempfile

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Original Ground Truth Text 12345")
        doc.set_metadata({'title': 'Contract Agreement', 'author': 'Lead Auditor'})

        temp_pdf = Path(TestConfig.BASE_DIR) / "demo_dataset" / "_temp_separation_test.pdf"
        try:
            doc.save(str(temp_pdf))
            doc.close()

            result = extract_document_content(str(temp_pdf))

            # 1. extracted_text / full_text must contain strictly verbatim extracted text
            self.assertIn("Original Ground Truth Text 12345", result['full_text'])
            self.assertNotIn("RULE-", result['full_text'])
            self.assertNotIn("[AI]", result['full_text'])
            self.assertNotIn("Synthetic", result['full_text'])

            # 2. Metadata must be held strictly in metadata dict
            self.assertEqual(result['metadata']['title'], 'Contract Agreement')
            self.assertEqual(result['metadata']['author'], 'Lead Auditor')

            # 3. Blocks must be structural dictionaries with bounding boxes
            self.assertGreaterEqual(len(result['pages'][0]['blocks']), 1)
            b = result['pages'][0]['blocks'][0]
            self.assertIn('bbox', b)
            self.assertIn('text', b)
            self.assertEqual(len(b['bbox']), 4)
        finally:
            if temp_pdf.exists():
                temp_pdf.unlink()

    def test_coordinate_transformation_under_rotation(self):
        """Verifies layout coordinates and viewport geometry under PDF page rotation."""
        import pymupdf as fitz
        from backend.extractor import extract_document_content

        doc = fitz.open()
        # Create standard page (A4: 595 x 842)
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 150), "Rotated Forensic Document Stamp 2026 Verification Evidence Text")
        # Apply 90 degree clockwise rotation
        page.set_rotation(90)

        temp_rot_pdf = Path(TestConfig.BASE_DIR) / "demo_dataset" / "_temp_rotation_test.pdf"
        try:
            doc.save(str(temp_rot_pdf))
            doc.close()

            result = extract_document_content(str(temp_rot_pdf))
            p0 = result['pages'][0]

            # In 90 degree rotation, PyMuPDF width/height reflect rotated dimensions (842 x 595)
            self.assertEqual(p0['rotation'], 90)
            self.assertEqual(p0['width'], 842.0)
            self.assertEqual(p0['height'], 595.0)

            # Bounding box coordinates must be non-negative and stay within rotated boundaries
            self.assertGreaterEqual(len(p0['blocks']), 1)
            bbox = p0['blocks'][0]['bbox']
            self.assertGreaterEqual(bbox[0], 0.0)
            self.assertGreaterEqual(bbox[1], 0.0)
            self.assertLessEqual(bbox[2], 842.0)
            self.assertLessEqual(bbox[3], 595.0)
        finally:
            if temp_rot_pdf.exists():
                temp_rot_pdf.unlink()


if __name__ == '__main__':
    unittest.main()
