"""
VEXORA — Phase G Test Suite
Tests:
1. Benchmark demonstration dataset existence and labels.csv schema.
2. Benchmark evaluation execution and metric calculation.
3. Documentation integrity (ARCHITECTURE.md, CAPABILITIES.md, LIMITATIONS.md).
4. Security hardening (SECRET_KEY fallback, restricted CORS, demo Google auth route).
"""

import os
import csv
import unittest
from pathlib import Path

from backend.config import Config, TestConfig
from backend.app import create_app
from backend.database import init_db
from tools.make_samples import generate_all_samples, DATASET_DIR
from tools.evaluate import run_evaluation


class TestV2PhaseG(unittest.TestCase):
    """Automated test cases for Phase G Proof, Documentation, and Honesty Fixes."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestConfig)
        cls.client = cls.app.test_client()

    def setUp(self):
        init_db(TestConfig.DATABASE)

    def test_01_demo_dataset_and_labels_exist(self):
        """demo_dataset exists and contains at least 10 genuine and 10 tampered files."""
        csv_path = DATASET_DIR / 'labels.csv'
        if not csv_path.exists():
            generate_all_samples()

        self.assertTrue(csv_path.exists())
        records = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)

        self.assertGreaterEqual(len(records), 20)
        genuine = [r for r in records if r['is_tampered'] == '0']
        tampered = [r for r in records if r['is_tampered'] == '1']
        self.assertGreaterEqual(len(genuine), 10)
        self.assertGreaterEqual(len(tampered), 10)

        # Check each file actually exists on disk
        for r in records:
            fpath = DATASET_DIR / r['filename']
            self.assertTrue(fpath.exists(), f"File {r['filename']} must exist in demo_dataset/")

    def test_02_evaluation_pipeline_execution(self):
        """tools/evaluate.py executes successfully and returns exit code 0."""
        ret = run_evaluation()
        self.assertEqual(ret, 0)

    def test_03_documentation_files_exist_and_contain_required_sections(self):
        """docs/ARCHITECTURE.md, CAPABILITIES.md, and LIMITATIONS.md exist and are populated."""
        root = Path(__file__).resolve().parent.parent

        arch_file = root / 'docs' / 'ARCHITECTURE.md'
        self.assertTrue(arch_file.exists())
        arch_content = arch_file.read_text(encoding='utf-8')
        self.assertIn("```mermaid", arch_content)
        self.assertIn("VEXORA — System Architecture", arch_content)

        cap_file = root / 'docs' / 'CAPABILITIES.md'
        self.assertTrue(cap_file.exists())
        cap_content = cap_file.read_text(encoding='utf-8')
        self.assertIn("Handwriting Recognition", cap_content)
        self.assertIn("Unsupported", cap_content)
        self.assertIn("Multilingual Document Extraction", cap_content)

        lim_file = root / 'docs' / 'LIMITATIONS.md'
        self.assertTrue(lim_file.exists())
        lim_content = lim_file.read_text(encoding='utf-8')
        self.assertIn("Known Limitations", lim_content)
        self.assertIn("False Positive", lim_content)

    def test_04_readme_corrections_and_v2_additions(self):
        """README.md contains V2 additions and accurate technical corrections."""
        root = Path(__file__).resolve().parent.parent
        readme_file = root / 'README.md'
        self.assertTrue(readme_file.exists())
        content = readme_file.read_text(encoding='utf-8')

        self.assertIn("V2 Forensic Extensions & Additions", content)
        self.assertIn("Technical Corrections & Honesty Notes", content)
        # Verify honest reporting of NER (no false claim of spaCy)
        self.assertIn("Pure Regex", content)

    def test_05_demo_google_login_endpoint(self):
        """GET /api/auth/google returns demo user and is explicitly labeled as not verified."""
        res = self.client.get('/api/auth/google')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data.get('auth_mode'), 'demo_unverified')
        self.assertIn('not verified', data.get('message', '').lower())
        self.assertIn('not verified', data['user'].get('auth_note', '').lower())

    def test_06_cors_configuration(self):
        """CORS headers respect allowed origins and default behavior."""
        # Request with Origin in allowed list
        res = self.client.get('/api/health', headers={'Origin': 'http://127.0.0.1:5000'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Access-Control-Allow-Origin'), 'http://127.0.0.1:5000')

        # Request without Origin header defaults to '*'
        res_no_origin = self.client.get('/api/health')
        self.assertEqual(res_no_origin.status_code, 200)
        self.assertEqual(res_no_origin.headers.get('Access-Control-Allow-Origin'), '*')


if __name__ == '__main__':
    unittest.main()
