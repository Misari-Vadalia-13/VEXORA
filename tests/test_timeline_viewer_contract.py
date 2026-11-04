"""
Automated unit tests for Investigation Timeline Synthesis, Dynamic Forensic Viewer,
and Visual Evidence Artifact serving.
"""
import unittest
import os
import io
import json
import shutil
import tempfile
from pathlib import Path
from PIL import Image

from backend.config import Config
from backend.database import init_db
from backend.models import create_case, create_document, create_finding, save_document_extraction
from backend.evidence import get_finding_evidence_image, get_document_page_overlay
from backend.correlator import build_case_timeline
from backend.app import create_app


class TestTimelineAndDynamicViewer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="vexora_test_timeline_")
        self.db_path = os.path.join(self.temp_dir, "test_vexora.db")
        self.upload_dir = os.path.join(self.temp_dir, "uploads")
        self.evidence_dir = os.path.join(self.upload_dir, "evidence")
        os.makedirs(self.evidence_dir, exist_ok=True)

        self.orig_db = Config.DATABASE
        Config.DATABASE = self.db_path
        os.environ['VEXORA_DB_PATH'] = self.db_path
        os.environ['VEXORA_REQUIRE_AUTH'] = 'false'
        os.environ['VEXORA_ALLOW_DEMO_RESET'] = 'true'

        init_db(self.db_path)

        self.app = create_app({
            'TESTING': True,
            'DATABASE': self.db_path,
            'UPLOAD_FOLDER': self.upload_dir,
            'SECRET_KEY': 'test-secret-key-timeline',
            'WTF_CSRF_ENABLED': False
        })
        self.client = self.app.test_client()

    def tearDown(self):
        Config.DATABASE = self.orig_db
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_case_timeline_synthesis_and_anomalies(self):
        """Tests that chronological events are synthesized and temporal conflicts flagged."""
        case = create_case({
            'title': 'Timeline Test Case',
            'type': 'Financial Fraud',
            'priority': 'High',
            'status': 'Active',
            'investigator': 'Lead Investigator',
            'description': 'Testing chronological anomalies'
        }, user='Tester')
        case_id = case['id']

        # Document 1: PO dated 2026-03-01
        po_path = os.path.join(self.upload_dir, "PO_001.pdf")
        with open(po_path, 'wb') as f:
            f.write(b"%PDF-1.4 PO mock")

        doc_po = create_document({
            'case_id': case_id,
            'filename': 'PO_001.pdf',
            'file_type': 'pdf',
            'file_size': 1024,
            'file_path': po_path,
            'category': 'Purchase Order'
        })
        save_document_extraction(doc_po['id'], {
            'full_text': 'Purchase Order PO-9988 Date: 2026-03-01 Total: USD 15,000 to CyberTech Ltd',
            'entities': {
                'dates': [{'value': '2026-03-01'}],
                'monetary_values': [{'value': '15000'}]
            }
        })

        # Document 2: Invoice dated 2026-02-15 (Pre-dated invoice before PO!)
        inv_path = os.path.join(self.upload_dir, "INV_001.pdf")
        with open(inv_path, 'wb') as f:
            f.write(b"%PDF-1.4 Invoice mock")

        doc_inv = create_document({
            'case_id': case_id,
            'filename': 'INV_001.pdf',
            'file_type': 'pdf',
            'file_size': 1024,
            'file_path': inv_path,
            'category': 'Invoice'
        })
        save_document_extraction(doc_inv['id'], {
            'full_text': 'Tax Invoice INV-2026-77 Date: 2026-02-15 Amount Due: USD 15,000 from CyberTech Ltd',
            'entities': {
                'dates': [{'value': '2026-02-15'}],
                'monetary_values': [{'value': '15000'}]
            }
        })

        # Synthesize timeline
        with self.app.app_context():
            timeline = build_case_timeline(case_id)
            self.assertTrue(timeline['success'])
            self.assertGreaterEqual(timeline['event_count'], 2)

            # Verify events are in chronological order (2026-02-15 before 2026-03-01)
            dates = [e['date'] for e in timeline['events']]
            self.assertEqual(dates, sorted(dates))

            # Verify that pre-dated invoice anomaly was detected
            self.assertGreaterEqual(timeline['anomaly_count'], 1)
            anomaly_types = [a['type'] for a in timeline['anomalies']]
            self.assertIn('pre_dated_invoice', anomaly_types)

            # Test API endpoint
            res = self.client.get(f'/api/cases/{case_id}/timeline')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data['success'])
            self.assertEqual(data['case_id'], case_id)
            self.assertGreaterEqual(data['anomaly_count'], 1)

    def test_visual_evidence_artifact_retrieval(self):
        """Tests that get_finding_evidence_image returns visual evidence artifacts when present."""
        case = create_case({
            'title': 'Artifact Test Case',
            'type': 'Asset Verification',
            'priority': 'Medium',
            'status': 'Active',
            'investigator': 'Lead Investigator',
            'description': 'Testing ELA heatmap serving'
        }, user='Tester')
        case_id = case['id']

        # Create a sample image file
        img_path = os.path.join(self.upload_dir, "sample.png")
        img = Image.new("RGB", (200, 200), color=(100, 150, 200))
        img.save(img_path)
        img.close()

        doc = create_document({
            'case_id': case_id,
            'filename': 'sample.png',
            'file_type': 'png',
            'file_size': os.path.getsize(img_path),
            'file_path': img_path
        })

        # Create a synthetic ELA difference artifact
        artifact_filename = "ela_diff_sample.png"
        artifact_path = os.path.join(self.evidence_dir, artifact_filename)
        art_img = Image.new("RGB", (200, 200), color=(255, 0, 0))
        art_img.save(artifact_path)
        art_img.close()

        # Create finding with evidence pointing to saved artifact
        finding = create_finding({
            'case_id': case_id,
            'document_id': doc['id'],
            'title': 'Error Level Analysis Inconsistency',
            'severity': 'Medium',
            'category': 'Visual Artifact',
            'rule_id': 'IMG-001',
            'evidence': f'High ELA difference detected: 14.5% (heatmap saved: {artifact_filename})',
            'evidence_class': 'Observation',
            'page_number': 1
        })

        with self.app.app_context():
            # Retrieve evidence image bytes via helper
            png_bytes, err = get_finding_evidence_image(finding['id'])
            self.assertIsNone(err)
            self.assertIsNotNone(png_bytes)
            self.assertGreater(len(png_bytes), 100)

            # Test through API route
            res = self.client.get(f'/api/findings/{finding["id"]}/evidence-image')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.mimetype, 'image/png')
            self.assertEqual(res.data, png_bytes)

            # Test streaming evidence endpoint
            res_stream = self.client.get(f'/api/evidence/{artifact_filename}')
            self.assertEqual(res_stream.status_code, 200)
            self.assertEqual(res_stream.mimetype, 'image/png')

    def test_frontend_inspector_and_timeline_elements(self):
        """Verifies that index.html contains the dynamic viewer and timeline elements."""
        index_path = Path("frontend/index.html")
        content = index_path.read_text(encoding="utf-8")

        # Dynamic viewer elements
        self.assertIn('id="forensicDocTitleHeader"', content)
        self.assertIn('id="forensicExtractionModeBadge"', content)
        self.assertIn('id="forensicFindingsCountBadge"', content)
        self.assertIn('id="forensicViewerCanvasWrap"', content)
        self.assertIn('id="forensicPageOverlayImg"', content)
        self.assertIn('id="forensicTextTranscriptWrap"', content)

        # Timeline elements
        self.assertIn('id="timelineStatsBadge"', content)
        self.assertIn('id="timelineAnomalyBanner"', content)
        self.assertIn('id="caseTimelineFeed"', content)
        self.assertIn('v2LoadCaseTimeline', content)


if __name__ == '__main__':
    unittest.main()
