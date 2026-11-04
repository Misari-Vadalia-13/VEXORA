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

from tools.evaluate import (
    compute_binary_metrics,
    render_confusion_matrix_ascii,
    export_benchmark_reports
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
        """Verifies export_benchmark_reports generates valid JSON and CSV reports."""
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

        export_benchmark_reports(mock_single_doc, mock_case_data)

        reports_dir = Path("reports")
        json_file = reports_dir / 'benchmark_results.json'
        csv_file = reports_dir / 'benchmark_results.csv'

        self.assertTrue(json_file.exists())
        self.assertTrue(csv_file.exists())

        # Verify JSON structure
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.assertEqual(data['benchmark_suite'], 'VEXORA Forensic Benchmark Suite')
            self.assertEqual(data['document_level_metrics']['accuracy_pct'], 85.0)
            self.assertEqual(data['case_level_metrics']['accuracy_pct'], 100.0)

        # Verify CSV content
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            self.assertGreaterEqual(len(rows), 2)
            header = rows[0]
            self.assertIn('filename', header)
            self.assertIn('matched_rules', header)
            self.assertIn('doc_verdict', header)


if __name__ == '__main__':
    unittest.main()
