import unittest
import os
import shutil
import tempfile
import numpy as np
import cv2

from backend.forensics_image import (
    is_image_forensics_available,
    check_error_level_analysis,
    check_noise_and_sharpness_inconsistency,
    check_copy_move_orb,
    check_signature_region,
    run_image_forensics,
    IMAGE_FORENSIC_RULES
)
from backend.evidence_class import get_evidence_class
from backend.app import create_app
from backend.config import TestConfig
from backend.database import init_db
from backend.models import create_case, create_document, get_findings_by_document
from backend.analyzer import analyze_document


class TestV2PhaseDImageForensics(unittest.TestCase):
    """
    Test suite for V2 Phase D:
    - Verifies OpenCV / NumPy image forensics availability
    - Tests IMG-001 (ELA JPEG compression residue)
    - Tests IMG-002 (Sharpness / noise variance inconsistency)
    - Tests IMG-003 (ORB copy-move duplication detection)
    - Tests IMG-004 (Signature stroke detection & unsupported fallback)
    - Tests Analyzer integration with ENABLE_IMAGE_FORENSICS flag
    """

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="vexora_phase_d_test_")
        cls.test_db = os.path.join(cls.test_dir, "phase_d.db")
        cls.test_uploads = os.path.join(cls.test_dir, "uploads")
        cls.test_reports = os.path.join(cls.test_dir, "reports")
        os.makedirs(cls.test_uploads, exist_ok=True)
        os.makedirs(cls.test_reports, exist_ok=True)

        class PhaseDTestConfig(TestConfig):
            DATABASE = cls.test_db
            UPLOAD_FOLDER = cls.test_uploads
            REPORTS_FOLDER = cls.test_reports
            TESTING = True
            ENABLE_IMAGE_FORENSICS = True

        cls.config_class = PhaseDTestConfig
        cls.app = create_app(PhaseDTestConfig)

        with cls.app.app_context():
            init_db(cls.test_db)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_image_forensics_availability(self):
        """Verifies that OpenCV and NumPy are installed and detected as available."""
        self.assertTrue(is_image_forensics_available())

    def test_img_001_error_level_analysis(self):
        """
        Tests ELA detects anomalous block compression residue when an uncompressed/differently
        compressed patch is spliced into a JPEG image.
        """
        # Create base canvas and compress heavily as JPEG quality 40
        base = np.full((320, 320, 3), 220, dtype=np.uint8)
        cv2.putText(base, "Invoice Statement Baseline", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 40), 2)
        cv2.putText(base, "Account No: 1234-5678", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 1)
        
        _, enc_base = cv2.imencode('.jpg', base, [cv2.IMWRITE_JPEG_QUALITY, 40])
        base_jpeg = cv2.imdecode(enc_base, cv2.IMREAD_COLOR)

        # Create high-entropy patch with different compression history (quality 95)
        patch = np.random.randint(60, 220, (80, 80, 3), dtype=np.uint8)
        _, enc_patch = cv2.imencode('.jpg', patch, [cv2.IMWRITE_JPEG_QUALITY, 95])
        patch_jpeg = cv2.imdecode(enc_patch, cv2.IMREAD_COLOR)

        # Splice patch into the base JPEG without recompressing host image
        composite = base_jpeg.copy()
        composite[160:240, 160:240] = patch_jpeg

        findings = check_error_level_analysis(composite, quality=90, page_num=1)
        self.assertGreaterEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding['rule_id'], 'IMG-001')
        self.assertEqual(finding['evidence_class'], 'Potential Manipulation')
        self.assertEqual(finding['status'], 'Potential Anomaly')
        self.assertIn("heuristic", finding['description'].lower())
        self.assertIsNotNone(finding['coordinates'])

    def test_img_002_sharpness_inconsistency(self):
        """
        Tests Laplacian variance inconsistency detector when a sharp patch is embedded
        in an otherwise soft / blurred document canvas.
        """
        canvas = np.full((350, 350), 230, dtype=np.uint8)
        cv2.putText(canvas, "Soft blurred text line one", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 80, 80), 1)
        cv2.putText(canvas, "Soft blurred text line two", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 80, 80), 1)
        canvas = cv2.GaussianBlur(canvas, (11, 11), 3.0)

        sharp_patch = np.zeros((90, 90), dtype=np.uint8)
        for r in range(0, 90, 6):
            for c in range(0, 90, 6):
                if (r // 6 + c // 6) % 2 == 0:
                    sharp_patch[r:r+6, c:c+6] = 255

        composite = canvas.copy()
        composite[180:270, 180:270] = sharp_patch

        findings = check_noise_and_sharpness_inconsistency(composite, block_size=64, page_num=1)
        self.assertGreaterEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding['rule_id'], 'IMG-002')
        self.assertEqual(finding['evidence_class'], 'Observation')
        self.assertEqual(finding['status'], 'Observation')
        self.assertIn("limitation", finding['description'].lower())

    def test_img_003_copy_move_detection(self):
        """
        Tests ORB keypoint matching for duplicated/cloned regions.
        """
        canvas = np.full((400, 400), 245, dtype=np.uint8)

        # Draw a distinctive complex stamp pattern
        stamp = np.full((90, 90), 245, dtype=np.uint8)
        cv2.circle(stamp, (45, 45), 40, (30,), 2)
        cv2.circle(stamp, (45, 45), 25, (30,), 2)
        cv2.line(stamp, (10, 45), (80, 45), (30,), 2)
        cv2.line(stamp, (45, 10), (45, 80), (30,), 2)
        cv2.putText(stamp, "VERIFIED", (12, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (10,), 1)
        cv2.putText(stamp, "AUDIT-01", (14, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (10,), 1)

        # Place original stamp at (60, 60)
        canvas[60:150, 60:150] = stamp
        # Duplicate exact stamp at (250, 250) (offset dx=190, dy=190)
        canvas[250:340, 250:340] = stamp

        findings = check_copy_move_orb(canvas, min_matches=6, min_distance=40.0, page_num=1)
        self.assertGreaterEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding['rule_id'], 'IMG-003')
        self.assertEqual(finding['evidence_class'], 'Potential Manipulation')
        self.assertEqual(finding['status'], 'Potential Anomaly')
        self.assertIn("matched keypoint pairs", finding['evidence'].lower())

    def test_img_004_signature_region_detection(self):
        """
        Tests detection of cursive handwritten strokes in the bottom third of the page.
        """
        canvas = np.full((500, 400), 255, dtype=np.uint8)
        cv2.putText(canvas, "Official Agreement Form", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20,), 2)
        cv2.putText(canvas, "Terms and conditions apply.", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50,), 1)

        # Draw signature strokes in bottom third (y > 325)
        curve_pts = np.array([
            [80, 410], [95, 390], [110, 430], [130, 385],
            [150, 420], [170, 395], [190, 425], [220, 410]
        ], np.int32)
        cv2.polylines(canvas, [curve_pts], isClosed=False, color=(20,), thickness=3)

        findings = check_signature_region(canvas, page_num=1)
        self.assertGreaterEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding['rule_id'], 'IMG-004')
        self.assertEqual(finding['evidence_class'], 'Observation')
        self.assertIsNotNone(finding['coordinates'])

    def test_img_004_signature_unsupported_small_image(self):
        """
        Tests fallback notice when image resolution is below threshold for signature analysis.
        """
        small_canvas = np.full((120, 120), 255, dtype=np.uint8)
        findings = check_signature_region(small_canvas, page_num=1)
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding['rule_id'], 'IMG-004')
        self.assertIn("signature analysis: unsupported", finding['description'])

    def test_run_image_forensics_standalone_image(self):
        """
        Tests run_image_forensics helper on a saved test image file.
        """
        img_path = os.path.join(self.test_uploads, "test_doc.png")
        canvas = np.full((400, 400, 3), 250, dtype=np.uint8)
        cv2.putText(canvas, "Standard Header", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        cv2.imwrite(img_path, canvas)

        findings = run_image_forensics(img_path)
        self.assertIsInstance(findings, list)
        for f in findings:
            self.assertIn('rule_id', f)
            self.assertIn('evidence_class', f)
            self.assertIn('status', f)
            self.assertIn('confidence', f)
            self.assertIn(f['evidence_class'], ['Observation', 'Inconsistency', 'Potential Manipulation'])

    def test_analyzer_integration_with_flag(self):
        """
        Verifies analyze_document executes image forensics only when ENABLE_IMAGE_FORENSICS is active.
        """
        img_path = os.path.join(self.test_uploads, "contract.png")
        canvas = np.full((400, 400, 3), 245, dtype=np.uint8)
        # Duplicate stamp for IMG-003
        cv2.circle(canvas, (80, 80), 30, (20, 20, 20), 2)
        cv2.line(canvas, (50, 80), (110, 80), (20, 20, 20), 2)
        cv2.circle(canvas, (260, 260), 30, (20, 20, 20), 2)
        cv2.line(canvas, (230, 260), (290, 260), (20, 20, 20), 2)
        cv2.imwrite(img_path, canvas)

        with self.app.app_context():
            case = create_case({
                'title': 'Phase D Case',
                'type': 'Forensics',
                'priority': 'Medium',
                'status': 'Active',
                'investigator': 'Lead',
                'description': 'Image forensics test'
            })
            doc = create_document({
                'case_id': case['id'],
                'filename': 'contract.png',
                'file_type': 'image/png',
                'file_size': 40000,
                'file_path': img_path,
                'file_hash': 'hash_d_001',
                'category': 'Agreement',
                'status': 'Pending'
            })
            doc_id = doc['id']

            # Test 1: Flag False -> 0 IMG findings
            self.app.config['ENABLE_IMAGE_FORENSICS'] = False
            results_off = analyze_document(doc_id)
            img_findings_off = [f for f in results_off.get('findings', []) if f.get('rule_id', '').startswith('IMG-')]
            self.assertEqual(len(img_findings_off), 0)

            # Test 2: Flag True -> IMG findings produced
            self.app.config['ENABLE_IMAGE_FORENSICS'] = True
            results_on = analyze_document(doc_id)
            img_findings_on = [f for f in results_on.get('findings', []) if f.get('rule_id', '').startswith('IMG-')]
            self.assertGreater(len(img_findings_on), 0)

            # Check that evidence class is assigned
            for f in img_findings_on:
                self.assertIn(f.get('evidence_class'), ['Observation', 'Inconsistency', 'Potential Manipulation'])


if __name__ == '__main__':
    unittest.main()
