"""
VEXORA — V2 Phase K Test Suite: Dossier Completeness (P5 Fix)
Verifies:
1. All 5 new dossier sections appear in generated PDF dossiers:
   - K1: Extracted Information & Field Confidence
   - K2: Evidence and Traceability (top 5 findings with highlighted image, rule ID, class label, page, box, quote)
   - K3: Plain-language Investigation Summary
   - K4: Areas Requiring Further Verification
   - K5: Limitations (static and dynamic)
2. All 5 new dossier sections appear in generated HTML dossiers.
3. Simulated fallback extraction mode displays a prominent visible warning.
4. Report generation still succeeds when evidence rendering fails or throws an exception.
5. Report generation still succeeds when AI data is completely absent.
6. generate_case_dossier_data returns all 5 required structured keys.
"""

import os
import unittest
from unittest.mock import patch
from pathlib import Path
import pymupdf as fitz  # PyMuPDF

from backend.config import Config, TestConfig
from backend.app import create_app
from backend.database import init_db, execute_db
from backend.models import (
    create_case,
    create_document,
    save_document_extraction,
    create_finding
)
from backend.extractor import extract_document_content
from backend.reporter import (
    generate_case_dossier_data,
    generate_dossier_pdf,
    generate_dossier_html
)


class TestV2PhaseK(unittest.TestCase):
    """Automated test cases for Phase K Dossier Completeness."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestConfig)
        cls.client = cls.app.test_client()
        cls.dataset_dir = Path(__file__).resolve().parent.parent / 'demo_dataset'

    def setUp(self):
        init_db(TestConfig.DATABASE)
        execute_db("DELETE FROM findings WHERE case_id LIKE 'CAS-TEST-K%'")
        execute_db("DELETE FROM documents WHERE id LIKE '%TEST-K%' OR case_id LIKE 'CAS-TEST-K%'")
        execute_db("DELETE FROM cases WHERE id LIKE 'CAS-TEST-K%'")

    def tearDown(self):
        init_db(TestConfig.DATABASE)
        execute_db("DELETE FROM findings WHERE case_id LIKE 'CAS-TEST-K%'")
        execute_db("DELETE FROM documents WHERE id LIKE '%TEST-K%' OR case_id LIKE 'CAS-TEST-K%'")
        execute_db("DELETE FROM cases WHERE id LIKE 'CAS-TEST-K%'")

    def _setup_sample_case(self, case_id='CAS-TEST-K-MAIN', extraction_mode='digital_pdf'):
        """Helper to create a populated case with documents and findings."""
        case = create_case({
            'title': 'Dossier Completeness Verification Case',
            'type': 'Procurement Fraud Investigation',
            'priority': 'Critical',
            'status': 'Active',
            'investigator': 'Lead Forensic Inspector',
            'description': 'Evaluating completeness of forensic dossier sections K1-K5.'
        }, custom_id=case_id)

        f1 = self.dataset_dir / 'tampered_01_font_shift.pdf'
        doc1 = create_document({
            'id': f'DOC-{case_id}-01',
            'case_id': case_id,
            'filename': 'tampered_01_font_shift.pdf',
            'file_type': 'pdf',
            'file_size': f1.stat().st_size,
            'file_path': str(f1.resolve()),
            'category': 'Invoice',
            'status': 'Flagged'
        })
        save_document_extraction(doc1['id'], extract_document_content(str(f1)))
        if extraction_mode != 'digital_pdf':
            execute_db("UPDATE documents SET extraction_mode = ? WHERE id = ?", (extraction_mode, doc1['id']))

        # Create findings for top 5 evidence traceability
        create_finding({
            'document_id': doc1['id'],
            'case_id': case_id,
            'rule_id': 'RULE-VIS-002',
            'title': 'Overlapping Text Elements Detected',
            'severity': 'Critical',
            'category': 'Visual Formatting',
            'evidence_class': 'Potential Manipulation',
            'description': 'Dual-layer text printing with numeric overwriting.',
            'evidence': 'Total Amount $5,000.00',
            'page_number': 1,
            'coordinates': '[50, 100, 250, 130]',
            'confidence': 0.95
        })

        create_finding({
            'document_id': doc1['id'],
            'case_id': case_id,
            'rule_id': 'PDF-003',
            'title': 'Disallowed Image Editing Software Metadata',
            'severity': 'High',
            'category': 'Metadata Integrity',
            'evidence_class': 'Inconsistency',
            'description': 'PDF creator software metadata indicates Adobe Photoshop CC.',
            'evidence': 'Creator: Adobe Photoshop CC',
            'page_number': 1,
            'coordinates': '',
            'confidence': 0.92
        })

        return case_id

    def test_01_all_phase_k_sections_present_in_pdf(self):
        """PDF dossier contains all 5 required Phase K sections: K1, K2, K3, K4, K5."""
        with self.app.app_context():
            case_id = self._setup_sample_case('CAS-TEST-K-PDF')
            pdf_res = generate_dossier_pdf(case_id)
            self.assertTrue(pdf_res['success'])
            pdf_path = pdf_res['file_path']
            self.assertTrue(os.path.exists(pdf_path))

            doc_pdf = fitz.open(pdf_path)
            full_text = ""
            for p in doc_pdf:
                full_text += p.get_text()
            doc_pdf.close()

            # K1: Extracted Information
            self.assertIn("EXTRACTED INFORMATION", full_text)
            self.assertIn("tampered_01_font_shift.pdf", full_text)

            # K2: Evidence and Traceability (top findings)
            self.assertIn("EVIDENCE AND TRACEABILITY", full_text)
            self.assertIn("RULE-VIS-002", full_text)
            self.assertIn("Class: Potential Manipulation", full_text)

            # K3: Plain-language Investigation Summary
            self.assertIn("INVESTIGATION SUMMARY", full_text)

            # K4: Areas Requiring Further Verification
            self.assertIn("AREAS REQUIRING FURTHER VERIFICATION", full_text)

            # K5: Limitations
            self.assertIn("LIMITATIONS", full_text)
            self.assertIn("Digital vs. Physical Materiality", full_text)

    def test_02_all_phase_k_sections_present_in_html(self):
        """HTML dossier contains all 5 required Phase K sections with structured formatting."""
        with self.app.app_context():
            case_id = self._setup_sample_case('CAS-TEST-K-HTML')
            html_res = generate_dossier_html(case_id)
            self.assertTrue(html_res['success'])
            html_path = html_res['file_path']
            self.assertTrue(os.path.exists(html_path))

            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # K1: Extracted Information & Field Confidence
            self.assertIn("Extracted Information & Field Confidence", content)
            self.assertIn("Confidence", content)

            # K2: Evidence & Traceability
            self.assertIn("Evidence & Traceability", content)
            self.assertIn("Class: Potential Manipulation", content)
            self.assertIn("RULE-VIS-002", content)
            self.assertIn("Source Quote:", content)

            # K3: Plain-Language Investigation Summary
            self.assertIn("Plain-Language Investigation Summary", content)

            # K4: Areas Requiring Further Verification
            self.assertIn("Areas Requiring Further Verification", content)

            # K5: Limitations & System Boundaries
            self.assertIn("Limitations & System Boundaries", content)
            self.assertIn("Standard System Assumptions", content)

    def test_03_simulated_fallback_visible_warning(self):
        """Simulated fallback extraction mode displays a prominent visible warning in PDF and HTML."""
        with self.app.app_context():
            case_id = self._setup_sample_case('CAS-TEST-K-SIM', extraction_mode='simulated_fallback')

            pdf_res = generate_dossier_pdf(case_id)
            doc_pdf = fitz.open(pdf_res['file_path'])
            pdf_text = "".join(p.get_text() for p in doc_pdf)
            doc_pdf.close()
            self.assertIn("Simulated Fallback", pdf_text)

            html_res = generate_dossier_html(case_id)
            with open(html_res['file_path'], 'r', encoding='utf-8') as f:
                html_text = f.read()
            self.assertIn("Simulated Fallback", html_text)

    def test_04_report_generation_succeeds_when_evidence_rendering_fails(self):
        """Dossier PDF and HTML generation never fails even if visual evidence rendering raises an exception."""
        with self.app.app_context():
            case_id = self._setup_sample_case('CAS-TEST-K-FAIL')

            with patch('backend.evidence.get_finding_evidence_image', side_effect=RuntimeError("Image rendering crash")):
                pdf_res = generate_dossier_pdf(case_id)
                self.assertTrue(pdf_res['success'])
                self.assertTrue(os.path.exists(pdf_res['file_path']))

                html_res = generate_dossier_html(case_id)
                self.assertTrue(html_res['success'])
                self.assertTrue(os.path.exists(html_res['file_path']))

    def test_05_report_generation_succeeds_when_ai_data_missing(self):
        """Dossier PDF and HTML generation succeeds cleanly when AI insights and findings are absent."""
        with self.app.app_context():
            case_id = self._setup_sample_case('CAS-TEST-K-NOAI')

            with patch('backend.models.get_ai_insights_by_case', return_value=[]):
                data = generate_case_dossier_data(case_id)
                self.assertIsNone(data.get('ai_summary'))
                self.assertIsNotNone(data.get('investigation_summary'))

                pdf_res = generate_dossier_pdf(case_id)
                self.assertTrue(pdf_res['success'])

                html_res = generate_dossier_html(case_id)
                self.assertTrue(html_res['success'])

    def test_06_dossier_data_structure_completeness(self):
        """generate_case_dossier_data returns all 5 Phase K keys properly structured."""
        with self.app.app_context():
            case_id = self._setup_sample_case('CAS-TEST-K-DATA')
            data = generate_case_dossier_data(case_id)

            self.assertIn('extracted_information', data)
            self.assertIn('evidence_traceability', data)
            self.assertIn('investigation_summary', data)
            self.assertIn('areas_for_verification', data)
            self.assertIn('limitations', data)

            # Check K1 structure
            self.assertIsInstance(data['extracted_information'], list)
            self.assertGreaterEqual(len(data['extracted_information']), 1)
            self.assertIn('fields', data['extracted_information'][0])

            # Check K2 structure
            self.assertIsInstance(data['evidence_traceability'], list)
            self.assertLessEqual(len(data['evidence_traceability']), 5)
            if data['evidence_traceability']:
                first_ev = data['evidence_traceability'][0]
                self.assertIn('class_label', first_ev)
                self.assertIn('rule_id', first_ev)
                self.assertIn('quoted_text', first_ev)

            # Check K4 structure
            self.assertIsInstance(data['areas_for_verification'], list)
            self.assertGreaterEqual(len(data['areas_for_verification']), 1)

            # Check K5 structure
            self.assertIn('static', data['limitations'])
            self.assertIn('dynamic', data['limitations'])


if __name__ == '__main__':
    unittest.main()
