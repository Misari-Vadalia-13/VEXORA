"""
VEXORA — Phase H Test Suite
Verifies forensic stabilization and principled gating:
1. Born-digital genuine PDF produces zero IMG findings and records an Observation note.
2. Raster image with a pasted patch produces IMG findings with severity capped at Medium.
3. Embedded raster image inside a PDF is extracted and analyzed.
4. Startup flag and dependency status is correctly exposed via /api/system/diagnostics.
5. Copy-move ORB ignores repeated text letters while detecting duplicated graphical elements.
6. Heuristic image forensic rules in catalog are capped at Medium severity.
"""

import os
import io
import shutil
import tempfile
import unittest
import numpy as np
import cv2
from PIL import Image
import pymupdf as fitz

from backend.forensics_image import (
    run_image_forensics,
    check_error_level_analysis,
    check_noise_and_sharpness_inconsistency,
    check_copy_move_orb,
    check_signature_region,
    IMAGE_FORENSIC_RULES
)
from backend.banner import get_v2_features_status, check_tesseract_binary
from backend.app import create_app
from backend.config import TestConfig
from backend.database import init_db


class TestV2PhaseH(unittest.TestCase):
    """Test suite for Phase H stabilization and demo reliability."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="vexora_phase_h_test_")
        cls.test_db = os.path.join(cls.test_dir, "phase_h.db")
        cls.test_uploads = os.path.join(cls.test_dir, "uploads")
        cls.test_reports = os.path.join(cls.test_dir, "reports")
        os.makedirs(cls.test_uploads, exist_ok=True)
        os.makedirs(cls.test_reports, exist_ok=True)

        class PhaseHTestConfig(TestConfig):
            DATABASE = cls.test_db
            UPLOAD_FOLDER = cls.test_uploads
            REPORTS_FOLDER = cls.test_reports
            TESTING = True
            ENABLE_IMAGE_FORENSICS = True
            ENABLE_EXTENDED_FORENSICS = True
            ENABLE_CORRELATOR = True

        cls.config_class = PhaseHTestConfig
        cls.app = create_app(PhaseHTestConfig)
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            init_db(cls.test_db)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_born_digital_pdf_produces_zero_img_findings(self):
        """
        Principled Gate: A born-digital PDF with no embedded images must NEVER produce
        IMG-001, IMG-002, IMG-003, or IMG-004 findings.
        It must instead record a single Observation-level note explaining image forensics is not applicable.
        """
        # Create a vector PDF with pure digital text and zero embedded raster images
        pdf_path = os.path.join(self.test_dir, "clean_born_digital.pdf")
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text(fitz.Point(50, 100), "OFFICIAL BANK STATEMENT", fontsize=16)
        page.insert_text(fitz.Point(50, 150), "Account Holder: Enterprise Holdings LLC", fontsize=11)
        page.insert_text(fitz.Point(50, 180), "Closing Balance: $148,250.00", fontsize=11)
        page.insert_text(fitz.Point(50, 210), "All transactions verified and cleared.", fontsize=11)
        doc.save(pdf_path)
        doc.close()

        findings = run_image_forensics(pdf_path)

        # Must NOT produce any IMG rule findings
        img_rules = [f for f in findings if (f.get('rule_id') or '').startswith('IMG-')]
        self.assertEqual(len(img_rules), 0, f"Born-digital PDF produced unexpected IMG findings: {img_rules}")

        # Must produce exactly one observation note stating image forensics is not applicable
        self.assertEqual(len(findings), 1)
        note = findings[0]
        self.assertEqual(note.get('evidence_class'), 'Observation')
        self.assertEqual(note.get('status'), 'Observation')
        self.assertIn("born-digital", str(note.get('description', '')).lower())
        self.assertIn("not applicable", str(note.get('description', '')).lower())

    def test_02_pasted_patch_image_produces_img_findings_with_capped_severity(self):
        """
        An uploaded raster image with an inserted patch must still produce image forensic findings,
        and rule severities must be capped at 'Medium' due to their heuristic nature.
        """
        # Create test canvas and insert high-entropy patch
        img_path = os.path.join(self.test_dir, "patched_document.png")
        base = np.full((350, 350, 3), 235, dtype=np.uint8)
        cv2.putText(base, "Invoice Statement Baseline", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2)
        _, enc_base = cv2.imencode('.jpg', base, [cv2.IMWRITE_JPEG_QUALITY, 45])
        base_jpeg = cv2.imdecode(enc_base, cv2.IMREAD_COLOR)

        patch = np.random.randint(40, 230, (90, 90, 3), dtype=np.uint8)
        _, enc_patch = cv2.imencode('.jpg', patch, [cv2.IMWRITE_JPEG_QUALITY, 95])
        patch_jpeg = cv2.imdecode(enc_patch, cv2.IMREAD_COLOR)

        composite = base_jpeg.copy()
        composite[150:240, 150:240] = patch_jpeg
        cv2.imwrite(img_path, composite)

        findings = run_image_forensics(img_path)
        img_findings = [f for f in findings if (f.get('rule_id') or '').startswith('IMG-')]
        self.assertGreaterEqual(len(img_findings), 1, "Expected forensic anomaly from pasted patch")

        # Verify severities are capped at Medium
        for f in img_findings:
            self.assertIn(f.get('severity'), ['Medium', 'Low', 'Info'])
            self.assertIn("limitation", f.get('description', '').lower())

    def test_03_embedded_image_in_pdf_is_extracted_and_analyzed(self):
        """
        When a PDF contains embedded raster images, PyMuPDF must extract them
        and execute pixel forensics on the extracted image data.
        """
        # Generate an image with a spliced high-contrast patch
        canvas = np.full((320, 320, 3), 240, dtype=np.uint8)
        cv2.putText(canvas, "Original Scanned Receipt", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 40, 40), 1)
        # Spliced checkerboard patch for sharpness and ELA disparity
        for r in range(120, 220, 10):
            for c in range(120, 220, 10):
                if (r // 10 + c // 10) % 2 == 0:
                    canvas[r:r+10, c:c+10] = (20, 20, 20)

        _, buf = cv2.imencode('.png', canvas)
        img_bytes = buf.tobytes()

        # Embed image into a new PDF
        pdf_path = os.path.join(self.test_dir, "pdf_with_embedded_image.pdf")
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text(fitz.Point(50, 50), "Document with Embedded Scanned Receipt Attachment:", fontsize=12)
        rect = fitz.Rect(50, 80, 400, 430)
        page.insert_image(rect, stream=img_bytes)
        doc.save(pdf_path)
        doc.close()

        findings = run_image_forensics(pdf_path)

        # Embedded image must have been extracted and evaluated
        self.assertGreaterEqual(len(findings), 1)
        img_rule_ids = [f.get('rule_id') for f in findings if f.get('rule_id')]
        self.assertTrue(any(rid in ('IMG-001', 'IMG-002', 'IMG-003') for rid in img_rule_ids),
                        f"Expected IMG-001 or IMG-002 from embedded image, got {img_rule_ids}")

    def test_04_startup_flag_info_reported_in_diagnostics(self):
        """
        GET /api/system/diagnostics must return the status of all V2 feature flags
        and the availability state of the Tesseract OCR binary.
        """
        res = self.client.get('/api/system/diagnostics')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertTrue(data.get('success'))
        self.assertIn('v2_features', data)
        self.assertIn('tesseract_available', data)
        self.assertIn('tesseract_detail', data)

        v2 = data['v2_features']
        for flag in [
            'ENABLE_EVIDENCE_OVERLAY',
            'ENABLE_EXTENDED_FORENSICS',
            'ENABLE_IMAGE_FORENSICS',
            'ENABLE_CORRELATOR',
            'ENABLE_LLM',
            'VEXORA_STRICT_OCR',
            'VEXORA_LLM_REDACT'
        ]:
            self.assertIn(flag, v2, f"Expected {flag} in v2_features")

    def test_05_copymove_ignores_text_areas(self):
        """
        ORB copy-move detection must ignore keypoint matches across detected printed text lines,
        preventing false alarms on repeated characters.
        """
        # Canvas containing repeated text lines
        canvas = np.full((400, 500, 3), 250, dtype=np.uint8)
        cv2.putText(canvas, "Standard Corporate Transaction", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1)
        cv2.putText(canvas, "Standard Corporate Settlement", (30, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1)
        cv2.putText(canvas, "Account Balance: $10,000.00", (30, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1)
        cv2.putText(canvas, "Closing Balance: $10,000.00", (30, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1)

        findings = check_copy_move_orb(canvas, page_num=1)
        # Should not trigger false copy-move from repeated text characters
        self.assertEqual(len(findings), 0, f"Copy-move falsely triggered on text: {findings}")

    def test_06_rules_catalog_capped_at_medium(self):
        """
        Verifies that in IMAGE_FORENSIC_RULES, the heuristic rules (IMG-001, IMG-002, IMG-003)
        are capped at Medium severity.
        """
        for rid in ['IMG-001', 'IMG-002', 'IMG-003']:
            rule = IMAGE_FORENSIC_RULES[rid]
            self.assertEqual(rule['severity'], 'Medium', f"{rid} severity must be 'Medium'")


if __name__ == '__main__':
    unittest.main()
