"""
VEXORA — Flask Backend Application
Connects frontend pages with SQLite database, provides REST API endpoints,
serves static UI assets, and records investigation activity.
"""

import sys
import os
from pathlib import Path

# Ensure project root is in sys.path for direct script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

from backend.config import Config, FRONTEND_DIR, DATABASE_PATH
from backend.database import init_db, seed_data, query_db, execute_db
from backend.models import (
    ValidationError,
    validate_case_data,
    validate_user_registration,
    get_all_cases,
    get_case_by_id,
    create_case,
    update_case,
    delete_case,
    get_all_documents,
    get_document_by_id,
    create_document,
    delete_document,
    save_document_extraction,
    get_document_extraction,
    get_all_findings,
    get_finding_by_id,
    get_findings_by_document,
    create_finding,
    update_finding,
    get_system_stats,
    get_audit_logs,
    log_audit
)
from backend.uploader import process_single_upload, allowed_file
from backend.extractor import extract_document_content, ExtractionError
from backend.analyzer import analyze_document

def create_app(config_class=Config):
    """Application factory for VEXORA Flask backend."""
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class)

    # Initialize SQLite database and seed initial demonstration data
    with app.app_context():
        try:
            init_db(app.config.get('DATABASE'))
            seed_data(app.config.get('DATABASE'))
        except Exception as e:
            app.logger.error(f"Error during database initialization: {e}")

    # ==========================================
    # CORS Header Hook (Enables Cross-Origin Dev)
    # ==========================================
    @app.after_request
    def add_cors_headers(response):
        """Allows both standalone static dev server and Flask dev server to access APIs."""
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    # ==========================================
    # Frontend Static & HTML Routes
    # ==========================================
    @app.route('/')
    @app.route('/index.html')
    def serve_index():
        """Serves the main VEXORA Single Page Application."""
        return send_from_directory(FRONTEND_DIR, 'index.html')

    @app.route('/css/<path:filename>')
    def serve_css(filename):
        """Serves CSS stylesheet assets."""
        return send_from_directory(FRONTEND_DIR / 'css', filename)

    @app.route('/js/<path:filename>')
    def serve_js(filename):
        """Serves JavaScript application scripts."""
        return send_from_directory(FRONTEND_DIR / 'js', filename)

    @app.route('/pages/<path:filename>')
    def serve_pages(filename):
        """Serves standalone companion page entrypoints."""
        return send_from_directory(FRONTEND_DIR / 'pages', filename)

    @app.route('/assets/<path:filename>')
    def serve_assets(filename):
        """Serves media and UI assets."""
        assets_dir = FRONTEND_DIR / 'assets'
        if not assets_dir.exists():
            assets_dir.mkdir(parents=True, exist_ok=True)
        return send_from_directory(assets_dir, filename)

    # ==========================================
    # System & Health API Routes
    # ==========================================
    @app.route('/api/health', methods=['GET'])
    def api_health():
        """Returns health status of the application and database."""
        db_alive = False
        try:
            query_db("SELECT 1", one=True)
            db_alive = True
        except Exception:
            db_alive = False

        return jsonify({
            'status': 'healthy' if db_alive else 'degraded',
            'system': 'VEXORA Document Forensics & Intelligence System',
            'version': '1.0.0 (Phase 3)',
            'database': {
                'connected': db_alive,
                'engine': 'SQLite3',
                'path': str(DATABASE_PATH)
            }
        }), 200 if db_alive else 503

    @app.route('/api/stats', methods=['GET'])
    def api_stats():
        """Returns live system statistics for dashboard telemetry."""
        try:
            stats = get_system_stats()
            return jsonify({'success': True, 'data': stats}), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ==========================================
    # Case Management API Routes
    # ==========================================
    @app.route('/api/cases', methods=['GET'])
    def api_list_cases():
        """Lists cases with optional priority, status, or search filters."""
        priority = request.args.get('priority')
        status = request.args.get('status')
        search = request.args.get('search')
        
        cases = get_all_cases(priority=priority, status=status, search=search)
        return jsonify({
            'success': True,
            'count': len(cases),
            'data': cases
        }), 200

    @app.route('/api/cases', methods=['POST'])
    def api_create_case():
        """Creates a new investigation case with strict input validation."""
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or missing JSON payload in request body.'}), 400

        try:
            validated = validate_case_data(payload)
            custom_id = payload.get('id')
            user = session.get('username', 'alex.turner')
            case = create_case(validated, custom_id=custom_id, user=user)
            return jsonify({
                'success': True,
                'message': f"Case {case['id']} registered successfully.",
                'data': case
            }), 201
        except ValidationError as ve:
            return jsonify({'success': False, 'error': ve.message, 'field': ve.field}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': f"Failed to create case: {str(e)}"}), 500

    @app.route('/api/cases/<case_id>', methods=['GET'])
    def api_get_case(case_id):
        """Retrieves details of a specific case with attached documents and findings."""
        case = get_case_by_id(case_id)
        if not case:
            return jsonify({'success': False, 'error': f"Case with ID '{case_id}' was not found."}), 404
        return jsonify({'success': True, 'data': case}), 200

    @app.route('/api/cases/<case_id>', methods=['PUT'])
    def api_update_case(case_id):
        """Updates an existing case."""
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or missing JSON payload.'}), 400

        try:
            user = session.get('username', 'alex.turner')
            updated = update_case(case_id, payload, user=user)
            if not updated:
                return jsonify({'success': False, 'error': f"Case with ID '{case_id}' was not found."}), 404
            return jsonify({
                'success': True,
                'message': f"Case {case_id} updated successfully.",
                'data': updated
            }), 200
        except ValidationError as ve:
            return jsonify({'success': False, 'error': ve.message, 'field': ve.field}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/cases/<case_id>', methods=['DELETE'])
    def api_delete_case(case_id):
        """Deletes an investigation case."""
        user = session.get('username', 'alex.turner')
        success = delete_case(case_id, user=user)
        if not success:
            return jsonify({'success': False, 'error': f"Case '{case_id}' not found."}), 404
        return jsonify({'success': True, 'message': f"Case '{case_id}' deleted successfully."}), 200

    # ==========================================
    # Documents API Routes
    # ==========================================
    @app.route('/api/documents', methods=['GET'])
    def api_list_documents():
        """Lists documents with optional case_id and category filters."""
        case_id = request.args.get('case_id')
        category = request.args.get('category')
        docs = get_all_documents(case_id=case_id, category=category)
        return jsonify({
            'success': True,
            'count': len(docs),
            'data': docs
        }), 200

    @app.route('/api/documents/upload', methods=['POST'])
    def api_upload_documents():
        """
        Ingests multi-format documents (PDF, JPG, PNG).
        Supports single file ('file') or batch uploads ('files').
        Validates formats and sizes, hashes with SHA-256, classifies, and saves to disk and SQLite.
        """
        case_id = request.form.get('case_id') or request.args.get('case_id')
        user = session.get('username', 'alex.turner')
        upload_folder = app.config.get('UPLOAD_FOLDER')

        # Collect files from multipart form
        file_list = []
        if 'files' in request.files:
            file_list = request.files.getlist('files')
        elif 'file' in request.files:
            file_list = [request.files['file']]

        if not file_list or all(f.filename == '' for f in file_list):
            return jsonify({'success': False, 'error': 'No files provided in request.'}), 400

        uploaded_docs = []
        errors = []

        for f in file_list:
            if not f or not f.filename:
                continue
            try:
                doc = process_single_upload(f, case_id=case_id, user=user, upload_folder=upload_folder)
                uploaded_docs.append(doc)
            except ValidationError as ve:
                errors.append({'filename': f.filename, 'error': ve.message, 'field': ve.field})
            except Exception as e:
                errors.append({'filename': f.filename, 'error': str(e)})

        # If all uploads failed due to validation, return 400
        if not uploaded_docs and errors:
            return jsonify({
                'success': False,
                'error': errors[0]['error'],
                'details': errors
            }), 400

        return jsonify({
            'success': True,
            'message': f"Successfully ingested {len(uploaded_docs)} document(s).",
            'count': len(uploaded_docs),
            'data': uploaded_docs,
            'errors': errors if errors else None
        }), 201

    @app.route('/api/documents', methods=['POST'])
    def api_register_document():
        """Registers metadata for a new document."""
        payload = request.get_json(silent=True)
        if not payload or not payload.get('filename'):
            return jsonify({'success': False, 'error': 'Filename is required.'}), 400

        try:
            user = session.get('username', 'alex.turner')
            doc = create_document(payload, user=user)
            return jsonify({
                'success': True,
                'message': f"Document {doc['id']} registered successfully.",
                'data': doc
            }), 201
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/documents/<doc_id>', methods=['GET'])
    def api_get_document(doc_id):
        """Retrieves details of a specific document."""
        doc = get_document_by_id(doc_id)
        if not doc:
            return jsonify({'success': False, 'error': f"Document '{doc_id}' not found."}), 404
        return jsonify({'success': True, 'data': doc}), 200

    @app.route('/api/documents/<doc_id>/download', methods=['GET'])
    def api_download_document(doc_id):
        """Safely streams document file from uploads folder."""
        doc = get_document_by_id(doc_id)
        if not doc or not doc.get('file_path'):
            return jsonify({'success': False, 'error': f"Document '{doc_id}' not found."}), 404

        upload_folder = Path(app.config.get('UPLOAD_FOLDER'))
        disk_filename = Path(doc['file_path']).name
        target_file = upload_folder / disk_filename

        if not target_file.exists():
            return jsonify({'success': False, 'error': f"Physical file '{disk_filename}' missing on disk."}), 404

        return send_from_directory(upload_folder, disk_filename, as_attachment=False, download_name=doc['filename'])

    @app.route('/api/documents/<doc_id>', methods=['DELETE'])
    def api_delete_document(doc_id):
        """Deletes a document record and removes physical file from disk."""
        doc = get_document_by_id(doc_id)
        if not doc:
            return jsonify({'success': False, 'error': f"Document '{doc_id}' not found."}), 404

        user = session.get('username', 'alex.turner')
        delete_document(doc_id, user=user)

        # Remove physical file if exists
        if doc.get('file_path'):
            upload_folder = Path(app.config.get('UPLOAD_FOLDER'))
            disk_filename = Path(doc['file_path']).name
            target_file = upload_folder / disk_filename
            if target_file.exists():
                try:
                    target_file.unlink()
                except Exception as e:
                    app.logger.warning(f"Could not remove physical file {target_file}: {e}")

        return jsonify({'success': True, 'message': f"Document '{doc_id}' deleted successfully."}), 200

    @app.route('/api/documents/<doc_id>/extract', methods=['POST'])
    def api_extract_document(doc_id):
        """
        Executes text, layout block, metadata, and entity extraction on the document.
        Uses PyMuPDF for PDFs and Pillow/Tesseract for images.
        """
        doc = get_document_by_id(doc_id)
        if not doc:
            return jsonify({'success': False, 'error': f"Document '{doc_id}' not found."}), 404

        upload_folder = Path(app.config.get('UPLOAD_FOLDER'))
        disk_filename = Path(doc['file_path']).name
        target_file = upload_folder / disk_filename

        if not target_file.exists():
            return jsonify({'success': False, 'error': f"Physical file '{disk_filename}' not found on disk."}), 404

        try:
            user = session.get('username', 'alex.turner')
            extracted_data = extract_document_content(target_file)
            save_document_extraction(doc_id, extracted_data, user=user)

            return jsonify({
                'success': True,
                'message': f"Successfully extracted {extracted_data['page_count']} page(s) and {len(extracted_data['entities']['dates']) + len(extracted_data['entities']['monetary_values'])} entities.",
                'document_id': doc_id,
                'data': extracted_data
            }), 200
        except ExtractionError as ee:
            return jsonify({'success': False, 'error': str(ee)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': f"Extraction error: {str(e)}"}), 500

    @app.route('/api/documents/<doc_id>/extracted', methods=['GET'])
    def api_get_extracted_document(doc_id):
        """Retrieves previously extracted forensic layout and entities for a document."""
        data = get_document_extraction(doc_id)
        if not data:
            return jsonify({'success': False, 'error': f"No extraction data found for document '{doc_id}'. Please trigger extraction first."}), 404
        return jsonify({'success': True, 'document_id': doc_id, 'data': data}), 200

    @app.route('/api/documents/<doc_id>/analyze', methods=['POST'])
    def api_analyze_document(doc_id):
        """
        Executes Phase 6 forensic & contextual intelligence analysis:
        visual typography, font consistency, text overlaps, boundary checks,
        missing fields, conflicting identifiers, chronological and monetary consistency.
        """
        doc = get_document_by_id(doc_id)
        if not doc:
            return jsonify({'success': False, 'error': f"Document '{doc_id}' not found."}), 404

        try:
            user = session.get('username', 'alex.turner')
            result = analyze_document(doc_id, user=user)
            if not result.get('success'):
                return jsonify(result), 400
            return jsonify(result), 200
        except Exception as e:
            app.logger.error(f"Analysis failure for {doc_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"Forensic analysis failed: {str(e)}"}), 500

    @app.route('/api/documents/<doc_id>/findings', methods=['GET'])
    def api_get_document_findings(doc_id):
        """Retrieves all forensic findings and anomalies for a specific document."""
        doc = get_document_by_id(doc_id)
        if not doc:
            return jsonify({'success': False, 'error': f"Document '{doc_id}' not found."}), 404

        findings = get_findings_by_document(doc_id)
        return jsonify({
            'success': True,
            'document_id': doc_id,
            'count': len(findings),
            'data': findings
        }), 200

    # ==========================================
    # Findings & Evidence API Routes
    # ==========================================
    @app.route('/api/findings', methods=['GET'])
    def api_list_findings():
        """Lists forensic findings and anomalies."""
        case_id = request.args.get('case_id')
        severity = request.args.get('severity')
        findings = get_all_findings(case_id=case_id, severity=severity)
        return jsonify({
            'success': True,
            'count': len(findings),
            'data': findings
        }), 200

    @app.route('/api/findings', methods=['POST'])
    def api_create_finding():
        """Creates a forensic finding record."""
        payload = request.get_json(silent=True)
        if not payload or not payload.get('title') or not payload.get('case_id'):
            return jsonify({'success': False, 'error': 'Both title and case_id are required.'}), 400

        try:
            user = session.get('username', 'alex.turner')
            finding = create_finding(payload, user=user)
            return jsonify({
                'success': True,
                'message': 'Forensic finding created successfully.',
                'data': finding
            }), 201
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/findings/<finding_id>', methods=['GET'])
    def api_get_finding(finding_id):
        """Retrieves a single forensic finding record."""
        finding = get_finding_by_id(finding_id)
        if not finding:
            return jsonify({'success': False, 'error': f"Finding '{finding_id}' not found."}), 404
        return jsonify({'success': True, 'data': finding}), 200

    @app.route('/api/findings/<finding_id>', methods=['PATCH'])
    def api_update_finding(finding_id):
        """Updates status of a forensic finding ('Verified', 'Dismissed', 'Unresolved')."""
        payload = request.get_json(silent=True) or {}
        try:
            user = session.get('username', 'alex.turner')
            updated = update_finding(finding_id, payload, user=user)
            if not updated:
                return jsonify({'success': False, 'error': f"Finding '{finding_id}' not found."}), 404
            return jsonify({
                'success': True,
                'message': f"Finding '{finding_id}' status updated to {updated['status']}.",
                'data': updated
            }), 200
        except ValidationError as ve:
            return jsonify({'success': False, 'error': str(ve)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ==========================================
    # Audit Trail API Route
    # ==========================================
    @app.route('/api/audit-logs', methods=['GET'])
    def api_audit_logs():
        """Retrieves recent chronological audit records."""
        limit = request.args.get('limit', 50, type=int)
        logs = get_audit_logs(limit=limit)
        return jsonify({
            'success': True,
            'count': len(logs),
            'data': logs
        }), 200

    # ==========================================
    # Authentication & Session Routes
    # ==========================================
    @app.route('/api/auth/login', methods=['POST'])
    def api_login():
        """Authenticates investigator credentials with scrypt verification."""
        payload = request.get_json(silent=True) or {}
        username = payload.get('username', '').strip().lower()
        password = payload.get('password', '')

        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password are required.'}), 400

        user = query_db("SELECT * FROM users WHERE username = ? OR email = ?", (username, username), one=True)
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({'success': False, 'error': 'Invalid username or password.'}), 401

        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']

        log_audit("USER_LOGIN", "auth", str(user['id']), f"Investigator '{user['username']}' authenticated successfully.", user['username'])

        return jsonify({
            'success': True,
            'message': 'Authentication successful.',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'badge_number': user['badge_number']
            }
        }), 200

    @app.route('/api/auth/register', methods=['POST'])
    def api_register():
        """Registers a new investigator account with hashed password."""
        payload = request.get_json(silent=True)
        try:
            validated = validate_user_registration(payload)
            
            # Check unique username / email
            existing = query_db("SELECT id FROM users WHERE username = ? OR email = ?", (validated['username'], validated['email']), one=True)
            if existing:
                return jsonify({'success': False, 'error': 'A user with this username or email already exists.'}), 409

            hashed_pw = generate_password_hash(validated['password'], method='scrypt')
            user_id = execute_db(
                """
                INSERT INTO users (username, email, password_hash, role, badge_number)
                VALUES (?, ?, ?, ?, ?)
                """,
                (validated['username'], validated['email'], hashed_pw, validated['role'], validated['badge_number'])
            )

            log_audit("USER_REGISTER", "auth", str(user_id), f"New user '{validated['username']}' registered.", validated['username'])

            return jsonify({
                'success': True,
                'message': 'Investigator registered successfully.',
                'user': {
                    'id': user_id,
                    'username': validated['username'],
                    'email': validated['email'],
                    'role': validated['role'],
                    'badge_number': validated['badge_number']
                }
            }), 201
        except ValidationError as ve:
            return jsonify({'success': False, 'error': ve.message, 'field': ve.field}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/auth/current-user', methods=['GET'])
    def api_current_user():
        """Returns the current investigator's identity."""
        username = session.get('username')
        if not username:
            # Default to baseline analyst profile if unauthenticated
            return jsonify({
                'authenticated': False,
                'user': {
                    'username': 'alex.turner',
                    'email': 'turner@vexora.internal',
                    'role': 'Senior Forensic Specialist',
                    'badge_number': 'VEX-782'
                }
            }), 200

        user = query_db("SELECT id, username, email, role, badge_number FROM users WHERE username = ?", (username,), one=True)
        return jsonify({'authenticated': True, 'user': user}), 200

    # ==========================================
    # Global Error Handlers
    # ==========================================
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': f"Endpoint '{request.path}' not found."}), 404
        return send_from_directory(FRONTEND_DIR, 'index.html'), 200

    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Internal server error occurred.'}), 500
        return jsonify({'error': 'Server error'}), 500

    return app

# Main entrypoint when run as a standalone script
if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    print(f"[*] Starting VEXORA Backend & API Server on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
