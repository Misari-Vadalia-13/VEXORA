"""
VEXORA — V2 Phase B Unit & Integration Tests: Deeper PDF Forensics & Evidence Classification
Verifies:
1. Evidence classification mapping (Observation, Inconsistency, Potential Manipulation)
2. Individual detectors: PDF-001, PDF-002, PDF-003, PDF-004, PDF-005
3. Master runner run_extended_pdf_forensics
4. Feature flag ENABLE_EXTENDED_FORENSICS behavior in analyze_document
5. Database storage and model hydration of evidence_class
6. Dossier PDF and HTML rendering with evidence class tags
"""

import os
import io
import time
import tempfile
import unittest
from pathlib import Path
from PIL import Image

import pymupdf as fitz

from backend.app import create_app
from backend.config import Config, TestConfig
from backend.database import init_db, get_db
from backend.evidence_class import (
    RULE_EVIDENCE_CLASS_MAP,
    VALID_EVIDENCE_CLASSES,
    get_evidence_class,
    classify_finding
)
from backend.forensics_pdf import (
    EXTENDED_PDF_RULES,
    check_text_hidden_under_shapes,
    check_incremental_updates,
    check_metadata_inconsistencies,
    check_embedded_images_and_resolution,
    check_invisible_and_offpage_text,
    run_extended_pdf_forensics
)
from backend.models import (
    create_case,
    create_document,
    create_finding,
    get_finding_by_id,
    get_findings_by_document,
    get_all_findings
)
from backend.analyzer import analyze_document
from backend.reporter import generate_case_dossier_data, generate_dossier_pdf, generate_dossier_html


class TestEvidenceClassification(unittest.TestCase):
    """Unit tests for evidence class classification rules."""

    def test_evidence_classes_defined(self):
        self.assertIn("Observation", VALID_EVIDENCE_CLASSES)
        self.assertIn("Inconsistency", VALID_EVIDENCE_CLASSES)
        self.assertIn("Potential Manipulation", VALID_EVIDENCE_CLASSES)

    def test_rule_mapping_coverage(self):
        # Baseline rules
        self.assertEqual(get_evidence_class('RULE-VIS-001'), 'Observation')
        self.assertEqual(get_evidence_class('RULE-VIS-002'), 'Potential Manipulation')
        self.assertEqual(get_evidence_class('RULE-CTX-001'), 'Inconsistency')
        self.assertEqual(get_evidence_class('RULE-CTX-004'), 'Inconsistency')
        self.assertEqual(get_evidence_class('RULE-CTX-005'), 'Inconsistency')

        # Extended PDF rules
        self.assertEqual(get_evidence_class('PDF-001'), 'Potential Manipulation')
        self.assertEqual(get_evidence_class('PDF-002'), 'Observation')
        self.assertEqual(get_evidence_class('PDF-003'), 'Inconsistency')
        self.assertEqual(get_evidence_class('PDF-004'), 'Potential Manipulation')
        self.assertEqual(get_evidence_class('PDF-005'), 'Potential Manipulation')

    def test_unknown_rule_fallback(self):
        self.assertEqual(get_evidence_class('UNKNOWN-999'), 'Observation')
        self.assertEqual(get_evidence_class('UNKNOWN-999', 'Inconsistency'), 'Inconsistency')

    def test_classify_finding_helper(self):
        finding = {
            'rule_id': 'PDF-001',
            'title': 'Hidden Text',
            'severity': 'High'
        }
        res = classify_finding(finding)
        self.assertEqual(res.get('evidence_class'), 'Potential Manipulation')

        # Existing valid class preserved
        finding_custom = {
            'rule_id': 'PDF-001',
            'evidence_class': 'Observation'
        }
        res_custom = classify_finding(finding_custom)
        self.assertEqual(res_custom.get('evidence_class'), 'Observation')


class TestExtendedPDFForensicsDetectors(unittest.TestCase):
    """Unit tests for individual PDF forensic detectors using programmatic PDFs."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="vexora_phase_b_detectors_")

    def test_clean_pdf_has_no_extended_findings(self):
        pdf_path = os.path.join(self.test_dir, "clean.pdf")
        doc = fitz.open()
        p = doc.new_page(width=600, height=800)
        p.insert_text(fitz.Point(72, 100), "Standard Clean Commercial Invoice", fontsize=12)
        doc.set_metadata({
            'creationDate': 'D:20260101120000',
            'modDate': 'D:20260101120000',
            'producer': 'ReportEngine 1.0',
            'creator': 'ERP Billing System'
        })
        doc.save(pdf_path)
        doc.close()

        findings = run_extended_pdf_forensics(pdf_path)
        self.assertEqual(len(findings), 0)

    def test_pdf_001_hidden_under_filled_shape(self):
        pdf_path = os.path.join(self.test_dir, "pdf_001_hidden.pdf")
        doc = fitz.open()
        p = doc.new_page(width=600, height=800)
        # Insert text
        p.insert_text(fitz.Point(100, 100), "Original Amount: $99,000.00", fontsize=12)
        # Draw opaque rectangle covering the text
        p.draw_rect(fitz.Rect(90, 85, 300, 115), color=(1, 1, 1), fill=(1, 1, 1))
        doc.save(pdf_path)
        doc.close()

        doc_check = fitz.open(pdf_path)
        findings = check_text_hidden_under_shapes(doc_check)
        doc_check.close()

        self.assertGreaterEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f['rule_id'], 'PDF-001')
        self.assertEqual(f['evidence_class'], 'Potential Manipulation')
        self.assertIn('Original Amount', f['description'])
        self.assertEqual(f['status'], 'Potential Anomaly')

    def test_pdf_002_incremental_updates(self):
        pdf_path = os.path.join(self.test_dir, "pdf_002_incremental.pdf")
        # Base minimal PDF
        doc = fitz.open()
        doc.new_page(width=400, height=400)
        doc.save(pdf_path)
        doc.close()

        # Append incremental update indicator (%%EOF marker)
        with open(pdf_path, 'ab') as f:
            f.write(b"\n% Incremental update chunk\n%%EOF\n")

        findings = check_incremental_updates(pdf_path)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f['rule_id'], 'PDF-002')
        self.assertEqual(f['evidence_class'], 'Observation')
        self.assertIn("incremental update", f['description'].lower())

    def test_pdf_003_metadata_date_divergence(self):
        pdf_path = os.path.join(self.test_dir, "pdf_003_meta.pdf")
        doc = fitz.open()
        doc.new_page(width=400, height=400)
        doc.set_metadata({
            'creationDate': 'D:20240101120000',
            'modDate': 'D:20261102120000',
            'producer': 'ERP System',
            'creator': 'Financial Billing'
        })
        doc.save(pdf_path)
        doc.close()

        doc_check = fitz.open(pdf_path)
        findings = check_metadata_inconsistencies(doc_check)
        doc_check.close()

        self.assertGreaterEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f['rule_id'], 'PDF-003')
        self.assertEqual(f['evidence_class'], 'Inconsistency')
        self.assertIn("differs from original creation date", f['description'])

    def test_pdf_003_commercial_editor_detected(self):
        pdf_path = os.path.join(self.test_dir, "pdf_003_canva.pdf")
        doc = fitz.open()
        doc.new_page(width=400, height=400)
        doc.set_metadata({
            'creationDate': 'D:20260101120000',
            'modDate': 'D:20260101120000',
            'producer': 'Canva PDF Generator 2.0',
            'creator': 'Canva'
        })
        doc.save(pdf_path)
        doc.close()

        doc_check = fitz.open(pdf_path)
        findings = check_metadata_inconsistencies(doc_check)
        doc_check.close()

        self.assertGreaterEqual(len(findings), 1)
        found_editor = any("Canva" in f['title'] for f in findings)
        self.assertTrue(found_editor)

    def test_pdf_004_image_superimposed_over_text(self):
        pdf_path = os.path.join(self.test_dir, "pdf_004_img_overlay.pdf")
        doc = fitz.open()
        p = doc.new_page(width=600, height=800)
        # Insert text
        p.insert_text(fitz.Point(100, 200), "Authorised Signatory John Doe", fontsize=12)

        # Create small test image
        img = Image.new("RGB", (100, 50), color=(180, 20, 20))
        img_bytes_io = io.BytesIO()
        img.save(img_bytes_io, format="PNG")
        img_bytes = img_bytes_io.getvalue()

        # Insert image over the text rect
        p.insert_image(fitz.Rect(95, 180, 250, 220), stream=img_bytes)
        doc.save(pdf_path)
        doc.close()

        doc_check = fitz.open(pdf_path)
        findings = check_embedded_images_and_resolution(doc_check)
        doc_check.close()

        self.assertGreaterEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f['rule_id'], 'PDF-004')
        self.assertEqual(f['evidence_class'], 'Potential Manipulation')
        self.assertIn("superimposed directly over", f['description'])

    def test_pdf_005_offpage_text(self):
        pdf_path = os.path.join(self.test_dir, "pdf_005_offpage.pdf")
        doc = fitz.open()
        p = doc.new_page(width=500, height=500)
        # Place text outside visible boundaries (-50, -50)
        p.insert_text(fitz.Point(-50, -50), "Off-screen secret watermark", fontsize=10)
        doc.save(pdf_path)
        doc.close()

        doc_check = fitz.open(pdf_path)
        findings = check_invisible_and_offpage_text(doc_check)
        doc_check.close()

        self.assertGreaterEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f['rule_id'], 'PDF-005')
        self.assertEqual(f['evidence_class'], 'Potential Manipulation')
        self.assertIn("outside the visible page boundaries", f['description'])

    def test_run_extended_pdf_forensics_non_pdf(self):
        txt_path = os.path.join(self.test_dir, "notes.txt")
        with open(txt_path, 'w') as f:
            f.write("Just a plain text file")

        findings = run_extended_pdf_forensics(txt_path)
        self.assertEqual(findings, [])

    def test_run_extended_pdf_forensics_missing_file(self):
        findings = run_extended_pdf_forensics("non_existent_file_path.pdf")
        self.assertEqual(findings, [])


class TestPhaseBIntegrationAndPersistence(unittest.TestCase):
    """Integration tests verifying DB schema migration, models, and analyzer."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="vexora_phase_b_integration_")
        cls.test_db = os.path.join(cls.test_dir, "phase_b.db")
        cls.test_uploads = os.path.join(cls.test_dir, "uploads")
        cls.test_reports = os.path.join(cls.test_dir, "reports")
        os.makedirs(cls.test_uploads, exist_ok=True)
        os.makedirs(cls.test_reports, exist_ok=True)

        class PhaseBTestConfig(TestConfig):
            DATABASE = cls.test_db
            UPLOAD_FOLDER = cls.test_uploads
            REPORTS_FOLDER = cls.test_reports
            TESTING = True
            ENABLE_EXTENDED_FORENSICS = True

        cls.config_class = PhaseBTestConfig
        cls.app = create_app(PhaseBTestConfig)

        with cls.app.app_context():
            init_db(cls.test_db)

        # Create a test PDF with white-box redaction (PDF-001)
        cls.sample_tampered_pdf = os.path.join(cls.test_uploads, "tampered_invoice.pdf")
        doc = fitz.open()
        p = doc.new_page(width=595, height=842)
        p.insert_text(fitz.Point(72, 100), "INVOICE #INV-2026-B001", fontsize=14)
        p.insert_text(fitz.Point(72, 150), "Original Fee: $1,250,000", fontsize=12)
        # Cover the fee with a white box
        p.draw_rect(fitz.Rect(65, 135, 250, 165), color=(1, 1, 1), fill=(1, 1, 1))
        doc.save(cls.sample_tampered_pdf)
        doc.close()

    def _create_test_case(self, title):
        return create_case({
            'title': title,
            'type': 'Financial Audit',
            'priority': 'High',
            'status': 'Active',
            'investigator': 'Lead Investigator',
            'description': 'Integration test case'
        })

    def test_model_persistence_and_hydration(self):
        with self.app.app_context():
            case = self._create_test_case('Model Test Case')
            doc = create_document({
                'case_id': case['id'],
                'filename': 'test.pdf',
                'file_type': 'pdf',
                'file_size': 1024,
                'file_path': self.sample_tampered_pdf,
                'file_hash': 'h12345',
                'category': 'Invoice',
                'status': 'Pending'
            })

            # Create finding with explicit evidence_class
            f = create_finding({
                'document_id': doc['id'],
                'rule_id': 'PDF-001',
                'title': 'White Box Redaction',
                'severity': 'High',
                'category': 'Visual Structure',
                'evidence_class': 'Potential Manipulation',
                'description': 'Text hidden under shape',
                'evidence': 'Text under box'
            })

            self.assertEqual(f.get('evidence_class'), 'Potential Manipulation')

            # Retrieve by ID
            f_fetched = get_finding_by_id(f['id'])
            self.assertIsNotNone(f_fetched)
            self.assertEqual(f_fetched.get('evidence_class'), 'Potential Manipulation')

            # Retrieve by document
            doc_findings = get_findings_by_document(doc['id'])
            self.assertEqual(len(doc_findings), 1)
            self.assertEqual(doc_findings[0].get('evidence_class'), 'Potential Manipulation')

    def test_analyzer_with_flag_enabled_finds_pdf_001(self):
        with self.app.app_context():
            case = self._create_test_case('Analyzer Flag Test Case')
            doc = create_document({
                'case_id': case['id'],
                'filename': 'tampered_invoice.pdf',
                'file_type': 'pdf',
                'file_size': os.path.getsize(self.sample_tampered_pdf),
                'file_path': self.sample_tampered_pdf,
                'file_hash': 'tampered_hash_1',
                'category': 'Invoice',
                'status': 'Pending'
            })

            result = analyze_document(doc['id'], user="Forensic Analyst")
            self.assertIn('findings', result)

            # Check that PDF-001 was detected
            pdf_001_findings = [f for f in result['findings'] if f.get('rule_id') == 'PDF-001']
            self.assertGreaterEqual(len(pdf_001_findings), 1)
            f = pdf_001_findings[0]
            self.assertEqual(f.get('evidence_class'), 'Potential Manipulation')
            self.assertEqual(f.get('rule_id'), 'PDF-001')

    def test_analyzer_with_flag_disabled(self):
        with self.app.app_context():
            # Temporarily disable flag
            Config.ENABLE_EXTENDED_FORENSICS = False
            case = self._create_test_case('Flag Disabled Test Case')
            doc = create_document({
                'case_id': case['id'],
                'filename': 'tampered_invoice_2.pdf',
                'file_type': 'pdf',
                'file_size': os.path.getsize(self.sample_tampered_pdf),
                'file_path': self.sample_tampered_pdf,
                'file_hash': 'tampered_hash_2',
                'category': 'Invoice',
                'status': 'Pending'
            })

            result = analyze_document(doc['id'], user="Forensic Analyst")
            pdf_findings = [f for f in result['findings'] if f.get('rule_id', '').startswith('PDF-')]
            self.assertEqual(len(pdf_findings), 0)

            # Restore flag
            Config.ENABLE_EXTENDED_FORENSICS = True

    def test_dossier_contains_evidence_class(self):
        with self.app.app_context():
            case = self._create_test_case('Dossier Evidence Class Case')
            doc = create_document({
                'case_id': case['id'],
                'filename': 'tampered_invoice_dossier.pdf',
                'file_type': 'pdf',
                'file_size': os.path.getsize(self.sample_tampered_pdf),
                'file_path': self.sample_tampered_pdf,
                'file_hash': 'tampered_hash_dossier',
                'category': 'Invoice',
                'status': 'Pending'
            })

            analyze_document(doc['id'], user="Auditor")

            # Check dossier structured data
            dossier_data = generate_case_dossier_data(case['id'])
            self.assertGreater(len(dossier_data['findings']), 0)
            for f in dossier_data['findings']:
                self.assertIn(f.get('evidence_class'), VALID_EVIDENCE_CLASSES)

            # Generate HTML dossier and check for evidence_class badge
            html_report = generate_dossier_html(case['id'])
            self.assertTrue(os.path.exists(html_report['file_path']))
            with open(html_report['file_path'], 'r', encoding='utf-8') as f_html:
                html_text = f_html.read()
            self.assertTrue(
                "Potential Manipulation" in html_text or
                "Inconsistency" in html_text or
                "Observation" in html_text
            )

            # Sleep slightly to avoid report ID collision
            time.sleep(1.05)
            # Generate PDF dossier
            pdf_report = generate_dossier_pdf(case['id'], user="Auditor")
            self.assertTrue(os.path.exists(pdf_report['file_path']))
            self.assertGreater(pdf_report['file_size'], 1000)


if __name__ == '__main__':
    unittest.main()
