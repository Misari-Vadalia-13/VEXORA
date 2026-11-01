"""
VEXORA — Automated Backend & Database Test Suite
Tests SQLite database operations, REST API routes, input validation,
audit logging, and user authentication using an isolated in-memory database.
"""

import unittest
import json
import os
from pathlib import Path
from backend.app import create_app
from backend.config import TestConfig
from backend.database import get_db, init_db, seed_data, query_db

class VexoraBackendTestCase(unittest.TestCase):
    """Test suite covering core backend and database operations."""

    def setUp(self):
        """Prepares a fresh isolated Flask client and clean test SQLite database."""
        test_db = Path(TestConfig.DATABASE)
        if test_db.exists():
            try:
                test_db.unlink()
            except Exception:
                pass

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        """Cleans up the test database file after each test execution."""
        test_db = Path(TestConfig.DATABASE)
        if test_db.exists():
            try:
                test_db.unlink()
            except Exception:
                pass

    def test_health_check(self):
        """Verifies the /api/health endpoint returns 200 OK and healthy status."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertTrue(data['database']['connected'])

    def test_system_stats(self):
        """Verifies dashboard telemetry metrics aggregation from SQLite."""
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        stats = data['data']
        self.assertIn('total_cases', stats)
        self.assertIn('active_cases', stats)
        self.assertIn('total_documents', stats)
        self.assertIn('high_risk_rate_percent', stats)
        self.assertGreaterEqual(stats['total_cases'], 1)

    def test_list_cases(self):
        """Verifies listing cases with optional filters."""
        # Unfiltered list
        response = self.client.get('/api/cases')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['count'], 1)

        # Filter by priority
        crit_res = self.client.get('/api/cases?priority=Critical')
        self.assertEqual(crit_res.status_code, 200)
        crit_data = crit_res.get_json()
        for c in crit_data['data']:
            self.assertEqual(c['priority'], 'Critical')

    def test_create_and_retrieve_case(self):
        """Verifies creating an investigation case and retrieving it with associated details."""
        new_case_payload = {
            'title': 'Test Forensic Investigation Alpha',
            'type': 'Financial Fraud',
            'priority': 'Critical',
            'status': 'Active',
            'investigator': 'Dr. Alex Turner',
            'description': 'Automated test investigation for verifying persistence.'
        }
        create_res = self.client.post(
            '/api/cases',
            data=json.dumps(new_case_payload),
            content_type='application/json'
        )
        self.assertEqual(create_res.status_code, 201)
        created_data = create_res.get_json()
        self.assertTrue(created_data['success'])
        case_id = created_data['data']['id']
        self.assertTrue(case_id.startswith('CAS-'))

        # Retrieve specific case
        get_res = self.client.get(f'/api/cases/{case_id}')
        self.assertEqual(get_res.status_code, 200)
        retrieved_data = get_res.get_json()
        self.assertEqual(retrieved_data['data']['title'], new_case_payload['title'])
        self.assertEqual(retrieved_data['data']['priority'], 'Critical')

    def test_case_input_validation(self):
        """Verifies strict input validation rejecting empty or invalid payloads."""
        # Empty title
        bad_title_payload = {
            'title': '   ',
            'type': 'Financial Fraud',
            'priority': 'High',
            'status': 'Active'
        }
        res1 = self.client.post('/api/cases', data=json.dumps(bad_title_payload), content_type='application/json')
        self.assertEqual(res1.status_code, 400)
        self.assertIn('title', res1.get_json()['error'].lower())

        # Invalid priority
        bad_priority_payload = {
            'title': 'Valid Case Title Here',
            'type': 'Financial Fraud',
            'priority': 'SuperUrgent',  # Invalid enum
            'status': 'Active'
        }
        res2 = self.client.post('/api/cases', data=json.dumps(bad_priority_payload), content_type='application/json')
        self.assertEqual(res2.status_code, 400)
        self.assertIn('priority', res2.get_json()['error'].lower())

    def test_update_and_delete_case(self):
        """Verifies updating case status and subsequent deletion."""
        # Create case first
        create_res = self.client.post(
            '/api/cases',
            data=json.dumps({
                'title': 'Case To Be Updated',
                'type': 'Contract Tampering',
                'priority': 'Medium',
                'status': 'Active',
                'investigator': 'Elena Rostova'
            }),
            content_type='application/json'
        )
        case_id = create_res.get_json()['data']['id']

        # Update case
        update_res = self.client.put(
            f'/api/cases/{case_id}',
            data=json.dumps({'status': 'Solved', 'priority': 'Low'}),
            content_type='application/json'
        )
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.get_json()['data']['status'], 'Solved')

        # Delete case
        del_res = self.client.delete(f'/api/cases/{case_id}')
        self.assertEqual(del_res.status_code, 200)

        # Confirm 404 on get
        not_found_res = self.client.get(f'/api/cases/{case_id}')
        self.assertEqual(not_found_res.status_code, 404)

    def test_document_registration(self):
        """Verifies registering a document record and associating it with a case."""
        doc_payload = {
            'case_id': 'CAS-2026-0891',
            'filename': 'Test_Evidence_Invoice.pdf',
            'file_type': 'pdf',
            'file_size': 1048576,
            'category': 'Invoice',
            'classification_confidence': 96.5,
            'status': 'Pending'
        }
        res = self.client.post('/api/documents', data=json.dumps(doc_payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data['success'])
        doc_id = data['data']['id']

        # Retrieve document
        get_res = self.client.get(f'/api/documents/{doc_id}')
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.get_json()['data']['filename'], 'Test_Evidence_Invoice.pdf')

    def test_findings_creation_and_listing(self):
        """Verifies creating and querying forensic findings."""
        finding_payload = {
            'case_id': 'CAS-2026-0891',
            'title': 'Test Compression Artifact Inconsistency',
            'severity': 'High',
            'category': 'Compression Anomaly',
            'description': 'Discrepant quantization tables discovered in JPEG stream.',
            'confidence': 91.2
        }
        res = self.client.post('/api/findings', data=json.dumps(finding_payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.get_json()['success'])

        # List findings
        list_res = self.client.get('/api/findings?case_id=CAS-2026-0891')
        self.assertEqual(list_res.status_code, 200)
        self.assertGreaterEqual(list_res.get_json()['count'], 1)

    def test_audit_logs_retrieval(self):
        """Verifies that system events generate immutable audit records."""
        res = self.client.get('/api/audit-logs')
        self.assertEqual(res.status_code, 200)
        logs = res.get_json()['data']
        self.assertIsInstance(logs, list)
        self.assertGreaterEqual(len(logs), 1)

    def test_user_auth_flow(self):
        """Verifies user registration, password hashing, and login authentication."""
        # Register new analyst
        reg_payload = {
            'username': 'agent.smith',
            'email': 'smith@vexora.internal',
            'password': 'SecurePassword@123',
            'role': 'Digital Forensics Analyst',
            'badge_number': 'VEX-999'
        }
        reg_res = self.client.post('/api/auth/register', data=json.dumps(reg_payload), content_type='application/json')
        self.assertEqual(reg_res.status_code, 201)

        # Duplicate registration should return 409 Conflict
        dup_res = self.client.post('/api/auth/register', data=json.dumps(reg_payload), content_type='application/json')
        self.assertEqual(dup_res.status_code, 409)

        # Successful login
        login_payload = {
            'username': 'agent.smith',
            'password': 'SecurePassword@123'
        }
        login_res = self.client.post('/api/auth/login', data=json.dumps(login_payload), content_type='application/json')
        self.assertEqual(login_res.status_code, 200)
        self.assertTrue(login_res.get_json()['success'])

        # Failed login with bad password
        bad_login_payload = {
            'username': 'agent.smith',
            'password': 'WrongPassword123'
        }
        bad_login_res = self.client.post('/api/auth/login', data=json.dumps(bad_login_payload), content_type='application/json')
        self.assertEqual(bad_login_res.status_code, 401)

    def test_upload_single_pdf(self):
        """Verifies single PDF upload, SHA-256 hash generation, classification, and disk storage."""
        import io
        dummy_pdf_content = b"%PDF-1.4 mock content invoice test subtotal VAT payment details %%EOF"
        data = {
            'case_id': 'CAS-2026-0891',
            'file': (io.BytesIO(dummy_pdf_content), 'Apex_Vendor_Invoice_INV99.pdf')
        }
        res = self.client.post('/api/documents/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        res_data = res.get_json()
        self.assertTrue(res_data['success'])
        self.assertEqual(res_data['count'], 1)
        doc = res_data['data'][0]
        self.assertTrue(doc['id'].startswith('DOC-'))
        self.assertEqual(doc['filename'], 'Apex_Vendor_Invoice_INV99.pdf')
        self.assertEqual(doc['category'], 'Invoice')
        self.assertGreaterEqual(doc['classification_confidence'], 90.0)
        self.assertTrue(len(doc['file_hash']) == 64)  # SHA-256 hex length

    def test_upload_multiple_files(self):
        """Verifies batch upload of multiple documents in a single HTTP request."""
        import io
        doc1 = (io.BytesIO(b"%PDF-1.4 contract agreement terms %%EOF"), 'Partnership_Agreement.pdf')
        doc2 = (io.BytesIO(b"\x89PNG\r\n\x1a\n mock customs declaration image data"), 'Customs_Manifest_Port.png')
        data = {
            'case_id': 'CAS-2026-0888',
            'files': [doc1, doc2]
        }
        res = self.client.post('/api/documents/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        res_data = res.get_json()
        self.assertTrue(res_data['success'])
        self.assertEqual(res_data['count'], 2)
        categories = [d['category'] for d in res_data['data']]
        self.assertIn('Contract', categories)
        self.assertIn('Customs Declaration', categories)

    def test_upload_unsupported_file_type(self):
        """Verifies rejection of unsupported file extensions with HTTP 400."""
        import io
        data = {
            'file': (io.BytesIO(b"MZ executable binary payload"), 'malicious_tool.exe')
        }
        res = self.client.post('/api/documents/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        res_data = res.get_json()
        self.assertFalse(res_data['success'])
        self.assertIn('unsupported', res_data['error'].lower())

    def test_upload_empty_file(self):
        """Verifies rejection of empty (0-byte) files."""
        import io
        data = {
            'file': (io.BytesIO(b""), 'empty_invoice.pdf')
        }
        res = self.client.post('/api/documents/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        self.assertIn('empty', res.get_json()['error'].lower())

    def test_duplicate_filename_handling(self):
        """Verifies that uploading duplicate filenames preserves both with unique IDs and disk paths."""
        import io
        pdf_bytes = b"%PDF-1.4 mock content %%EOF"
        data1 = {'file': (io.BytesIO(pdf_bytes), 'Standard_Invoice.pdf')}
        res1 = self.client.post('/api/documents/upload', data=data1, content_type='multipart/form-data')
        self.assertEqual(res1.status_code, 201)
        doc1 = res1.get_json()['data'][0]

        data2 = {'file': (io.BytesIO(pdf_bytes), 'Standard_Invoice.pdf')}
        res2 = self.client.post('/api/documents/upload', data=data2, content_type='multipart/form-data')
        self.assertEqual(res2.status_code, 201)
        doc2 = res2.get_json()['data'][0]

        self.assertNotEqual(doc1['id'], doc2['id'])
        self.assertNotEqual(doc1['file_path'], doc2['file_path'])

    def test_download_and_delete_document(self):
        """Verifies streaming document download and subsequent deletion."""
        import io
        pdf_content = b"%PDF-1.4 Download stream verification sample %%EOF"
        data = {'file': (io.BytesIO(pdf_content), 'Download_Test_Document.pdf')}
        res = self.client.post('/api/documents/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        doc_id = res.get_json()['data'][0]['id']

        # Download document
        dl_res = self.client.get(f'/api/documents/{doc_id}/download')
        self.assertEqual(dl_res.status_code, 200)
        self.assertEqual(dl_res.data, pdf_content)
        dl_res.close()  # Close stream to release Windows file handle

        # Delete document
        del_res = self.client.delete(f'/api/documents/{doc_id}')
        self.assertEqual(del_res.status_code, 200)

        # Confirm 404
        dl_404 = self.client.get(f'/api/documents/{doc_id}/download')
        self.assertEqual(dl_404.status_code, 404)

    def test_extract_digital_pdf(self):
        """Verifies text, layout bounding box, and entity extraction from a digital PDF."""
        import io
        import pymupdf

        # Create genuine digital PDF with text
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text(
            (50, 70),
            "Vendor Invoice INV-2026-8812\n"
            "Date: 2026-10-18\n"
            "Contractor: Apex Global Inc.\n"
            "Auditor: Dr. Alex Turner\n"
            "Total Due: $4,850,000.00\n"
            "Contact: forensic.audit@apex.internal\n"
        )
        pdf_bytes = doc.tobytes()
        doc.close()

        # 1. Upload PDF
        upload_data = {'file': (io.BytesIO(pdf_bytes), 'Apex_Digital_Invoice.pdf')}
        up_res = self.client.post('/api/documents/upload', data=upload_data, content_type='multipart/form-data')
        self.assertEqual(up_res.status_code, 201)
        doc_id = up_res.get_json()['data'][0]['id']

        # 2. Trigger Extraction
        extract_res = self.client.post(f'/api/documents/{doc_id}/extract')
        self.assertEqual(extract_res.status_code, 200)
        ext_json = extract_res.get_json()
        self.assertTrue(ext_json['success'])
        data = ext_json['data']
        self.assertEqual(data['format'], 'PDF')
        self.assertEqual(data['page_count'], 1)
        self.assertGreater(data['total_words'], 5)

        # 3. Verify Extracted Entities
        entities = data['entities']
        date_vals = [d['value'] for d in entities['dates']]
        self.assertIn('2026-10-18', date_vals)

        id_vals = [i['value'] for i in entities['identifiers']]
        self.assertTrue(any('INV-2026-8812' in v for v in id_vals))

        money_vals = [m['value'] for m in entities['monetary_values']]
        self.assertTrue(any('$4,850,000.00' in v or '4,850,000.00' in v for v in money_vals))

        org_vals = [o['value'] for o in entities['organizations']]
        self.assertTrue(any('Apex Global Inc' in v for v in org_vals))

        # 4. Verify Retrieval from Database
        get_res = self.client.get(f'/api/documents/{doc_id}/extracted')
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.get_json()['data']['page_count'], 1)

    def test_extract_multi_page_pdf(self):
        """Verifies multi-page PDF extraction and page traceability."""
        import io
        import pymupdf

        doc = pymupdf.open()
        p1 = doc.new_page()
        p1.insert_text((50, 50), "Page One: Agreement initiated on 2026-05-12.")
        p2 = doc.new_page()
        p2.insert_text((50, 50), "Page Two: Settlement amount of $250,000.00 agreed.")
        pdf_bytes = doc.tobytes()
        doc.close()

        upload_data = {'file': (io.BytesIO(pdf_bytes), 'Multi_Page_Contract.pdf')}
        up_res = self.client.post('/api/documents/upload', data=upload_data, content_type='multipart/form-data')
        doc_id = up_res.get_json()['data'][0]['id']

        extract_res = self.client.post(f'/api/documents/{doc_id}/extract')
        self.assertEqual(extract_res.status_code, 200)
        data = extract_res.get_json()['data']
        self.assertEqual(data['page_count'], 2)
        self.assertEqual(len(data['pages']), 2)
        self.assertEqual(data['pages'][0]['page_number'], 1)
        self.assertEqual(data['pages'][1]['page_number'], 2)

    def test_extract_image_document(self):
        """Verifies image metadata, dimension extraction, and OCR resilience."""
        import io
        from PIL import Image

        img = Image.new('RGB', (300, 150), color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        upload_data = {'file': (buf, 'Sample_Scan.png')}
        up_res = self.client.post('/api/documents/upload', data=upload_data, content_type='multipart/form-data')
        doc_id = up_res.get_json()['data'][0]['id']

        extract_res = self.client.post(f'/api/documents/{doc_id}/extract')
        self.assertEqual(extract_res.status_code, 200)
        data = extract_res.get_json()['data']
        self.assertEqual(data['format'], 'PNG')
        self.assertEqual(data['page_count'], 1)
        self.assertEqual(data['metadata']['dimensions'], '300x150')

    def test_extract_corrupted_document(self):
        """Verifies graceful error handling (HTTP 400) when document is corrupted."""
        import io

        corrupted_bytes = b"CORRUPTED BYTES THAT ARE NOT A PDF"
        upload_data = {'file': (io.BytesIO(corrupted_bytes), 'Corrupt_File.pdf')}
        up_res = self.client.post('/api/documents/upload', data=upload_data, content_type='multipart/form-data')
        doc_id = up_res.get_json()['data'][0]['id']

        extract_res = self.client.post(f'/api/documents/{doc_id}/extract')
        self.assertEqual(extract_res.status_code, 400)
        res_json = extract_res.get_json()
        self.assertFalse(res_json['success'])
        self.assertIn('error', res_json)

    # ==========================================
    # Phase 6: Forensic & Contextual Intelligence Tests
    # ==========================================

    def test_analyze_visual_font_discrepancy(self):
        """Verifies detection of discrepant font family in critical financial text (RULE-VIS-001)."""
        import io
        import pymupdf

        doc = pymupdf.open()
        page = doc.new_page()
        # Insert dominant body text in standard font (Helvetica)
        for i in range(12):
            page.insert_text(
                (50, 50 + (i * 20)),
                f"Standard corporate contract paragraph line {i+1} detailing obligations and terms.",
                fontname="helv",
                fontsize=10.0
            )
        # Insert anomalous text span in Courier with financial figure
        page.insert_text(
            (50, 320),
            "Total Disbursed Balance Due: $9,950,000.00",
            fontname="courier",
            fontsize=12.0
        )
        pdf_bytes = doc.tobytes()
        doc.close()

        upload_data = {'file': (io.BytesIO(pdf_bytes), 'Font_Tampered_Invoice.pdf')}
        up_res = self.client.post('/api/documents/upload', data=upload_data, content_type='multipart/form-data')
        doc_id = up_res.get_json()['data'][0]['id']

        # Trigger Analysis
        analyze_res = self.client.post(f'/api/documents/{doc_id}/analyze')
        self.assertEqual(analyze_res.status_code, 200)
        data = analyze_res.get_json()
        self.assertTrue(data['success'])
        self.assertGreater(data['findings_count'], 0)
        self.assertIn(data['risk_level'], ['Medium Risk', 'High Risk', 'Critical Risk'])

        # Check that font rule was flagged
        findings = data['findings']
        font_findings = [f for f in findings if f['rule_id'] == 'RULE-VIS-001']
        self.assertGreaterEqual(len(font_findings), 1)
        self.assertEqual(font_findings[0]['page_number'], 1)
        self.assertIsNotNone(font_findings[0]['coordinates'])

    def test_analyze_overlapping_text_elements(self):
        """Verifies detection of overlapping/colliding text elements (RULE-VIS-002)."""
        import io
        import pymupdf

        doc = pymupdf.open()
        page = doc.new_page()
        # Original text layer
        page.insert_text((100, 100), "Original Settlement Amount: $10,000.00", fontname="helv", fontsize=11.0)
        # Overlapping overwritten layer at almost identical coordinates
        page.insert_text((102, 101), "Altered Settlement Amount: $90,000.00", fontname="helv", fontsize=11.0)
        pdf_bytes = doc.tobytes()
        doc.close()

        upload_data = {'file': (io.BytesIO(pdf_bytes), 'Overprinted_Contract.pdf')}
        up_res = self.client.post('/api/documents/upload', data=upload_data, content_type='multipart/form-data')
        doc_id = up_res.get_json()['data'][0]['id']

        analyze_res = self.client.post(f'/api/documents/{doc_id}/analyze')
        self.assertEqual(analyze_res.status_code, 200)
        data = analyze_res.get_json()
        findings = data['findings']
        overlap_findings = [f for f in findings if f['rule_id'] == 'RULE-VIS-002']
        self.assertGreaterEqual(len(overlap_findings), 1)
        self.assertEqual(overlap_findings[0]['severity'], 'High')

    def test_analyze_contextual_inconsistencies(self):
        """Verifies contextual rules: reversed chronological due date (RULE-CTX-003)."""
        import io
        import pymupdf

        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text(
            (50, 70),
            "Commercial Vendor Invoice INV-2026-7788\n"
            "Invoice Date: 2026-10-15\n"
            "Payment Due Date: 2026-08-01\n"  # Due date BEFORE invoice date!
            "Total Amount: $45,000.00\n"
            "Vendor: Apex Supplies Ltd.\n"
        )
        pdf_bytes = doc.tobytes()
        doc.close()

        upload_data = {'file': (io.BytesIO(pdf_bytes), 'Inconsistent_Dates_Invoice.pdf')}
        up_res = self.client.post('/api/documents/upload', data=upload_data, content_type='multipart/form-data')
        doc_id = up_res.get_json()['data'][0]['id']

        analyze_res = self.client.post(f'/api/documents/{doc_id}/analyze')
        self.assertEqual(analyze_res.status_code, 200)
        data = analyze_res.get_json()
        findings = data['findings']

        # Verify reversed chronological flow was flagged
        chrono_findings = [f for f in findings if f['rule_id'] == 'RULE-CTX-003']
        self.assertGreaterEqual(len(chrono_findings), 1)
        self.assertIn('chronologically earlier', chrono_findings[0]['description'].lower())

    def test_findings_api_lifecycle(self):
        """Verifies GET /documents/<id>/findings, GET /findings/<id>, and PATCH /findings/<id>."""
        import io
        import pymupdf

        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 70), "Unusual Draft Invoice with anomalous date: 2045-12-31\nAmount: $10,000.00")
        pdf_bytes = doc.tobytes()
        doc.close()

        upload_data = {'file': (io.BytesIO(pdf_bytes), 'Lifecycle_Doc.pdf')}
        up_res = self.client.post('/api/documents/upload', data=upload_data, content_type='multipart/form-data')
        doc_id = up_res.get_json()['data'][0]['id']

        # 1. Trigger analysis
        self.client.post(f'/api/documents/{doc_id}/analyze')

        # 2. GET findings for this document
        doc_find_res = self.client.get(f'/api/documents/{doc_id}/findings')
        self.assertEqual(doc_find_res.status_code, 200)
        findings = doc_find_res.get_json()['data']
        self.assertGreater(len(findings), 0)
        target_fnd = findings[0]
        fnd_id = target_fnd['id']

        # 3. GET single finding by ID
        get_one = self.client.get(f'/api/findings/{fnd_id}')
        self.assertEqual(get_one.status_code, 200)
        self.assertEqual(get_one.get_json()['data']['id'], fnd_id)

        # 4. PATCH status to 'Verified'
        patch_res = self.client.patch(f'/api/findings/{fnd_id}', json={'status': 'Verified'})
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.get_json()['data']['status'], 'Verified')

        # 5. PATCH with invalid status returns 400
        patch_invalid = self.client.patch(f'/api/findings/{fnd_id}', json={'status': 'Fraudulent'})
        self.assertEqual(patch_invalid.status_code, 400)

    # ==========================================
    # Phase 7: Cross-Document Comparison & Evidence Tests
    # ==========================================

    def test_compare_matching_documents(self):
        """Verifies pairwise comparison across two harmonized matching documents."""
        import io
        import pymupdf

        # Document A: Vendor Invoice
        doc_a = pymupdf.open()
        p1 = doc_a.new_page()
        p1.insert_text(
            (50, 50),
            "Original Billing Statement\n"
            "Invoice: INV-2026-8812\n"
            "Date: 2026-10-18\n"
            "Entity: Apex Global Inc.\n"
            "Amount: $4,850,000.00\n"
        )
        bytes_a = doc_a.tobytes()
        doc_a.close()

        # Document B: Bank Mandate
        doc_b = pymupdf.open()
        p2 = doc_b.new_page()
        p2.insert_text(
            (50, 50),
            "Bank Confirmation\n"
            "Reference: INV-2026-8812\n"
            "Execution Date: 2026-10-18\n"
            "Account: Apex Global Inc.\n"
            "Disbursed: $4,850,000.00\n"
        )
        bytes_b = doc_b.tobytes()
        doc_b.close()

        up_a = self.client.post('/api/documents/upload', data={'file': (io.BytesIO(bytes_a), 'Invoice_A.pdf')}, content_type='multipart/form-data')
        doc_a_id = up_a.get_json()['data'][0]['id']

        up_b = self.client.post('/api/documents/upload', data={'file': (io.BytesIO(bytes_b), 'Bank_B.pdf')}, content_type='multipart/form-data')
        doc_b_id = up_b.get_json()['data'][0]['id']

        cmp_res = self.client.post('/api/documents/compare', json={'doc_a_id': doc_a_id, 'doc_b_id': doc_b_id})
        self.assertEqual(cmp_res.status_code, 200)
        data = cmp_res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['verdict'], 'Consistent Records')
        self.assertGreaterEqual(data['matches_count'], 2)
        self.assertEqual(data['conflicts_count'], 0)

    def test_compare_conflicting_documents(self):
        """Verifies detection of monetary and counterparty conflicts across documents."""
        import io
        import pymupdf

        # Document A: High value claim
        doc_a = pymupdf.open()
        p1 = doc_a.new_page()
        p1.insert_text(
            (50, 50),
            "Contract Claim: $4,850,000.00\n"
            "Vendor: Apex Global Inc.\n"
            "Date: 2026-10-18\n"
        )
        bytes_a = doc_a.tobytes()
        doc_a.close()

        # Document B: Lower payment slip with disparate entity
        doc_b = pymupdf.open()
        p2 = doc_b.new_page()
        p2.insert_text(
            (50, 50),
            "Settlement Receipt: $2,100,000.00\n"
            "Payee: Apex Offshore Logistics LLC\n"
            "Date: 2026-05-12\n"
        )
        bytes_b = doc_b.tobytes()
        doc_b.close()

        up_a = self.client.post('/api/documents/upload', data={'file': (io.BytesIO(bytes_a), 'Claim_Doc.pdf')}, content_type='multipart/form-data')
        doc_a_id = up_a.get_json()['data'][0]['id']

        up_b = self.client.post('/api/documents/upload', data={'file': (io.BytesIO(bytes_b), 'Receipt_Doc.pdf')}, content_type='multipart/form-data')
        doc_b_id = up_b.get_json()['data'][0]['id']

        cmp_res = self.client.post('/api/documents/compare', json={'doc_a_id': doc_a_id, 'doc_b_id': doc_b_id})
        self.assertEqual(cmp_res.status_code, 200)
        data = cmp_res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['verdict'], 'High Discrepancy')
        self.assertGreater(data['conflicts_count'], 0)
        self.assertGreater(data['risk_score'], 30)

        # Confirm monetary conflict was flagged in matrix
        matrix = data['alignment_matrix']
        money_conflicts = [m for m in matrix if 'Monetary' in m['attribute'] and m['status'] == 'Conflict']
        self.assertGreaterEqual(len(money_conflicts), 1)

    def test_compare_case_documents_endpoint(self):
        """Verifies case-wide multi-document cross-comparison discovery."""
        import io
        import pymupdf

        # Create case
        c_res = self.client.post('/api/cases', json={'title': 'Cross-Doc Audit Case', 'type': 'Financial Audit', 'priority': 'High'})
        case_id = c_res.get_json()['data']['id']

        # Upload Doc 1 to this case
        d1 = pymupdf.open()
        d1.new_page().insert_text((50, 50), "Document 1 Total: $500,000.00")
        b1 = d1.tobytes()
        d1.close()
        self.client.post('/api/documents/upload', data={'file': (io.BytesIO(b1), 'Case_D1.pdf'), 'case_id': case_id}, content_type='multipart/form-data')

        # Upload Doc 2 to this case
        d2 = pymupdf.open()
        d2.new_page().insert_text((50, 50), "Document 2 Total: $250,000.00")
        b2 = d2.tobytes()
        d2.close()
        self.client.post('/api/documents/upload', data={'file': (io.BytesIO(b2), 'Case_D2.pdf'), 'case_id': case_id}, content_type='multipart/form-data')

        # Run case-wide compare
        case_cmp = self.client.get(f'/api/cases/{case_id}/compare')
        self.assertEqual(case_cmp.status_code, 200)
        data = case_cmp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['documents_count'], 2)
        self.assertEqual(data['comparisons_run'], 1)

    def test_evidence_provenance_graph_endpoint(self):
        """Verifies retrieval of transparent evidence provenance nodes."""
        res = self.client.get('/api/evidence-graph')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)

    def test_compare_validation_errors(self):
        """Verifies edge cases: same document comparison and missing IDs."""
        # 1. Missing parameters
        res1 = self.client.post('/api/documents/compare', json={'doc_a_id': 'DOC-1'})
        self.assertEqual(res1.status_code, 400)

        # 2. Comparing document to itself
        res2 = self.client.post('/api/documents/compare', json={'doc_a_id': 'DOC-1', 'doc_b_id': 'DOC-1'})
        self.assertEqual(res2.status_code, 400)
        self.assertIn('itself', res2.get_json()['error'])

if __name__ == '__main__':
    unittest.main()




