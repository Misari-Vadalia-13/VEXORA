"""
VEXORA — V2 Phase A Unit & Integration Tests: Visual Evidence Overlay
Verifies coordinate parsing, overlay rendering for PDFs and images,
evidence image endpoints, and dossier generation with/without ENABLE_EVIDENCE_OVERLAY.
"""

import os
import json
import tempfile
import shutil
import unittest
from pathlib import Path
from PIL import Image

import pymupdf as fitz

from backend.app import create_app
from backend.config import Config, TestConfig
from backend.database import init_db
from backend.evidence import parse_coordinates, render_page_overlay, get_finding_evidence_image
from backend.models import create_case, create_document, create_finding, get_case_by_id
from backend.reporter import generate_dossier_pdf


class TestVisualEvidenceOverlay(unittest.TestCase):
    """Test suite for Phase A visual evidence overlay features."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="vexora_phase_a_test_")
        cls.test_db = os.path.join(cls.test_dir, "phase_a.db")
        cls.test_uploads = os.path.join(cls.test_dir, "uploads")
        cls.test_reports = os.path.join(cls.test_dir, "reports")
        os.makedirs(cls.test_uploads, exist_ok=True)
        os.makedirs(cls.test_reports, exist_ok=True)

        class PhaseATestConfig(TestConfig):
            DATABASE = cls.test_db
            UPLOAD_FOLDER = cls.test_uploads
            REPORTS_FOLDER = cls.test_reports
            TESTING = True
            ENABLE_EVIDENCE_OVERLAY = False

        cls.config_class = PhaseATestConfig
        cls.app = create_app(PhaseATestConfig)
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            init_db(cls.test_db)

        # 1. Generate a test PDF with text on page 1
        cls.test_pdf_path = os.path.join(cls.test_uploads, "sample_invoice.pdf")
        doc = fitz.open()
        p = doc.new_page(width=595, height=842)
        p.insert_text(fitz.Point(72, 100), "INVOICE #INV-2026-001", fontsize=14)
        p.insert_text(fitz.Point(72, 140), "Total Balance Due: $9,950,000.00", fontsize=12)
        doc.save(cls.test_pdf_path)
        doc.close()

        # 2. Generate a test raster image (PNG)
        cls.test_img_path = os.path.join(cls.test_uploads, "sample_receipt.png")
        img = Image.new("RGB", (400, 300), color=(240, 240, 245))
        img.save(cls.test_img_path)

        # 3. Seed test case and documents in DB
        with cls.app.app_context():
            cls.test_case = create_case({
                'title': 'Phase A Evidence Case',
                'type': 'Financial Audit',
                'priority': 'High',
                'status': 'Active',
                'investigator': 'Lead Reviewer',
                'description': 'Test case for visual evidence overlay'
            })
            cls.case_id = cls.test_case['id']

            # Register PDF document
            cls.pdf_doc = create_document({
                'case_id': cls.case_id,
                'filename': 'sample_invoice.pdf',
                'file_type': 'pdf',
                'file_size': os.path.getsize(cls.test_pdf_path),
                'file_path': cls.test_pdf_path,
                'file_hash': 'abc123pdfhash',
                'category': 'Commercial Invoice',
                'status': 'Analyzed'
            })
            cls.pdf_doc_id = cls.pdf_doc['id']

            # Register Image document
            cls.img_doc = create_document({
                'case_id': cls.case_id,
                'filename': 'sample_receipt.png',
                'file_type': 'png',
                'file_size': os.path.getsize(cls.test_img_path),
                'file_path': cls.test_img_path,
                'file_hash': 'abc123imghash',
                'category': 'Receipt',
                'status': 'Analyzed'
            })
            cls.img_doc_id = cls.img_doc['id']

            # Finding WITH coordinates (visual finding)
            cls.visual_finding = create_finding({
                'case_id': cls.case_id,
                'document_id': cls.pdf_doc_id,
                'title': 'Discrepant Font Family Detected',
                'severity': 'High',
                'category': 'Visual Formatting',
                'description': "Text span 'Total Balance Due' rendered with unexpected font family.",
                'confidence': 0.88,
                'status': 'Unresolved',
                'page_number': 1,
                'coordinates': [72.0, 130.0, 320.0, 145.0],
                'rule_id': 'RULE-VIS-001',
                'evidence': 'Font Courier vs Helvetica'
            })
            cls.visual_finding_id = cls.visual_finding['id']

            # Finding WITHOUT coordinates (contextual finding)
            cls.contextual_finding = create_finding({
                'case_id': cls.case_id,
                'document_id': cls.pdf_doc_id,
                'title': 'Chronological Sequence Inconsistency',
                'severity': 'Medium',
                'category': 'Contextual Inconsistency',
                'description': 'Billing due date precedes invoice creation date.',
                'confidence': 0.91,
                'status': 'Unresolved',
                'page_number': 1,
                'coordinates': None,
                'rule_id': 'RULE-CTX-003',
                'evidence': 'Issue: 2026-03-20 vs Due: 2026-03-10'
            })
            cls.contextual_finding_id = cls.contextual_finding['id']

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # =========================================================================
    # 1. Coordinate Parsing Tests
    # =========================================================================

    def test_parse_coordinates(self):
        """Verifies robust parsing across lists, JSON strings, and invalid inputs."""
        # Valid list
        self.assertEqual(parse_coordinates([10, 20, 30, 40]), [10.0, 20.0, 30.0, 40.0])
        # Valid JSON string
        self.assertEqual(parse_coordinates("[72.5, 100.2, 250.0, 115.8]"), [72.5, 100.2, 250.0, 115.8])
        # Comma-separated string
        self.assertEqual(parse_coordinates("50, 60, 70, 80"), [50.0, 60.0, 70.0, 80.0])
        # Empty or None
        self.assertIsNone(parse_coordinates(None))
        self.assertIsNone(parse_coordinates(""))
        self.assertIsNone(parse_coordinates("None"))
        self.assertIsNone(parse_coordinates("[10, 20]"))  # Incomplete box

    # =========================================================================
    # 2. Page Overlay Rendering Tests (PDF & Image)
    # =========================================================================

    def test_render_pdf_page_overlay(self):
        """Renders PDF page with finding bounding box to PNG bytes."""
        png_bytes = render_page_overlay(
            self.test_pdf_path,
            page_number=1,
            findings=[self.visual_finding],
            zoom=2.0
        )
        self.assertIsInstance(png_bytes, bytes)
        self.assertTrue(len(png_bytes) > 1000)
        # Check standard PNG magic bytes header
        self.assertEqual(png_bytes[:8], b'\x89PNG\r\n\x1a\n')

    def test_render_image_overlay(self):
        """Renders raster image with bounding box to PNG bytes."""
        img_finding = {
            'rule_id': 'RULE-VIS-005',
            'severity': 'Medium',
            'page_number': 1,
            'coordinates': [20, 30, 200, 150]
        }
        png_bytes = render_page_overlay(
            self.test_img_path,
            page_number=1,
            findings=[img_finding]
        )
        self.assertIsInstance(png_bytes, bytes)
        self.assertEqual(png_bytes[:8], b'\x89PNG\r\n\x1a\n')

    def test_render_clean_page_when_no_findings(self):
        """Renders clean page when findings list is empty."""
        png_bytes = render_page_overlay(self.test_pdf_path, page_number=1, findings=[])
        self.assertIsInstance(png_bytes, bytes)
        self.assertEqual(png_bytes[:8], b'\x89PNG\r\n\x1a\n')

    # =========================================================================
    # 3. REST API Endpoint Tests
    # =========================================================================

    def test_api_finding_evidence_image_success(self):
        """GET /api/findings/<id>/evidence-image returns 200 image/png for visual finding."""
        res = self.client.get(f"/api/findings/{self.visual_finding_id}/evidence-image")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'image/png')
        self.assertTrue(len(res.data) > 1000)
        self.assertEqual(res.data[:8], b'\x89PNG\r\n\x1a\n')

    def test_api_finding_evidence_image_no_coordinates_returns_json(self):
        """GET /api/findings/<id>/evidence-image returns clear JSON when finding has no box."""
        res = self.client.get(f"/api/findings/{self.contextual_finding_id}/evidence-image")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'application/json')
        data = res.get_json()
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('code'), 'NO_COORDINATES')
        self.assertIn('No visual bounding box', data.get('error', ''))

    def test_api_finding_evidence_image_not_found(self):
        """GET /api/findings/nonexistent/evidence-image returns 404 JSON."""
        res = self.client.get("/api/findings/FND-9999-999/evidence-image")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertFalse(data.get('success'))
        self.assertEqual(data.get('code'), 'NOT_FOUND')

    def test_api_document_page_overlay_endpoint(self):
        """GET /api/documents/<id>/pages/<n>/overlay returns 200 image/png."""
        res = self.client.get(f"/api/documents/{self.pdf_doc_id}/pages/1/overlay")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'image/png')
        self.assertEqual(res.data[:8], b'\x89PNG\r\n\x1a\n')

    def test_api_document_page_overlay_not_found(self):
        """GET /api/documents/nonexistent/pages/1/overlay returns 404 JSON."""
        res = self.client.get("/api/documents/DOC-NONEXISTENT/pages/1/overlay")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertFalse(data.get('success'))

    # =========================================================================
    # 4. Dossier Integration & Feature Flag Tests
    # =========================================================================

    def test_dossier_generation_with_flag_off(self):
        """Dossier report generation succeeds normally when ENABLE_EVIDENCE_OVERLAY is False."""
        Config.ENABLE_EVIDENCE_OVERLAY = False
        with self.app.app_context():
            res = generate_dossier_pdf(self.case_id)
            self.assertTrue(res['success'])
            self.assertTrue(os.path.exists(res['file_path']))

    def test_dossier_generation_with_flag_on(self):
        """Dossier report generation embeds evidence appendix when ENABLE_EVIDENCE_OVERLAY is True."""
        import time
        time.sleep(1.05)
        Config.ENABLE_EVIDENCE_OVERLAY = True
        try:
            with self.app.app_context():
                res = generate_dossier_pdf(self.case_id)
                self.assertTrue(res['success'])
                self.assertTrue(os.path.exists(res['file_path']))
                # Check that generated PDF is valid and has pages
                doc = fitz.open(res['file_path'])
                self.assertTrue(len(doc) >= 1)
                doc.close()
        finally:
            Config.ENABLE_EVIDENCE_OVERLAY = False


if __name__ == '__main__':
    unittest.main()
