"""
VEXORA — V2 Phase E Unit & Integration Tests: Real Field-Level Confidence
Verifies:
1. Digital PDF entity confidence: 'n/a (digital text)'
2. OCR word-level confidence and entity confidence averaging via pytesseract.image_to_data
3. Tesseract missing fallback behavior: extraction_mode = 'simulated_fallback' and UI/dossier warning badge
4. VEXORA_STRICT_OCR feature flag behavior (explicit 'OCR unavailable' status)
5. SQLite entities table schema and persistence with nullable confidence column
6. Display label 'Rule Weight' for rule-based findings in UI and dossiers
"""

import os
import io
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from PIL import Image

import pymupdf as fitz
import pytesseract

from backend.app import create_app
from backend.config import Config, TestConfig
from backend.database import init_db, get_db
from backend.ner import extract_entities_from_text, merge_entities
from backend.extractor import extract_pdf_document, extract_image_document, extract_document_content
from backend.models import (
    create_case,
    create_document,
    get_document_by_id,
    save_document_extraction,
    save_document_entities,
    get_entities_by_document,
    create_finding
)
from backend.reporter import generate_case_dossier_data, generate_dossier_pdf, generate_dossier_html


class TestV2PhaseEFieldConfidence(unittest.TestCase):
    """Test suite for Phase E field-level confidence, extraction modes, and rule weight display."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="vexora_phase_e_test_")
        cls.test_db = os.path.join(cls.test_dir, "phase_e.db")
        cls.test_uploads = os.path.join(cls.test_dir, "uploads")
        cls.test_reports = os.path.join(cls.test_dir, "reports")
        os.makedirs(cls.test_uploads, exist_ok=True)
        os.makedirs(cls.test_reports, exist_ok=True)

        class PhaseETestConfig(TestConfig):
            DATABASE = cls.test_db
            UPLOAD_FOLDER = cls.test_uploads
            REPORTS_FOLDER = cls.test_reports
            TESTING = True
            VEXORA_STRICT_OCR = False

        cls.config_class = PhaseETestConfig
        cls.app = create_app(PhaseETestConfig)

        with cls.app.app_context():
            init_db(cls.test_db)

        # Generate sample digital PDF with known entities
        cls.sample_pdf_path = os.path.join(cls.test_uploads, "digital_sample.pdf")
        doc = fitz.open()
        p = doc.new_page(width=595, height=842)
        p.insert_text(fitz.Point(72, 100), "INVOICE #INV-2026-E001", fontsize=14)
        p.insert_text(fitz.Point(72, 130), "Vendor: Acme Corporation", fontsize=11)
        p.insert_text(fitz.Point(72, 150), "Date: 2026-05-15", fontsize=11)
        p.insert_text(fitz.Point(72, 170), "Amount Due: $15,750.00", fontsize=11)
        doc.save(cls.sample_pdf_path)
        doc.close()

        # Generate sample image
        cls.sample_img_path = os.path.join(cls.test_uploads, "scanned_receipt.png")
        img = Image.new('RGB', (400, 300), color=(255, 255, 255))
        img.save(cls.sample_img_path)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def _create_test_case(self, title):
        return create_case({
            'title': title,
            'type': 'Financial Audit',
            'priority': 'High',
            'status': 'Active',
            'investigator': 'Lead Investigator',
            'description': 'Phase E test case'
        })

    def test_digital_pdf_entity_confidence(self):
        """Verifies that entities extracted from native digital PDFs receive 'n/a (digital text)' confidence."""
        result = extract_pdf_document(self.sample_pdf_path)
        self.assertTrue(result['success'])
        self.assertEqual(result.get('extraction_mode'), 'digital_pdf')

        entities = result.get('entities', {})
        # Verify that all found entities have confidence == 'n/a (digital text)'
        found_any = False
        for cat, items in entities.items():
            for item in items:
                found_any = True
                self.assertIn('confidence', item)
                self.assertEqual(item['confidence'], 'n/a (digital text)')
        self.assertTrue(found_any, "Expected at least one entity extracted from test PDF")

    def test_ocr_word_confidence_and_entity_averaging(self):
        """
        Verifies that when Tesseract is available, image_to_data per-word confidence
        is extracted and properly averaged for each multi-word entity.
        """
        mock_data = {
            'text': ['INVOICE', 'Vendor:', 'Acme', 'Corporation', 'Date:', '2026-05-15', 'Total:', '$15,750.00'],
            'conf': [95.0, 99.0, 92.0, 88.0, 98.0, 94.0, 96.0, 90.0]
        }
        mock_text = "INVOICE #INV-001\nVendor: Acme Corporation\nDate: 2026-05-15\nTotal: $15,750.00"

        with patch('pytesseract.image_to_data', return_value=mock_data), \
             patch('pytesseract.image_to_string', return_value=mock_text):
            result = extract_image_document(self.sample_img_path)
            self.assertTrue(result['success'])
            self.assertEqual(result.get('extraction_mode'), 'tesseract_ocr')

            entities = result.get('entities', {})
            orgs = entities.get('organizations', [])
            self.assertGreaterEqual(len(orgs), 1)

            acme_org = next((o for o in orgs if 'acme' in o['value'].lower()), None)
            self.assertIsNotNone(acme_org)
            # Acme Corporation has words 'Acme' (92.0) and 'Corporation' (88.0) -> average 90.0
            self.assertAlmostEqual(float(acme_org['confidence']), 90.0, places=1)

            # Check monetary value '$15,750.00' has word conf 90.0
            amounts = entities.get('monetary_values', [])
            self.assertGreaterEqual(len(amounts), 1)
            amt = amounts[0]
            self.assertAlmostEqual(float(amt['confidence']), 90.0, places=1)

    def test_tesseract_missing_fallback(self):
        """
        Verifies that when Tesseract is not installed, the extractor gracefully produces
        simulated_fallback without throwing unhandled exceptions.
        """
        with patch('pytesseract.image_to_data', side_effect=pytesseract.TesseractNotFoundError()), \
             patch('pytesseract.image_to_string', side_effect=pytesseract.TesseractNotFoundError()):
            result = extract_image_document(self.sample_img_path)
            self.assertTrue(result['success'])
            self.assertEqual(result.get('extraction_mode'), 'simulated_fallback')
            self.assertIn("Visual Artifact Analysis", result['full_text'])

    def test_strict_ocr_flag_enabled(self):
        """
        Verifies that when VEXORA_STRICT_OCR is True, missing Tesseract returns an explicit
        'OCR unavailable' status instead of synthetic fallback text.
        """
        with patch('pytesseract.image_to_data', side_effect=pytesseract.TesseractNotFoundError()), \
             patch('pytesseract.image_to_string', side_effect=pytesseract.TesseractNotFoundError()):

            # Turn flag ON
            self.app.config['VEXORA_STRICT_OCR'] = True
            with self.app.app_context():
                result = extract_image_document(self.sample_img_path)
                self.assertFalse(result['success'])
                self.assertEqual(result.get('status'), 'OCR unavailable')
                self.assertEqual(result.get('extraction_mode'), 'ocr_unavailable')
                self.assertIn('OCR unavailable', result.get('error', ''))

            # Turn flag OFF
            self.app.config['VEXORA_STRICT_OCR'] = False

    def test_entities_table_persistence(self):
        """
        Verifies that entities and their confidence values are persisted in the SQLite entities table.
        """
        with self.app.app_context():
            case = self._create_test_case('Entity Persistence Case')
            doc = create_document({
                'case_id': case['id'],
                'filename': 'contract.pdf',
                'file_type': 'pdf',
                'file_size': 2048,
                'file_path': self.sample_pdf_path,
                'file_hash': 'h_ent_001',
                'category': 'Agreement',
                'status': 'Pending'
            })

            extraction_data = {
                'full_text': 'Contract terms between Acme Corp and Beta LLC on 2026-06-01 for $50,000.00',
                'extraction_mode': 'digital_pdf',
                'page_count': 1,
                'total_words': 12,
                'entities': {
                    'organizations': [{'value': 'Acme Corp', 'page': 1, 'confidence': 'n/a (digital text)'}],
                    'monetary_values': [{'value': '$50,000.00', 'page': 1, 'confidence': 'n/a (digital text)'}],
                    'dates': [{'value': '2026-06-01', 'page': 1, 'confidence': 'n/a (digital text)'}]
                }
            }

            saved_doc = save_document_extraction(doc['id'], extraction_data)
            self.assertEqual(saved_doc.get('extraction_mode'), 'digital_pdf')

            # Verify entities table rows
            db_entities = get_entities_by_document(doc['id'])
            self.assertGreaterEqual(len(db_entities), 3)

            values = [e['value'] for e in db_entities]
            self.assertIn('Acme Corp', values)
            self.assertIn('$50,000.00', values)

            for e in db_entities:
                self.assertEqual(e['confidence'], 'n/a (digital text)')

    def test_dossier_and_ui_display_rule_weight(self):
        """
        Verifies that rule-based confidence numbers are displayed as 'Rule Weight' in dossiers,
        and simulated fallback documents produce visible warning indicators.
        """
        with self.app.app_context():
            case = self._create_test_case('Dossier Display Case')
            doc = create_document({
                'case_id': case['id'],
                'filename': 'scanned_receipt_fallback.png',
                'file_type': 'image/png',
                'file_size': 1024,
                'file_path': self.sample_img_path,
                'file_hash': 'h_disp_001',
                'category': 'Receipt',
                'status': 'Flagged'
            })

            # Save extraction with simulated_fallback
            extraction_data = {
                'full_text': '[Visual Artifact Analysis] Fallback text',
                'extraction_mode': 'simulated_fallback',
                'page_count': 1,
                'total_words': 6,
                'entities': {}
            }
            save_document_extraction(doc['id'], extraction_data)

            # Create a finding with rule weight 0.85
            f = create_finding({
                'case_id': case['id'],
                'document_id': doc['id'],
                'rule_id': 'RULE-VIS-001',
                'title': 'Font Size Discrepancy',
                'severity': 'Medium',
                'category': 'Visual Typography',
                'confidence': 0.85,
                'evidence_class': 'Observation',
                'description': 'Typography baseline variance detected',
                'evidence': '12pt vs 16pt'
            })

            # Check Dossier Data
            dossier_data = generate_case_dossier_data(case['id'])
            doc_inv = dossier_data['documents'][0]
            self.assertEqual(doc_inv.get('extraction_mode'), 'simulated_fallback')

            # Check HTML Dossier
            html_res = generate_dossier_html(case['id'])
            with open(html_res['file_path'], 'r', encoding='utf-8') as hf:
                html_text = hf.read()
            self.assertIn("SIMULATED FALLBACK", html_text)
            self.assertIn("Rule Weight:", html_text)
            self.assertIn("0.85", html_text)

            # Check PDF Dossier
            pdf_res = generate_dossier_pdf(case['id'])
            pdf_doc = fitz.open(pdf_res['file_path'])
            found_weight_label = False
            for page in pdf_doc:
                page_text = page.get_text()
                if "Rule Weight:" in page_text:
                    found_weight_label = True
            pdf_doc.close()
            self.assertTrue(found_weight_label, "PDF dossier should contain 'Rule Weight:' label")


if __name__ == '__main__':
    unittest.main()
