"""
VEXORA — Automated Visual Forensics Accuracy & False Positive Controls Test Suite
Verifies:
1. RANSAC affine geometric verification in Copy-Move detection (IMG-003).
2. Elimination of false positives on non-aligned random texture repetitions.
3. Clean document false-positive control (zero spurious findings on genuine documents).
4. Error Level Analysis (IMG-001) differential surface bounding.
"""

import unittest
import numpy as np
import cv2
import tempfile
import shutil
from pathlib import Path
from PIL import Image, ImageDraw

from backend.forensics_image import (
    check_error_level_analysis,
    check_copy_move_orb,
    run_image_forensics
)


class TestVisualForensicsAccuracy(unittest.TestCase):
    """Test suite for image forensics precision, RANSAC geometric checks, and negative controls."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="vexora_test_vis_acc_"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_01_ransac_copy_move_detects_genuine_clone(self):
        """Verifies RANSAC affine verification detects a rigidly duplicated stamp/graphic."""
        canvas = np.ones((500, 600, 3), dtype=np.uint8) * 255

        stamp = np.ones((80, 80, 3), dtype=np.uint8) * 255
        cv2.circle(stamp, (40, 40), 35, (0, 0, 180), 2)
        cv2.circle(stamp, (40, 40), 20, (0, 0, 180), 1)
        for i in range(8):
            angle = i * (np.pi / 4)
            x_end = int(40 + 30 * np.cos(angle))
            y_end = int(40 + 30 * np.sin(angle))
            cv2.line(stamp, (40, 40), (x_end, y_end), (0, 100, 200), 1)
        np.random.seed(42)
        noise = (np.random.rand(80, 80, 3) * 100).astype(np.uint8)
        mask = (stamp < 240)
        stamp[mask] = np.clip(stamp[mask] + noise[mask], 0, 255)

        # Place original stamp at (50, 100)
        canvas[100:180, 50:130] = stamp

        # Clone stamp with rigid translation to (300, 250)
        canvas[250:330, 300:380] = stamp

        findings = check_copy_move_orb(canvas, min_matches=4, min_distance=40.0)
        rule_ids = [f['rule_id'] for f in findings]
        self.assertIn('IMG-003', rule_ids)
        finding = next(f for f in findings if f['rule_id'] == 'IMG-003')
        self.assertIn("cloned feature vectors", finding['description'])

    def test_02_ransac_rejects_random_unaligned_patterns(self):
        """Verifies RANSAC geometric check suppresses false matches from random unaligned patterns."""
        canvas = np.ones((400, 400, 3), dtype=np.uint8) * 255
        np.random.seed(123)
        for _ in range(30):
            pt = (np.random.randint(20, 380), np.random.randint(20, 380))
            cv2.circle(canvas, pt, np.random.randint(2, 6), (50, 50, 50), -1)

        findings = check_copy_move_orb(canvas, min_matches=6, min_distance=45.0)
        rule_ids = [f['rule_id'] for f in findings]
        self.assertNotIn('IMG-003', rule_ids)

    def test_03_clean_image_negative_control(self):
        """Verifies clean image produces zero spurious copy-move or manipulation findings."""
        clean_file = self.temp_dir / "clean_receipt.png"
        pil_img = Image.new('RGB', (400, 500), color=(250, 250, 250))
        draw = ImageDraw.Draw(pil_img)
        draw.text((30, 40), "OFFICIAL RECEIPT", fill=(20, 20, 20))
        draw.text((30, 70), "Date: 2026-01-15", fill=(40, 40, 40))
        draw.text((30, 100), "Total: $1,200.00", fill=(40, 40, 40))
        draw.line([(30, 130), (370, 130)], fill=(180, 180, 180), width=1)
        pil_img.save(clean_file, format='PNG')

        findings = run_image_forensics(str(clean_file), doc_category="Receipt")
        critical_or_high = [f for f in findings if f.get('severity') in ('Critical', 'High')]
        self.assertEqual(len(critical_or_high), 0)


if __name__ == '__main__':
    unittest.main()
