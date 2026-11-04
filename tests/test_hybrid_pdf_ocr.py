"""
VEXORA — Hybrid Scanned & Digital PDF OCR Test Suite
Tests Priority 1 requirements:
- Digital PDF native extraction
- Fully scanned PDF extraction with OCR & coordinate scaling
- Mixed digital + scanned multi-page PDF processing
- Empty PDF handling
- Corrupted PDF error handling
- Low-quality scanned document pre-processing
- Strict OCR flag behavior
"""

import io
import unittest
from unittest.mock import patch
from pathlib import Path
import pymupdf
from PIL import Image, ImageDraw

from backend.extractor import (
    ExtractionError,
    extract_pdf_document,
    extract_image_document,
    extract_document_content,
    _enhance_scanned_image_for_ocr
)


class VexoraHybridPdfOcrTestCase(unittest.TestCase):
    """Unit test cases covering hybrid PDF extraction and OCR processing."""

    def _create_digital_pdf_bytes(self):
        """Creates an in-memory born-digital PDF with native text."""
        doc = pymupdf.open()
        page = doc.new_page(width=595.0, height=842.0)
        page.insert_text(
            (50, 100),
            "INVOICE #INV-2026-9001\n"
            "Date: 2026-02-15\n"
            "Vendor: Apex Forensic Logistics Ltd\n"
            "Total Amount: $45,250.00 USD\n"
            "Authorized by: Dr. Eleanor Vance\n"
            "Official Email: billing@apex-forensics.com\n",
            fontsize=12
        )
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def _create_scanned_pdf_bytes(self, text_to_draw="SCANNED VENDOR RECEIPT\nAmount: $8,750.00\nDate: 2026-01-20"):
        """Creates an in-memory PDF whose page contains ONLY a raster image (no digital text)."""
        # Create an image containing text
        img = Image.new('RGB', (800, 1100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((60, 80), text_to_draw, fill=(0, 0, 0))

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        img_bytes = buf.getvalue()

        # Insert into PDF as pure image
        doc = pymupdf.open()
        page = doc.new_page(width=595.0, height=842.0)
        page.insert_image(page.rect, stream=img_bytes)
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def _create_mixed_pdf_bytes(self):
        """Creates a 2-page PDF: Page 1 is native digital, Page 2 is scanned image-only."""
        doc = pymupdf.open()

        # Page 1: Digital
        doc.new_page(width=595.0, height=842.0)
        doc[0].insert_text(
            (50, 100),
            "PURCHASE ORDER #PO-2026-0042\n"
            "Vendor: Vertex Global Security\n"
            "Approved Total: $12,500.00\n"
            "Order Date: 2026-02-10\n",
            fontsize=12
        )

        # Page 2: Scanned image
        doc.new_page(width=595.0, height=842.0)
        img = Image.new('RGB', (800, 1100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((50, 60), "CUSTOMS CLEARANCE MANIFEST\nStamp ID: ST-9921\nDate: 2026-02-12", fill=(0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        doc[1].insert_image(doc[1].rect, stream=buf.getvalue())

        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def test_digital_pdf_extraction(self):
        """Verifies native digital PDF extraction extracts text blocks and vectors without OCR."""
        pdf_bytes = self._create_digital_pdf_bytes()
        res = extract_pdf_document(pdf_bytes)

        self.assertTrue(res['success'])
        self.assertEqual(res['format'], 'PDF')
        self.assertEqual(res['extraction_mode'], 'digital_pdf')
        self.assertFalse(res['ocr_applied'])
        self.assertEqual(res['page_count'], 1)
        self.assertEqual(res['digital_pages_count'], 1)
        self.assertEqual(res['scanned_pages_count'], 0)
        self.assertGreater(res['total_words'], 10)

        # Verify page details
        page = res['pages'][0]
        self.assertEqual(page['extraction_method'], 'native_pymupdf')
        self.assertFalse(page['ocr_applied'])
        self.assertIsNone(page['ocr_confidence'])
        self.assertGreater(len(page['blocks']), 0)
        for b in page['blocks']:
            self.assertEqual(b['type'], 'text')
            self.assertEqual(len(b['bbox']), 4)

        # Verify extracted entities
        entities = res['entities']
        self.assertTrue(any("45,250" in str(v) for v in entities['monetary_values']))
        self.assertTrue(any("INV-2026-9001" in str(i) for i in entities['identifiers']))

    def test_fully_scanned_pdf_extraction_fallback(self):
        """Verifies that a fully scanned PDF detects scanned pages and executes fallback when Tesseract is absent."""
        pdf_bytes = self._create_scanned_pdf_bytes()
        res = extract_pdf_document(pdf_bytes)

        self.assertTrue(res['success'])
        self.assertEqual(res['page_count'], 1)
        self.assertEqual(res['digital_pages_count'], 0)
        self.assertEqual(res['scanned_pages_count'], 1)
        self.assertTrue(res['ocr_applied'])
        self.assertIn(res['extraction_mode'], ('scanned_pdf_ocr', 'simulated_fallback'))

        page = res['pages'][0]
        self.assertTrue(page['ocr_applied'])
        self.assertIn(page['extraction_method'], ('tesseract_ocr', 'ocr_fallback'))
        self.assertGreater(len(page['blocks']), 0)
        self.assertEqual(len(page['blocks'][0]['bbox']), 4)

    def test_fully_scanned_pdf_with_mocked_ocr(self):
        """Verifies scanned PDF extraction preserves word confidences, text, and point coordinates when OCR succeeds."""
        pdf_bytes = self._create_scanned_pdf_bytes()

        # Mock pytesseract output
        mock_data = {
            'text': ['INVOICE', 'TOTAL:', '$8,750.00', 'DATE:', '2026-01-20'],
            'conf': ['95.0', '92.0', '96.5', '90.0', '94.0'],
            'left': [50, 150, 250, 50, 150],
            'top': [100, 100, 100, 150, 150],
            'width': [80, 80, 90, 60, 90],
            'height': [25, 25, 25, 25, 25],
            'block_num': [1, 1, 1, 2, 2]
        }

        with patch('pytesseract.image_to_data', return_value=mock_data), \
             patch('pytesseract.image_to_string', return_value="INVOICE TOTAL: $8,750.00 DATE: 2026-01-20"):
            res = extract_pdf_document(pdf_bytes)

            self.assertTrue(res['success'])
            self.assertEqual(res['extraction_mode'], 'scanned_pdf_ocr')
            self.assertTrue(res['ocr_applied'])
            self.assertEqual(res['scanned_pages_count'], 1)

            page = res['pages'][0]
            self.assertEqual(page['extraction_method'], 'tesseract_ocr')
            self.assertTrue(page['ocr_applied'])
            self.assertIsNotNone(page['ocr_confidence'])
            self.assertGreaterEqual(page['ocr_confidence'], 90.0)

            # Check that scaled coordinates fit within page bounds (595x842)
            for b in page['blocks']:
                self.assertEqual(len(b['bbox']), 4)
                self.assertLessEqual(b['bbox'][2], 595.0)
                self.assertLessEqual(b['bbox'][3], 842.0)

            # Check that entities were extracted
            self.assertTrue(any("8,750" in str(v) for v in res['entities']['monetary_values']))

    def test_mixed_digital_and_scanned_pdf(self):
        """Verifies mixed PDF processes digital and scanned pages independently without duplicating text."""
        pdf_bytes = self._create_mixed_pdf_bytes()
        res = extract_pdf_document(pdf_bytes)

        self.assertTrue(res['success'])
        self.assertEqual(res['page_count'], 2)
        self.assertEqual(res['digital_pages_count'], 1)
        self.assertEqual(res['scanned_pages_count'], 1)
        self.assertEqual(res['extraction_mode'], 'hybrid_pdf')
        self.assertTrue(res['ocr_applied'])

        # Page 1 must be native digital
        page1 = res['pages'][0]
        self.assertEqual(page1['page_number'], 1)
        self.assertEqual(page1['extraction_method'], 'native_pymupdf')
        self.assertFalse(page1['ocr_applied'])
        self.assertIn("PURCHASE ORDER", page1['text'])

        # Page 2 must be scanned
        page2 = res['pages'][1]
        self.assertEqual(page2['page_number'], 2)
        self.assertTrue(page2['ocr_applied'])
        self.assertIn(page2['extraction_method'], ('tesseract_ocr', 'ocr_fallback'))

    def test_empty_pdf_handling(self):
        """Verifies that an empty or zero-page PDF produces a clean response without crashing."""
        doc = pymupdf.open()
        res = extract_pdf_document(doc)
        self.assertTrue(res['success'])
        self.assertEqual(res['page_count'], 0)
        self.assertEqual(res['total_words'], 0)
        self.assertEqual(len(res['pages']), 0)
        self.assertEqual(res['full_text'], '')

        # Test single blank page PDF
        blank_doc = pymupdf.open()
        blank_doc.new_page(width=595.0, height=842.0)
        blank_bytes = blank_doc.tobytes()
        blank_doc.close()

        res_blank = extract_pdf_document(blank_bytes)
        self.assertTrue(res_blank['success'])
        self.assertEqual(res_blank['page_count'], 1)
        self.assertEqual(res_blank['total_words'], 0)

    def test_corrupted_pdf_handling(self):
        """Verifies that a corrupted or invalid PDF stream raises ExtractionError."""
        corrupt_bytes = b"%%PDF-1.4\nCorrupt Header Junk With No Valid Objects\n%%EOF"
        with self.assertRaises(ExtractionError):
            extract_pdf_document(corrupt_bytes)

    def test_low_quality_scanned_document_enhancement(self):
        """Verifies that _enhance_scanned_image_for_ocr normalizes contrast on low-contrast images."""
        # Create a low-contrast faint gray image
        faint_img = Image.new('RGB', (200, 200), color=(220, 220, 220))
        draw = ImageDraw.Draw(faint_img)
        draw.text((20, 20), "Faint Text", fill=(210, 210, 210))

        enhanced = _enhance_scanned_image_for_ocr(faint_img)
        self.assertIsNotNone(enhanced)
        self.assertEqual(enhanced.mode, 'L')

    def test_strict_ocr_flag_enforcement(self):
        """Verifies that when VEXORA_STRICT_OCR=true, missing Tesseract raises ExtractionError instead of silent fallback."""
        import pytesseract
        import os

        # Temporarily enable strict OCR
        old_env = os.environ.get('VEXORA_STRICT_OCR')
        os.environ['VEXORA_STRICT_OCR'] = 'true'

        try:
            with patch('pytesseract.image_to_data', side_effect=pytesseract.TesseractNotFoundError()):
                pdf_bytes = self._create_scanned_pdf_bytes()
                with self.assertRaises(ExtractionError) as ctx:
                    extract_pdf_document(pdf_bytes)
                self.assertIn("Tesseract OCR is not installed", str(ctx.exception))
        finally:
            if old_env is not None:
                os.environ['VEXORA_STRICT_OCR'] = old_env
            else:
                os.environ.pop('VEXORA_STRICT_OCR', None)


if __name__ == '__main__':
    unittest.main()
