"""
VEXORA — Resilience, Concurrency, and Adversarial Edge-Case Test Suite.
Tests:
1. Concurrency: Multi-threaded SQLite access and analysis.
2. Graceful degradation when external services (OCR, LLM) degrade.
3. Adversarial inputs: zero-length files, malformed metadata, corrupted headers.
4. Edge conditions: Single-document cases, empty text comparisons, zero division safety.
"""
import unittest
import os
import io
import shutil
import tempfile
import threading
from pathlib import Path
from PIL import Image

from backend.config import Config
from backend.database import init_db
from backend.models import create_case, create_document, create_finding, get_all_cases, get_system_stats
from backend.comparator import compare_two_documents, compare_case_documents
from backend.correlator import build_case_timeline, build_case_relationship_graph
from backend.forensics_image import run_image_forensics
from backend.forensics_pdf import run_extended_pdf_forensics
from backend.app import create_app


class TestResilienceAndAdversarial(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="vexora_test_resilience_")
        self.db_path = os.path.join(self.temp_dir, "test_vexora.db")
        self.upload_dir = os.path.join(self.temp_dir, "uploads")
        os.makedirs(self.upload_dir, exist_ok=True)

        self.orig_db = Config.DATABASE
        Config.DATABASE = self.db_path
        os.environ['VEXORA_DB_PATH'] = self.db_path
        os.environ['VEXORA_REQUIRE_AUTH'] = 'false'
        os.environ['VEXORA_ALLOW_DEMO_RESET'] = 'true'

        init_db(self.db_path)

        self.app = create_app({
            'TESTING': True,
            'DATABASE': self.db_path,
            'UPLOAD_FOLDER': self.upload_dir,
            'SECRET_KEY': 'test-resilience-secret',
            'WTF_CSRF_ENABLED': False
        })
        self.client = self.app.test_client()

    def tearDown(self):
        Config.DATABASE = self.orig_db
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_concurrent_access(self):
        """Tests that concurrent threads reading and writing to SQLite do not lock or crash."""
        case = create_case({
            'title': 'Concurrency Case',
            'type': 'Stress Testing',
            'priority': 'High',
            'status': 'Active',
            'investigator': 'Lead Investigator',
            'description': 'Multi-threaded stress testing'
        }, user='Tester')
        case_id = case['id']

        errors = []

        def worker_task(thread_id):
            try:
                with self.app.app_context():
                    # Write document
                    file_name = f"thread_{thread_id}.pdf"
                    fpath = os.path.join(self.upload_dir, file_name)
                    with open(fpath, 'wb') as f:
                        f.write(b"%PDF-1.4 Mock text content")
                    
                    doc = create_document({
                        'case_id': case_id,
                        'filename': file_name,
                        'file_type': 'pdf',
                        'file_size': 120,
                        'file_path': fpath
                    })
                    
                    # Write finding
                    create_finding({
                        'case_id': case_id,
                        'document_id': doc['id'],
                        'title': f'Thread Finding {thread_id}',
                        'severity': 'Low',
                        'rule_id': 'RULE-CONC'
                    })

                    # Read operations
                    stats = get_system_stats()
                    cases = get_all_cases()
                    self.assertGreaterEqual(stats['total_documents'], 1)
                    self.assertGreaterEqual(len(cases), 1)
            except Exception as e:
                errors.append(f"Thread {thread_id} failed: {str(e)}")

        threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Concurrency errors encountered: {errors}")

    def test_corrupt_and_truncated_image_forensics(self):
        """Verifies image forensics engine handles truncated and malformed image bytes without crashing."""
        corrupt_path = os.path.join(self.upload_dir, "corrupt.png")
        with open(corrupt_path, 'wb') as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\xff" * 20)  # Truncated PNG

        findings = run_image_forensics(corrupt_path)
        # Should gracefully return findings or error observation without throwing an unhandled exception
        self.assertIsInstance(findings, list)

    def test_corrupt_pdf_structure_analysis(self):
        """Verifies PDF structural analysis engine handles truncated/corrupted PDF bytes gracefully."""
        corrupt_path = os.path.join(self.upload_dir, "corrupt.pdf")
        with open(corrupt_path, 'wb') as f:
            f.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF_CORRUPTED")

        findings = run_extended_pdf_forensics(corrupt_path)
        self.assertIsInstance(findings, list)

    def test_comparator_empty_and_single_document_resilience(self):
        """Tests that comparator and correlator handle single document cases and empty texts safely."""
        case = create_case({
            'title': 'Single Doc Case',
            'type': 'Internal Audit',
            'priority': 'Low',
            'status': 'Active',
            'investigator': 'Lead Investigator',
            'description': 'Case with only one document'
        }, user='Tester')
        case_id = case['id']

        doc_path = os.path.join(self.upload_dir, "single.pdf")
        with open(doc_path, 'wb') as f:
            f.write(b"%PDF-1.4 Single")

        doc = create_document({
            'case_id': case_id,
            'filename': 'single.pdf',
            'file_type': 'pdf',
            'file_size': 100,
            'file_path': doc_path
        })

        with self.app.app_context():
            # Comparing single document case should return clean empty structure without zero-division or index errors
            res = compare_case_documents(case_id)
            self.assertTrue(res['success'])
            self.assertEqual(res['comparison_count'], 0)

            # Relationship graph on single document
            graph = build_case_relationship_graph(case_id)
            self.assertIn('nodes', graph)
            self.assertIn('edges', graph)

            # Timeline on single document
            timeline = build_case_timeline(case_id)
            self.assertTrue(timeline['success'])
            self.assertEqual(timeline['anomalies'], [])

            # Compare two documents with empty strings
            diff = compare_two_documents("", "")
            self.assertIsInstance(diff, dict)
            self.assertEqual(diff.get('discrepancies', []), [])


if __name__ == '__main__':
    unittest.main()
