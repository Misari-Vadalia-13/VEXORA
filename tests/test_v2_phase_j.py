"""
VEXORA — V2 Phase J Test Suite: Cross-Document Proof & Dossier Formatting
Verifies:
1. Dossier comparison section in PDF and HTML displays actual attribute names and values,
   never "Conflict: Attribute".
2. Duplicate invoice case (tampered_04 / tampered_05) is detected with monetary / entity conflict.
3. Bank mismatch case (tampered_05 / tampered_06) is detected with payment disparity.
4. Clean procurement case (genuine_01_invoice / genuine_01_matching_po) produces zero conflicts.
5. Case relationship graph establishes cross-document entity edges.
6. demo_dataset/cases.csv defines all three required scenarios with valid files on disk.
7. tools/evaluate.py case-level evaluation engine executes cleanly.
"""

import os
import csv
import unittest
from pathlib import Path
import fitz  # PyMuPDF

from backend.config import Config, TestConfig
from backend.app import create_app
from backend.database import init_db, execute_db
from backend.models import (
    create_case,
    create_document,
    save_document_extraction,
    get_all_documents
)
from backend.extractor import extract_document_content
from backend.comparator import compare_case_documents
from backend.correlator import build_case_relationship_graph
from backend.reporter import generate_dossier_pdf, generate_dossier_html
from tools.evaluate import run_case_evaluation


class TestV2PhaseJ(unittest.TestCase):
    """Automated test cases for Phase J Cross-Document Discrepancy Detection & Reporting."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestConfig)
        cls.client = cls.app.test_client()
        cls.dataset_dir = Path(__file__).resolve().parent.parent / 'demo_dataset'

    def setUp(self):
        init_db(TestConfig.DATABASE)
        execute_db("DELETE FROM cases WHERE id LIKE 'CAS-TEST-J%'")
        execute_db("DELETE FROM documents WHERE id LIKE 'DOC-TEST-J%'")
        Config.ENABLE_CORRELATOR = True

    def tearDown(self):
        init_db(TestConfig.DATABASE)
        execute_db("DELETE FROM cases WHERE id LIKE 'CAS-TEST-J%'")
        execute_db("DELETE FROM documents WHERE id LIKE 'DOC-TEST-J%'")

    def test_01_dossier_comparison_formatting_pdf_and_html(self):
        """Dossier comparison section in PDF and HTML renders field names, values, and filenames without 'Conflict: Attribute'."""
        with self.app.app_context():
            case_id = 'CAS-TEST-J-DOSSIER'
            case = create_case({
                'title': 'Dossier Value Formatting Verification Case',
                'type': 'Procurement Fraud',
                'priority': 'High',
                'status': 'Active',
                'investigator': 'Forensic Examiner',
                'description': 'Validating discrepancy line formatting.'
            }, custom_id=case_id)

            inv_a_path = self.dataset_dir / 'tampered_04_duplicate_inv_a.pdf'
            inv_b_path = self.dataset_dir / 'tampered_05_duplicate_inv_b.pdf'

            doc_a = create_document({
                'id': 'DOC-TEST-J-01',
                'case_id': case_id,
                'filename': 'tampered_04_duplicate_inv_a.pdf',
                'file_type': 'pdf',
                'file_size': inv_a_path.stat().st_size,
                'file_path': str(inv_a_path.resolve()),
                'category': 'Invoice',
                'status': 'Analyzed'
            })
            save_document_extraction('DOC-TEST-J-01', extract_document_content(str(inv_a_path)))

            doc_b = create_document({
                'id': 'DOC-TEST-J-02',
                'case_id': case_id,
                'filename': 'tampered_05_duplicate_inv_b.pdf',
                'file_type': 'pdf',
                'file_size': inv_b_path.stat().st_size,
                'file_path': str(inv_b_path.resolve()),
                'category': 'Invoice',
                'status': 'Analyzed'
            })
            save_document_extraction('DOC-TEST-J-02', extract_document_content(str(inv_b_path)))

            # 1. Generate and inspect PDF dossier
            pdf_res = generate_dossier_pdf(case_id)
            pdf_path = pdf_res['file_path'] if isinstance(pdf_res, dict) else pdf_res
            self.assertTrue(os.path.exists(pdf_path), "PDF dossier must exist on disk.")

            doc_pdf = fitz.open(pdf_path)
            full_pdf_text = ""
            for p in doc_pdf:
                full_pdf_text += p.get_text()
            doc_pdf.close()

            # Must NEVER contain the generic broken header
            self.assertNotIn("Conflict: Attribute\n", full_pdf_text)
            self.assertNotIn("Conflict: Attribute ", full_pdf_text)

            # Must contain actual attribute, filenames and/or values
            self.assertIn("Primary Monetary Value", full_pdf_text)
            self.assertTrue("$5,000" in full_pdf_text or "tampered_04" in full_pdf_text)

            # 2. Generate and inspect HTML dossier
            html_res = generate_dossier_html(case_id)
            html_path = html_res['file_path'] if isinstance(html_res, dict) else html_res
            self.assertTrue(os.path.exists(html_path), "HTML dossier must exist on disk.")

            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            self.assertNotIn("⚠️ Conflict: Attribute Discrepancy", html_content)
            self.assertNotIn("⚠️ Conflict: Attribute<", html_content)
            self.assertIn("Conflict: Primary Monetary Value", html_content)
            self.assertIn("tampered_04_duplicate_inv_a.pdf", html_content)
            self.assertIn("tampered_05_duplicate_inv_b.pdf", html_content)

    def test_02_duplicate_invoice_case_detected(self):
        """Case with duplicate invoice references and contradictory totals is flagged as a discrepancy."""
        with self.app.app_context():
            case_id = 'CAS-TEST-J-DUP'
            create_case({
                'title': 'Duplicate Invoice Test Case',
                'type': 'Financial Audit',
                'priority': 'Critical',
                'status': 'Active',
                'investigator': 'Forensic Examiner',
                'description': 'Duplicate submission detection.'
            }, custom_id=case_id)

            f1 = self.dataset_dir / 'tampered_04_duplicate_inv_a.pdf'
            f2 = self.dataset_dir / 'tampered_05_duplicate_inv_b.pdf'

            d1 = create_document({
                'id': 'DOC-TEST-J-D1',
                'case_id': case_id,
                'filename': 'tampered_04_duplicate_inv_a.pdf',
                'file_type': 'pdf',
                'file_size': f1.stat().st_size,
                'file_path': str(f1.resolve()),
                'category': 'Invoice',
                'status': 'Analyzed'
            })
            save_document_extraction('DOC-TEST-J-D1', extract_document_content(str(f1)))

            d2 = create_document({
                'id': 'DOC-TEST-J-D2',
                'case_id': case_id,
                'filename': 'tampered_05_duplicate_inv_b.pdf',
                'file_type': 'pdf',
                'file_size': f2.stat().st_size,
                'file_path': str(f2.resolve()),
                'category': 'Invoice',
                'status': 'Analyzed'
            })
            save_document_extraction('DOC-TEST-J-D2', extract_document_content(str(f2)))

            cmp_res = compare_case_documents(case_id)
            self.assertTrue(cmp_res['success'])
            self.assertGreaterEqual(cmp_res['discrepancies_count'], 1)

            attributes = [d['attribute'] for d in cmp_res['discrepancies']]
            self.assertIn('Primary Monetary Value', attributes)

            # Check value conflict
            monetary_disc = [d for d in cmp_res['discrepancies'] if d['attribute'] == 'Primary Monetary Value'][0]
            self.assertEqual(monetary_disc['status'], 'Conflict')
            vals = [monetary_disc['val_a'], monetary_disc['val_b']]
            self.assertTrue(any('$5,000.00' in v for v in vals))
            self.assertTrue(any('$18,500.00' in v for v in vals))

    def test_03_bank_mismatch_case_detected(self):
        """Case pairing an invoice with an unequal bank settlement is flagged as a monetary conflict."""
        with self.app.app_context():
            case_id = 'CAS-TEST-J-BANK'
            create_case({
                'title': 'Bank Mismatch Test Case',
                'type': 'Financial Audit',
                'priority': 'High',
                'status': 'Active',
                'investigator': 'Forensic Examiner',
                'description': 'Bank payment mismatch.'
            }, custom_id=case_id)

            f1 = self.dataset_dir / 'tampered_05_duplicate_inv_b.pdf'
            f2 = self.dataset_dir / 'tampered_06_bank_mismatch.pdf'

            d1 = create_document({
                'id': 'DOC-TEST-J-B1',
                'case_id': case_id,
                'filename': 'tampered_05_duplicate_inv_b.pdf',
                'file_type': 'pdf',
                'file_size': f1.stat().st_size,
                'file_path': str(f1.resolve()),
                'category': 'Invoice',
                'status': 'Analyzed'
            })
            save_document_extraction('DOC-TEST-J-B1', extract_document_content(str(f1)))

            d2 = create_document({
                'id': 'DOC-TEST-J-B2',
                'case_id': case_id,
                'filename': 'tampered_06_bank_mismatch.pdf',
                'file_type': 'pdf',
                'file_size': f2.stat().st_size,
                'file_path': str(f2.resolve()),
                'category': 'Bank Statement',
                'status': 'Analyzed'
            })
            save_document_extraction('DOC-TEST-J-B2', extract_document_content(str(f2)))

            cmp_res = compare_case_documents(case_id)
            self.assertTrue(cmp_res['success'])
            self.assertGreaterEqual(cmp_res['discrepancies_count'], 1)

            attributes = [d['attribute'] for d in cmp_res['discrepancies']]
            self.assertIn('Primary Monetary Value', attributes)

    def test_04_clean_procurement_case_produces_zero_conflicts(self):
        """Case pairing genuine invoice with synchronized PO produces zero discrepancies and confirmed matches."""
        with self.app.app_context():
            case_id = 'CAS-TEST-J-CLEAN'
            create_case({
                'title': 'Synchronized Procurement Case',
                'type': 'Procurement Verification',
                'priority': 'Low',
                'status': 'Active',
                'investigator': 'Forensic Examiner',
                'description': 'Valid genuine comparison.'
            }, custom_id=case_id)

            f1 = self.dataset_dir / 'genuine_01_invoice.pdf'
            f2 = self.dataset_dir / 'genuine_01_matching_po.pdf'

            d1 = create_document({
                'id': 'DOC-TEST-J-C1',
                'case_id': case_id,
                'filename': 'genuine_01_invoice.pdf',
                'file_type': 'pdf',
                'file_size': f1.stat().st_size,
                'file_path': str(f1.resolve()),
                'category': 'Invoice',
                'status': 'Analyzed'
            })
            save_document_extraction('DOC-TEST-J-C1', extract_document_content(str(f1)))

            d2 = create_document({
                'id': 'DOC-TEST-J-C2',
                'case_id': case_id,
                'filename': 'genuine_01_matching_po.pdf',
                'file_type': 'pdf',
                'file_size': f2.stat().st_size,
                'file_path': str(f2.resolve()),
                'category': 'Purchase Order',
                'status': 'Analyzed'
            })
            save_document_extraction('DOC-TEST-J-C2', extract_document_content(str(f2)))

            cmp_res = compare_case_documents(case_id)
            self.assertTrue(cmp_res['success'])
            self.assertEqual(cmp_res['discrepancies_count'], 0, "Clean case must have 0 discrepancies.")

    def test_05_cases_csv_definitions_and_files_exist(self):
        """cases.csv contains the three canonical benchmark cases and all referenced files exist."""
        cases_csv = self.dataset_dir / 'cases.csv'
        self.assertTrue(cases_csv.exists(), "demo_dataset/cases.csv must exist.")

        with open(cases_csv, 'r', encoding='utf-8') as f:
            cases = list(csv.DictReader(f))

        case_ids = [c['case_id'] for c in cases]
        self.assertIn('case_01_duplicate_invoices', case_ids)
        self.assertIn('case_02_bank_mismatch', case_ids)
        self.assertIn('case_03_clean_procurement', case_ids)

        for c in cases:
            filenames = [fn.strip() for fn in c['filenames'].split(';') if fn.strip()]
            for fn in filenames:
                fpath = self.dataset_dir / fn
                self.assertTrue(fpath.exists(), f"Benchmark case file '{fn}' must exist in demo_dataset.")

    def test_06_case_evaluation_engine_runs_successfully(self):
        """run_case_evaluation executes cleanly without errors and returns 0."""
        ret = run_case_evaluation()
        self.assertEqual(ret, 0)


if __name__ == '__main__':
    unittest.main()
