"""
VEXORA — Unit Tests for Enhanced Image & PDF Structural Forensics (Stage 4)
Tests:
1. IMG-005 EXIF metadata extraction, editor signatures, date divergence, and missing EXIF.
2. IMG-001 Error Level Analysis (ELA) visual difference map persistence and /api/evidence endpoint.
3. IMG-003 Copy-move detection tightening against collinear / periodic patterns.
4. PDF-002 Incremental updates with /Prev cross-reference pointer verification.
5. PDF-004 Vector text overprinting on scanned page backgrounds.
6. PDF-006 Suspicious PDF dictionary objects (/JavaScript, /Launch, /EmbeddedFiles).
"""

import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image, ExifTags
except ImportError:
    Image = None
    ExifTags = None

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

from backend.app import create_app
from backend.config import Config, TestConfig
from backend.database import init_db
from backend.evidence_class import get_evidence_class
from backend.forensics_image import (
    IMAGE_FORENSIC_RULES,
    check_error_level_analysis,
    check_copy_move_orb,
    check_exif_metadata,
    run_image_forensics
)
from backend.forensics_pdf import (
    EXTENDED_PDF_RULES,
    check_incremental_updates,
    check_embedded_images_and_resolution,
    check_suspicious_pdf_objects,
    run_extended_pdf_forensics
)


class TestImageForensicsEnhancements(unittest.TestCase):
    """Verifies Stage 4 image forensics capabilities: EXIF, ELA persistence, copy-move tightening."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="vexora_test_img_forensics_")
        cls.uploads_dir = os.path.join(cls.test_dir, "uploads")
        cls.reports_dir = os.path.join(cls.test_dir, "reports")
        cls.test_db = os.path.join(cls.test_dir, "test.db")
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

    def test_img_005_catalog_entry(self):
        """Verifies IMG-005 is cataloged with severity Low and evidence class Observation."""
        self.assertIn('IMG-005', IMAGE_FORENSIC_RULES)
        rule = IMAGE_FORENSIC_RULES['IMG-005']
        self.assertEqual(rule['severity'], 'Low')
        self.assertEqual(rule['evidence_class'], 'Observation')
        self.assertEqual(get_evidence_class('IMG-005'), 'Observation')

    def test_img_005_editor_signature_detected(self):
        """Verifies detection of third-party graphic editing software in EXIF."""
        if Image is None or ExifTags is None:
            self.skipTest("Pillow not available")

        img = Image.new("RGB", (120, 120), color=(200, 200, 200))
        exif = img.getexif()
        # Tag 305 is Software
        exif[305] = "Adobe Photoshop 2024"
        exif[306] = "2026:01:15 12:00:00"

        img_path = os.path.join(self.test_dir, "photoshop_test.jpg")
        img.save(img_path, format="JPEG", exif=exif)
        img.close()

        findings = check_exif_metadata(img_path, page_num=1)
        self.assertGreaterEqual(len(findings), 1)
        ed_finding = next((f for f in findings if "Photoshop" in f['title']), None)
        self.assertIsNotNone(ed_finding)
        self.assertEqual(ed_finding['rule_id'], 'IMG-005')
        self.assertEqual(ed_finding['severity'], 'Medium')
        self.assertEqual(ed_finding['evidence_class'], 'Observation')
        self.assertIn("Photoshop", ed_finding['description'])

    def test_img_005_date_divergence_detected(self):
        """Verifies detection of divergence between capture date and modification date."""
        if Image is None or ExifTags is None:
            self.skipTest("Pillow not available")

        img = Image.new("RGB", (120, 120), color=(180, 180, 180))
        exif = img.getexif()
        # DateTime is 306
        exif[306] = "2026:11:04 15:00:00"
        # Sub-IFD for DateTimeOriginal
        if hasattr(ExifTags, 'IFD') and hasattr(ExifTags.IFD, 'Exif'):
            sub_ifd = exif.get_ifd(ExifTags.IFD.Exif)
            sub_ifd[36867] = "2024:05:10 09:30:00"
        else:
            sub_ifd = exif.get_ifd(0x8769)
            sub_ifd[36867] = "2024:05:10 09:30:00"

        img_path = os.path.join(self.test_dir, "divergent_date.jpg")
        img.save(img_path, format="JPEG", exif=exif)
        img.close()

        findings = check_exif_metadata(img_path, page_num=1)
        date_finding = next((f for f in findings if "Date Divergence" in f['title']), None)
        self.assertIsNotNone(date_finding)
        self.assertEqual(date_finding['rule_id'], 'IMG-005')
        self.assertEqual(date_finding['evidence_class'], 'Inconsistency')

    def test_img_005_missing_exif_on_jpeg(self):
        """Verifies that missing EXIF on a bare JPEG is recorded as an investigative observation."""
        if Image is None:
            self.skipTest("Pillow not available")

        img = Image.new("RGB", (100, 100), color=(240, 240, 240))
        img_path = os.path.join(self.test_dir, "no_exif.jpg")
        img.save(img_path, format="JPEG")
        img.close()

        findings = check_exif_metadata(img_path, file_path=img_path, page_num=1)
        missing_finding = next((f for f in findings if "EXIF Provenance Metadata Absent" in f['title']), None)
        self.assertIsNotNone(missing_finding)
        self.assertEqual(missing_finding['rule_id'], 'IMG-005')
        self.assertEqual(missing_finding['severity'], 'Low')
        self.assertEqual(missing_finding['evidence_class'], 'Observation')
        self.assertIn("investigative indicator", missing_finding['description'])

    def test_img_001_ela_visualization_persistence_and_serving(self):
        """Verifies that ELA generates and saves a visual error map and the /api/evidence endpoint serves it."""
        if cv2 is None or np is None or Image is None:
            self.skipTest("Computer vision dependencies not available")

        # Create base canvas heavily compressed at Q40
        base = np.full((320, 320, 3), 220, dtype=np.uint8)
        cv2.putText(base, "Official Statement", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 40), 2)
        _, enc_base = cv2.imencode('.jpg', base, [cv2.IMWRITE_JPEG_QUALITY, 40])
        base_jpeg = cv2.imdecode(enc_base, cv2.IMREAD_COLOR)

        # Splice in high-entropy patch compressed at Q95
        patch = np.random.randint(60, 220, (80, 80, 3), dtype=np.uint8)
        _, enc_patch = cv2.imencode('.jpg', patch, [cv2.IMWRITE_JPEG_QUALITY, 95])
        patch_jpeg = cv2.imdecode(enc_patch, cv2.IMREAD_COLOR)

        composite = base_jpeg.copy()
        composite[160:240, 160:240] = patch_jpeg

        with self.app.app_context():
            findings = check_error_level_analysis(composite, quality=90, page_num=1)

        self.assertGreaterEqual(len(findings), 1)
        f = findings[0]
        self.assertIn('visualization_path', f)
        self.assertIn('evidence_url', f)

        viz_path = f.get('visualization_path')
        if viz_path:
            self.assertTrue(os.path.exists(viz_path), f"Visualization file not found at {viz_path}")
            evidence_url = f.get('evidence_url')
            resp = self.client.get(evidence_url)
            self.assertEqual(resp.status_code, 200)
            self.assertIn(resp.content_type, ['image/png', 'application/octet-stream'])

    def test_img_003_collinear_dotted_lines_rejected(self):
        """Verifies that thin collinear dotted lines or single borders do not trigger false copy-move matches."""
        if cv2 is None or np is None:
            self.skipTest("OpenCV/NumPy not available")

        canvas = np.full((400, 400), 255, dtype=np.uint8)
        # Draw periodic dotted line along a single row
        for x in range(30, 350, 8):
            cv2.circle(canvas, (x, 150), 2, (0,), -1)
            cv2.circle(canvas, (x, 250), 2, (0,), -1)

        findings = check_copy_move_orb(canvas, min_matches=6, page_num=1)
        # Should be rejected because it is collinear and thin (<15px height)
        self.assertEqual(len(findings), 0)


class TestPDFForensicsEnhancements(unittest.TestCase):
    """Verifies Stage 4 PDF structural forensics: /Prev trailers, overprinted text, suspicious objects."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="vexora_test_pdf_forensics_")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_pdf_006_catalog_entry(self):
        """Verifies PDF-006 is cataloged in EXTENDED_PDF_RULES with severity High and Potential Manipulation."""
        self.assertIn('PDF-006', EXTENDED_PDF_RULES)
        rule = EXTENDED_PDF_RULES['PDF-006']
        self.assertEqual(rule['severity'], 'High')
        self.assertEqual(rule['evidence_class'], 'Potential Manipulation')
        self.assertEqual(get_evidence_class('PDF-006'), 'Potential Manipulation')

    def test_pdf_002_prev_cross_reference_pointers(self):
        """Verifies incremental update detector parses /Prev trailer pointers and marks confirmed structural fact."""
        if fitz is None:
            self.skipTest("PyMuPDF not available")

        pdf_path = os.path.join(self.test_dir, "prev_pointer_test.pdf")
        doc = fitz.open()
        doc.new_page(width=400, height=400)
        doc.save(pdf_path)
        doc.close()

        # Append incremental update with /Prev pointer and %%EOF
        with open(pdf_path, 'ab') as f:
            f.write(b"\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 5 /Prev 1200 >>\nstartxref\n1500\n%%EOF\n")

        findings = check_incremental_updates(pdf_path)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f['rule_id'], 'PDF-002')
        self.assertEqual(f['evidence_class'], 'Observation')
        self.assertIn("Confirmed Structural Fact", f['description'])
        self.assertIn("/Prev xref offsets", f['evidence'])

    def test_pdf_004_vector_text_overprinted_on_scanned_background(self):
        """Verifies detection of digital vector text rendered over a full-page background raster scan."""
        if fitz is None or Image is None:
            self.skipTest("PyMuPDF or Pillow not available")

        pdf_path = os.path.join(self.test_dir, "overprinted_scan.pdf")
        doc = fitz.open()
        p = doc.new_page(width=500, height=700)

        # Create full-page background scan image (covers > 75% of page)
        bg = Image.new("RGB", (480, 680), color=(240, 235, 230))
        buf = io.BytesIO()
        bg.save(buf, format="PNG")
        bg_bytes = buf.getvalue()
        bg.close()

        # Insert as full-page background
        p.insert_image(fitz.Rect(10, 10, 490, 690), stream=bg_bytes)
        # Overprint digital vector text on top
        p.insert_text(fitz.Point(100, 200), "INVOICE TOTAL: $84,500.00", fontsize=14)
        doc.save(pdf_path)
        doc.close()

        doc_check = fitz.open(pdf_path)
        findings = check_embedded_images_and_resolution(doc_check)
        doc_check.close()

        overprint_finding = next((f for f in findings if "Overprinted on Scanned Page Background" in f['title']), None)
        self.assertIsNotNone(overprint_finding)
        self.assertEqual(overprint_finding['rule_id'], 'PDF-004')
        self.assertEqual(overprint_finding['evidence_class'], 'Potential Manipulation')
        self.assertIn("INVOICE TOTAL", overprint_finding['description'])

    def test_pdf_006_javascript_detected(self):
        """Verifies detection of embedded JavaScript actions in PDF structure."""
        if fitz is None:
            self.skipTest("PyMuPDF not available")

        pdf_path = os.path.join(self.test_dir, "suspicious_js.pdf")
        doc = fitz.open()
        doc.new_page(width=400, height=400)
        cat_xref = doc.pdf_catalog()
        doc.xref_set_key(cat_xref, 'OpenAction', '<</S /JavaScript /JS (app.alert)>>')
        doc.save(pdf_path)
        doc.close()

        doc_check = fitz.open(pdf_path)
        findings = check_suspicious_pdf_objects(doc_check)
        doc_check.close()

        js_finding = next((f for f in findings if "JavaScript" in f['title']), None)
        self.assertIsNotNone(js_finding)
        self.assertEqual(js_finding['rule_id'], 'PDF-006')
        self.assertEqual(js_finding['severity'], 'High')
        self.assertEqual(js_finding['evidence_class'], 'Potential Manipulation')
        self.assertIn("Confirmed Structural Fact", js_finding['description'])

    def test_pdf_006_launch_action_detected(self):
        """Verifies detection of executable /Launch actions with Critical severity."""
        if fitz is None:
            self.skipTest("PyMuPDF not available")

        pdf_path = os.path.join(self.test_dir, "suspicious_launch.pdf")
        doc = fitz.open()
        doc.new_page(width=400, height=400)
        cat_xref = doc.pdf_catalog()
        doc.xref_set_key(cat_xref, 'OpenAction', '<</S /Launch /F (calc.exe)>>')
        doc.save(pdf_path)
        doc.close()

        doc_check = fitz.open(pdf_path)
        findings = check_suspicious_pdf_objects(doc_check)
        doc_check.close()

        launch_finding = next((f for f in findings if "Launch" in f['title']), None)
        self.assertIsNotNone(launch_finding)
        self.assertEqual(launch_finding['rule_id'], 'PDF-006')
        self.assertEqual(launch_finding['severity'], 'Critical')
        self.assertEqual(launch_finding['evidence_class'], 'Potential Manipulation')


if __name__ == '__main__':
    unittest.main()
