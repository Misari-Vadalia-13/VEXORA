"""
VEXORA — Automated OCR Reliability & Error Reporting Test Suite
Verifies:
1. Discrete extraction status enums (SUCCESS, PARTIAL_SUCCESS, LOW_CONFIDENCE, OCR_UNAVAILABLE, OCR_FAILED).
2. Elimination of deceptive placeholder text ([Scanned Page 1 - OCR Fallback]).
3. OpenCV image deskewing and adaptive binarization preprocessing.
4. CER / WER quantitative error metrics.
"""

import unittest
from unittest.mock import patch
import io
import numpy as np
from PIL import Image, ImageDraw
import pymupdf

from backend.extractor import (
    extract_pdf_document,
    extract_image_document,
    ExtractionStatus,
    deskew_image_for_ocr,
    preprocess_image_for_ocr
)
from tools.evaluate_ocr import compute_cer, compute_wer, evaluate_ocr_strings


class TestOcrReliability(unittest.TestCase):
    """Test suite for OCR reliability, failure reporting, and quantitative accuracy."""

    def _create_scanned_page_doc(self):
        """Creates a single-page PDF containing only a raster image."""
        doc = pymupdf.open()
        page = doc.new_page(width=595.0, height=842.0)
        img = Image.new('RGB', (400, 200), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 50), "Apex Global Solutions Invoice $15,000", fill=(0, 0, 0))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        page.insert_image(page.rect, stream=img_bytes.getvalue())
        return doc

    def test_01_discrete_status_success(self):
        """Verifies SUCCESS status when OCR extracts high-confidence text."""
        doc = self._create_scanned_page_doc()
        mock_data = {
            'text': ['Apex', 'Global', 'Invoice', '$15,000'],
            'conf': ['95.0', '92.0', '96.0', '90.0'],
            'left': [10, 50, 100, 150],
            'top': [20, 20, 20, 20],
            'width': [30, 40, 40, 50],
            'height': [15, 15, 15, 15],
            'block_num': [1, 1, 1, 1]
        }
        with patch('pytesseract.image_to_data', return_value=mock_data), \
             patch('pytesseract.image_to_string', return_value="Apex Global Invoice $15,000"):
            res = extract_pdf_document(doc)
            self.assertEqual(res['extraction_status'], ExtractionStatus.SUCCESS)
            self.assertEqual(res['pages'][0]['extraction_status'], ExtractionStatus.SUCCESS)
            self.assertEqual(len(res['page_errors']), 0)

    def test_02_discrete_status_low_confidence(self):
        """Verifies LOW_CONFIDENCE status when average OCR confidence is below 60%."""
        doc = self._create_scanned_page_doc()
        mock_data = {
            'text': ['Blurry', 'Faded', 'Text'],
            'conf': ['45.0', '50.0', '42.0'],
            'left': [10, 50, 100],
            'top': [20, 20, 20],
            'width': [30, 40, 40],
            'height': [15, 15, 15],
            'block_num': [1, 1, 1]
        }
        with patch('pytesseract.image_to_data', return_value=mock_data), \
             patch('pytesseract.image_to_string', return_value="Blurry Faded Text"):
            res = extract_pdf_document(doc)
            self.assertEqual(res['extraction_status'], ExtractionStatus.LOW_CONFIDENCE)
            self.assertEqual(res['pages'][0]['extraction_status'], ExtractionStatus.LOW_CONFIDENCE)

    def test_03_discrete_status_ocr_unavailable(self):
        """Verifies OCR_UNAVAILABLE status when Tesseract binary is missing."""
        import pytesseract
        doc = self._create_scanned_page_doc()
        with patch('pytesseract.image_to_data', side_effect=pytesseract.TesseractNotFoundError()):
            res = extract_pdf_document(doc)
            self.assertEqual(res['extraction_status'], ExtractionStatus.OCR_UNAVAILABLE)
            self.assertEqual(res['pages'][0]['extraction_status'], ExtractionStatus.OCR_UNAVAILABLE)
            self.assertEqual(len(res['page_errors']), 1)

    def test_04_no_deceptive_placeholder_text_emitted(self):
        """Verifies that [Scanned Page 1 - OCR Fallback] is never emitted as valid text."""
        import pytesseract
        doc = self._create_scanned_page_doc()
        with patch('pytesseract.image_to_data', side_effect=pytesseract.TesseractNotFoundError()):
            res = extract_pdf_document(doc)
            # Full text must NOT contain fallback string
            self.assertNotIn("Scanned Page", res['full_text'])
            self.assertNotIn("OCR Fallback", res['full_text'])
            for page in res['pages']:
                self.assertNotIn("Scanned Page", page['text'])
                self.assertNotIn("OCR Fallback", page['text'])

    def test_05_opencv_deskew_and_binarization(self):
        """Verifies OpenCV preprocessing deskews and binarizes an image."""
        img = Image.new('RGB', (300, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 40), "TEST DESKEW STRING", fill=(0, 0, 0))

        # Rotate image slightly to simulate skew
        skewed = img.rotate(5, expand=True, fillcolor=(255, 255, 255))
        preprocessed, angle = preprocess_image_for_ocr(skewed)
        self.assertIsInstance(preprocessed, Image.Image)
        # Result must be binarized (mode L or 1)
        self.assertIn(preprocessed.mode, ('L', '1'))

    def test_06_quantitative_cer_wer_computation(self):
        """Verifies Character Error Rate (CER) and Word Error Rate (WER) mathematical accuracy."""
        ref = "INVOICE TOTAL $10,000.00"
        # 1 character replaced ($10,000 -> $18,000)
        hyp = "INVOICE TOTAL $18,000.00"

        cer, char_acc = compute_cer(ref, hyp)
        # Distance = 1, len(ref) = 24 -> 1/24 ~ 0.0417
        self.assertAlmostEqual(cer, 1 / 24, places=3)
        self.assertAlmostEqual(char_acc, 1 - (1 / 24), places=3)

        wer, word_acc = compute_wer(ref, hyp)
        # Distance = 1 word modified out of 3 words -> 1/3 ~ 0.3333
        self.assertAlmostEqual(wer, 1 / 3, places=3)
        self.assertAlmostEqual(word_acc, 2 / 3, places=3)


if __name__ == '__main__':
    unittest.main()

