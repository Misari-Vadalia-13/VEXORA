"""
VEXORA — Automated Benchmark Evaluator Unit Test Suite
Verifies:
- Accurate binary metric calculations with zero-division safety
- Proper 2x2 confusion matrix generation
- Strict error isolation (processing errors do not count as anomaly detections)
- Rule-level classification fidelity evaluation
- Correct machine-readable JSON and CSV report export
"""

import unittest
import json
import csv
from pathlib import Path

from unittest.mock import patch
from tools.evaluate import (
    compute_binary_metrics,
    render_confusion_matrix_ascii,
    export_benchmark_reports,
    evaluate_document_record
)


class VexoraBenchmarkEvaluatorTestCase(unittest.TestCase):
    """Test suite covering the benchmark evaluation calculations and output integrity."""

    def test_compute_binary_metrics_standard(self):
        """Verifies standard evaluation metrics calculation matches mathematical definitions."""
        # Baseline: TP=7, TN=10, FP=0, FN=3 (Total=20)
        metrics = compute_binary_metrics(tp=7, tn=10, fp=0, fn=3)

        self.assertEqual(metrics['total_evaluated'], 20)
        self.assertEqual(metrics['true_positives'], 7)
        self.assertEqual(metrics['true_negatives'], 10)
        self.assertEqual(metrics['false_positives'], 0)
        self.assertEqual(metrics['false_negatives'], 3)

        # Accuracy = (7 + 10) / 20 = 17 / 20 = 85.0%
        self.assertEqual(metrics['accuracy_pct'], 85.0)

        # Precision = 7 / (7 + 0) = 100.0%
        self.assertEqual(metrics['precision_pct'], 100.0)

        # Recall = 7 / (7 + 3) = 7 / 10 = 70.0%
        self.assertEqual(metrics['recall_pct'], 70.0)

        # Specificity = 10 / (10 + 0) = 100.0%
        self.assertEqual(metrics['specificity_pct'], 100.0)

        # F1 = 2 * (1.0 * 0.7) / (1.0 + 0.7) = 1.4 / 1.7 = 82.35%
        self.assertAlmostEqual(metrics['f1_score_pct'], 82.35, places=2)

        # 2x2 Confusion matrix: [[TN, FP], [FN, TP]]
        expected_cm = [[10, 0], [3, 7]]
        self.assertEqual(metrics['confusion_matrix'], expected_cm)

    def test_compute_binary_metrics_zero_division_safety(self):
        """Verifies that edge cases with zero denominators return 0.0 without throwing ZeroDivisionError."""
        # 1. Zero Total (no data)
        zero_total = compute_binary_metrics(tp=0, tn=0, fp=0, fn=0)
        self.assertEqual(zero_total['accuracy_pct'], 0.0)
        self.assertEqual(zero_total['precision_pct'], 0.0)
        self.assertEqual(zero_total['recall_pct'], 0.0)
        self.assertEqual(zero_total['specificity_pct'], 0.0)
        self.assertEqual(zero_total['f1_score_pct'], 0.0)
        self.assertEqual(zero_total['confusion_matrix'], [[0, 0], [0, 0]])

        # 2. No positive predictions (TP=0, FP=0) -> Precision denominator is 0
        no_positives = compute_binary_metrics(tp=0, tn=10, fp=0, fn=5)
        self.assertEqual(no_positives['precision_pct'], 0.0)
        self.assertEqual(no_positives['recall_pct'], 0.0)
        self.assertEqual(no_positives['specificity_pct'], 100.0)

        # 3. No actual positives (TP=0, FN=0) -> Recall denominator is 0
        no_actual_positives = compute_binary_metrics(tp=0, tn=15, fp=3, fn=0)
        self.assertEqual(no_actual_positives['recall_pct'], 0.0)
        self.assertEqual(no_actual_positives['precision_pct'], 0.0)
        self.assertEqual(no_actual_positives['specificity_pct'], round(15 / 18 * 100, 2))

        # 4. No actual negatives (TN=0, FP=0) -> Specificity denominator is 0
        no_actual_negatives = compute_binary_metrics(tp=10, tn=0, fp=0, fn=2)
        self.assertEqual(no_actual_negatives['specificity_pct'], 0.0)
        self.assertEqual(no_actual_negatives['recall_pct'], round(10 / 12 * 100, 2))

    def test_ascii_confusion_matrix_rendering(self):
        """Verifies ASCII representation contains expected counts and labels."""
        cm = [[10, 1], [2, 7]]
        rendered = render_confusion_matrix_ascii(cm)
        self.assertIn("True Negative (TN) = 10", rendered)
        self.assertIn("False Positive (FP) = 1", rendered)
        self.assertIn("False Negative (FN) = 2", rendered)
        self.assertIn("True Positive (TP) = 7", rendered)

    def test_benchmark_export_generation(self):
        """Verifies export_benchmark_reports generates all 5 unified artifacts without contaminating reports/."""
        import tempfile
        import shutil

        temp_dir = Path(tempfile.mkdtemp(prefix="vexora_eval_test_"))
        try:
            mock_single_doc = {
                'doc_metrics': compute_binary_metrics(tp=7, tn=10, fp=0, fn=3),
                'total_expected_rule_docs': 10,
                'exact_rule_hits': 3,
                'exact_rule_pct': 30.0,
                'rule_counts': {'RULE-CTX-003': 2, 'PDF-003': 2},
                'doc_results': [
                    {
                        'filename': 'test_tampered.pdf',
                        'is_tampered': 1,
                        'detected_anomaly': True,
                        'expected_rules': ['RULE-CTX-003'],
                        'fired_rules': ['RULE-CTX-003'],
                        'matched_rules': ['RULE-CTX-003'],
                        'doc_verdict': 'TP (HIT)',
                        'rule_match_verdict': 'HIT (RULE-CTX-003)',
                        'processing_error': None
                    }
                ]
            }
            mock_case_data = {
                'case_metrics': compute_binary_metrics(tp=2, tn=1, fp=0, fn=0),
                'case_results': [
                    {
                        'case_id': 'case_01',
                        'title': 'Test Case',
                        'is_tampered': 1,
                        'discrepancies_detected': ['Primary Monetary Value'],
                        'verdict': 'TP (HIT)'
                    }
                ]
            }

            # Export strictly to temporary isolated directory
            export_benchmark_reports(mock_single_doc, mock_case_data, output_dir=temp_dir)

            json_file = temp_dir / 'benchmark_results.json'
            csv_file = temp_dir / 'benchmark_results.csv'
            md_file = temp_dir / 'benchmark_report.md'
            cm_file = temp_dir / 'confusion_matrix.json'
            summary_file = temp_dir / 'benchmark_summary.txt'

            self.assertTrue(json_file.exists(), "benchmark_results.json missing from export")
            self.assertTrue(csv_file.exists(), "benchmark_results.csv missing from export")
            self.assertTrue(md_file.exists(), "benchmark_report.md missing from export")
            self.assertTrue(cm_file.exists(), "confusion_matrix.json missing from export")
            self.assertTrue(summary_file.exists(), "benchmark_summary.txt missing from export")

            # 1. Verify JSON structure
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.assertEqual(data['benchmark_suite'], 'VEXORA Forensic Benchmark Suite')
                self.assertEqual(data['document_level_metrics']['accuracy_pct'], 85.0)
                self.assertEqual(data['case_level_metrics']['accuracy_pct'], 100.0)

            # 2. Verify CSV content
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
                self.assertGreaterEqual(len(rows), 2)
                header = rows[0]
                self.assertIn('filename', header)
                self.assertIn('matched_rules', header)
                self.assertIn('doc_verdict', header)

            # 3. Verify Dedicated Confusion Matrix JSON
            with open(cm_file, 'r', encoding='utf-8') as f:
                cm_data = json.load(f)
                self.assertIn('document_level', cm_data)
                self.assertIn('case_level', cm_data)
                self.assertEqual(cm_data['document_level']['matrix'], [[10, 0], [3, 7]])
                self.assertEqual(cm_data['document_level']['counts']['true_positives'], 7)

            # 4. Verify Summary and Markdown
            md_text = md_file.read_text(encoding='utf-8')
            self.assertIn("VEXORA Forensic Intelligence System", md_text)
            self.assertIn("Confusion Matrix", md_text)

            sum_text = summary_file.read_text(encoding='utf-8')
            self.assertIn("BENCHMARK EVALUATION SUMMARY", sum_text)
            self.assertIn("Accuracy", sum_text)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)



    # =========================================================================
    # TASK 1 REGRESSION TESTS: PROCESSING-ERROR CLASSIFICATION & QUARANTINING
    # =========================================================================

    def test_regression_genuine_document_processing_failure(self):
        """
        Verifies that when a genuine document raises a processing exception:
        - status is marked as PROCESSING_ERROR
        - doc_verdict is marked as PROCESSING_ERROR
        - classification is None (strictly excluded from TN and FP)
        - error message is captured
        - it is never counted as an anomaly detection or clean verdict
        """
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dummy_file = tmp_path / "genuine_corrupt.pdf"
            dummy_file.write_bytes(b"%PDF-1.4 dummy corrupted data")

            rec = {
                'filename': 'genuine_corrupt.pdf',
                'is_tampered': '0',
                'expected_rules': 'None'
            }

            with patch('tools.evaluate.extract_document_content', side_effect=RuntimeError("OCR engine out of memory")):
                res = evaluate_document_record(rec, dataset_dir=tmp_path)

            self.assertEqual(res['status'], 'PROCESSING_ERROR')
            self.assertEqual(res['doc_verdict'], 'PROCESSING_ERROR')
            self.assertEqual(res['rule_match_verdict'], 'ERROR')
            self.assertIsNone(res['classification'], "Processing error must not be classified as TN or FP")
            self.assertFalse(res['detected_anomaly'])
            self.assertIn("OCR engine out of memory", res['processing_error'])

    def test_regression_tampered_document_processing_failure(self):
        """
        Verifies that when a tampered document raises a processing exception:
        - status is marked as PROCESSING_ERROR
        - doc_verdict is marked as PROCESSING_ERROR
        - classification is None (strictly excluded from TP and FN)
        - error message is captured
        - it is never counted as a missed detection (FN) or a hit (TP)
        """
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dummy_file = tmp_path / "tampered_corrupt.pdf"
            dummy_file.write_bytes(b"%PDF-1.4 invalid xref")

            rec = {
                'filename': 'tampered_corrupt.pdf',
                'is_tampered': '1',
                'expected_rules': 'PDF-003'
            }

            with patch('tools.evaluate.extract_document_content', side_effect=ValueError("Corrupted cross-reference table")):
                res = evaluate_document_record(rec, dataset_dir=tmp_path)

            self.assertEqual(res['status'], 'PROCESSING_ERROR')
            self.assertEqual(res['doc_verdict'], 'PROCESSING_ERROR')
            self.assertEqual(res['rule_match_verdict'], 'ERROR')
            self.assertIsNone(res['classification'], "Processing error must not be classified as TP or FN")
            self.assertFalse(res['detected_anomaly'])
            self.assertIn("Corrupted cross-reference table", res['processing_error'])

    def test_regression_missing_benchmark_file(self):
        """
        Verifies that when a benchmark file is missing from disk:
        - status is marked as PROCESSING_ERROR
        - doc_verdict is marked as PROCESSING_ERROR
        - classification is None (excluded from TP, TN, FP, FN)
        - error indicates missing file on disk
        """
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            rec = {
                'filename': 'missing_benchmark_file.pdf',
                'is_tampered': '1',
                'expected_rules': 'RULE-CTX-001'
            }

            res = evaluate_document_record(rec, dataset_dir=tmp_path)

            self.assertEqual(res['status'], 'PROCESSING_ERROR')
            self.assertEqual(res['doc_verdict'], 'PROCESSING_ERROR')
            self.assertIsNone(res['classification'], "Missing file must be excluded from confusion matrix")
            self.assertIn("Missing benchmark file on disk", res['processing_error'])

    def test_regression_successful_genuine_document(self):
        """
        Verifies that a genuine document without anomalies is correctly classified as TN (CLEAN).
        """
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dummy_file = tmp_path / "clean_genuine.pdf"
            dummy_file.write_bytes(b"%PDF-1.4 genuine content")

            rec = {
                'filename': 'clean_genuine.pdf',
                'is_tampered': '0',
                'expected_rules': 'None'
            }

            with patch('tools.evaluate.extract_document_content', return_value={'full_text': 'Valid invoice', 'extraction_status': 'SUCCESS'}), \
                 patch('tools.evaluate.analyze_visual_structure', return_value=[]), \
                 patch('tools.evaluate.analyze_contextual_rules', return_value=[]), \
                 patch('tools.evaluate.run_extended_pdf_forensics', return_value=[]), \
                 patch('tools.evaluate.run_image_forensics', return_value=[]):
                res = evaluate_document_record(rec, dataset_dir=tmp_path)

            self.assertEqual(res['status'], 'EVALUATED')
            self.assertEqual(res['classification'], 'TN')
            self.assertEqual(res['doc_verdict'], 'TN (CLEAN)')
            self.assertIsNone(res['processing_error'])
            self.assertFalse(res['detected_anomaly'])

    def test_regression_successful_tampered_document(self):
        """
        Verifies that a tampered document with anomalies is correctly classified as TP (HIT).
        """
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dummy_file = tmp_path / "tampered_invoice.pdf"
            dummy_file.write_bytes(b"%PDF-1.4 tampered content")

            rec = {
                'filename': 'tampered_invoice.pdf',
                'is_tampered': '1',
                'expected_rules': 'RULE-CTX-003'
            }

            mock_finding = [{'rule_id': 'RULE-CTX-003', 'description': 'Total mismatch'}]
            with patch('tools.evaluate.extract_document_content', return_value={'full_text': 'Tampered text', 'extraction_status': 'SUCCESS'}), \
                 patch('tools.evaluate.analyze_visual_structure', return_value=[]), \
                 patch('tools.evaluate.analyze_contextual_rules', return_value=mock_finding), \
                 patch('tools.evaluate.run_extended_pdf_forensics', return_value=[]), \
                 patch('tools.evaluate.run_image_forensics', return_value=[]):
                res = evaluate_document_record(rec, dataset_dir=tmp_path)

            self.assertEqual(res['status'], 'EVALUATED')
            self.assertEqual(res['classification'], 'TP')
            self.assertEqual(res['doc_verdict'], 'TP (HIT)')
            self.assertIsNone(res['processing_error'])
            self.assertTrue(res['detected_anomaly'])
            self.assertIn('RULE-CTX-003', res['fired_rules'])

    def test_regression_confusion_matrix_exclusion_and_totals(self):
        """
        Verifies that:
        1. TP + TN + FP + FN = successfully evaluated documents
        2. Processing failures do NOT affect confusion-matrix totals
        3. Accuracy calculation only divides by successfully evaluated documents
        """
        # 10 successfully evaluated documents: TP=4, TN=4, FP=1, FN=1
        # 5 processing errors: quarantined
        tp, tn, fp, fn = 4, 4, 1, 1
        processing_errors = 5

        metrics = compute_binary_metrics(tp, tn, fp, fn, processing_errors=processing_errors)

        # Assertion: Total evaluated must strictly equal TP + TN + FP + FN
        successfully_evaluated = tp + tn + fp + fn
        self.assertEqual(metrics['total_evaluated'], successfully_evaluated)
        self.assertEqual(metrics['total_evaluated'], 10)

        # Confusion matrix cell sum must equal total_evaluated
        cm_sum = sum(metrics['confusion_matrix'][0]) + sum(metrics['confusion_matrix'][1])
        self.assertEqual(cm_sum, successfully_evaluated)
        self.assertEqual(cm_sum, 10)

        # Processing errors are tracked orthogonally
        self.assertEqual(metrics['processing_errors'], 5)

        # Accuracy = (4 + 4) / 10 = 80.0% (unaffected by the 5 processing errors)
        self.assertEqual(metrics['accuracy_pct'], 80.0)

    def test_regression_processing_error_preservation_in_json_and_csv(self):
        """
        Verifies that processing-error records are preserved with full diagnostic detail in both JSON and CSV.
        """
        import tempfile
        import shutil

        temp_dir = Path(tempfile.mkdtemp(prefix="vexora_eval_quarantine_test_"))
        try:
            mock_single_doc = {
                'doc_metrics': compute_binary_metrics(tp=1, tn=1, fp=0, fn=0, processing_errors=1),
                'total_expected_rule_docs': 1,
                'exact_rule_hits': 1,
                'exact_rule_pct': 100.0,
                'rule_counts': {'PDF-003': 1},
                'doc_results': [
                    {
                        'filename': 'valid_tampered.pdf',
                        'is_tampered': 1,
                        'status': 'EVALUATED',
                        'detected_anomaly': True,
                        'expected_rules': ['PDF-003'],
                        'fired_rules': ['PDF-003'],
                        'matched_rules': ['PDF-003'],
                        'doc_verdict': 'TP (HIT)',
                        'rule_match_verdict': 'HIT (PDF-003)',
                        'processing_error': None
                    },
                    {
                        'filename': 'corrupted_sample.pdf',
                        'is_tampered': 0,
                        'status': 'PROCESSING_ERROR',
                        'detected_anomaly': False,
                        'expected_rules': [],
                        'fired_rules': [],
                        'matched_rules': [],
                        'doc_verdict': 'PROCESSING_ERROR',
                        'rule_match_verdict': 'ERROR',
                        'processing_error': 'Simulated extraction decoder fault'
                    }
                ]
            }
            mock_case_data = {
                'case_metrics': compute_binary_metrics(tp=1, tn=0, fp=0, fn=0),
                'case_results': []
            }

            export_benchmark_reports(mock_single_doc, mock_case_data, output_dir=temp_dir)

            json_file = temp_dir / 'benchmark_results.json'
            csv_file = temp_dir / 'benchmark_results.csv'

            # 1. Verify JSON preservation
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                doc_evals = data['document_evaluations']
                self.assertEqual(len(doc_evals), 2)
                err_doc = next(d for d in doc_evals if d['filename'] == 'corrupted_sample.pdf')
                self.assertEqual(err_doc['status'], 'PROCESSING_ERROR')
                self.assertEqual(err_doc['doc_verdict'], 'PROCESSING_ERROR')
                self.assertEqual(err_doc['processing_error'], 'Simulated extraction decoder fault')
                self.assertEqual(data['error_isolation']['processing_errors_count'], 1)

            # 2. Verify CSV preservation
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.assertEqual(len(rows), 2)
                err_row = next(r for r in rows if r['filename'] == 'corrupted_sample.pdf')
                self.assertEqual(err_row['status'], 'PROCESSING_ERROR')
                self.assertEqual(err_row['doc_verdict'], 'PROCESSING_ERROR')
                self.assertEqual(err_row['processing_error'], 'Simulated extraction decoder fault')
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()

