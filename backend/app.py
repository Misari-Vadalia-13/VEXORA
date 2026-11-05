"""
VEXORA — Flask Backend Application
Connects frontend pages with SQLite database, provides REST API endpoints,
serves static UI assets, and records investigation activity.
"""

import sys
import os
from functools import wraps
from pathlib import Path

# Ensure project root is in sys.path for direct script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import csv
import io
import json
import hashlib
import secrets
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory, send_file, session, Response
from werkzeug.security import check_password_hash, generate_password_hash

from backend.config import Config, FRONTEND_DIR, DATABASE_PATH
from backend.database import init_db, seed_data, query_db, execute_db
from backend.models import (
    ValidationError,
    check_case_access,
    check_document_access,
    check_finding_access,
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
    log_audit,
    create_report_record,
    get_report_by_id,
    get_reports_by_case,
    get_all_reports
)
from backend.uploader import process_single_upload, allowed_file
from backend.extractor import extract_document_content, ExtractionError
from backend.analyzer import analyze_document
from backend.comparator import (
    compare_two_documents,
    compare_case_documents,
    get_evidence_provenance_nodes
)
from backend.reporter import (
    generate_case_dossier_data,
    generate_dossier_pdf,
    generate_dossier_html
)

def create_app(config_class=Config):
    """Application factory for VEXORA Flask backend."""
    app = Flask(__name__, static_folder=None)
    if isinstance(config_class, dict):
        app.config.from_object(Config)
        app.config.update(config_class)
        if app.config.get('TESTING') and 'VEXORA_REQUIRE_AUTH' not in config_class:
            raw_auth = os.environ.get('VEXORA_REQUIRE_AUTH')
            if raw_auth is not None:
                app.config['VEXORA_REQUIRE_AUTH'] = raw_auth.lower() in ('true', '1', 'yes')
            else:
                app.config['VEXORA_REQUIRE_AUTH'] = False
    else:
        app.config.from_object(config_class)

    # Production safety check for cryptographic signing key
    if app.config.get('ENV') == 'production' or os.environ.get('FLASK_ENV') == 'production':
        sec = app.config.get('SECRET_KEY') or os.environ.get('SECRET_KEY')
        if not sec or sec == 'vexora-forensics-dev-secret-key-2026':
            raise RuntimeError('CRITICAL: Production environment requires an explicitly configured, non-default SECRET_KEY.')

    # Initialize SQLite database and seed initial demonstration data
    with app.app_context():
        try:
            db_path = app.config.get('DATABASE')
            app.logger.info(f"[*] VEXORA Database in use: {Path(db_path).resolve()}")
            init_db(db_path)
            seed_data(db_path)
        except Exception as e:
            app.logger.error(f"Error during database initialization: {e}")

    # ==========================================
    def _get_auth_context():
        """Extracts current session user or defaults to baseline demo investigator."""
        username = session.get('username')
        user_id = session.get('user_id')
        role = session.get('role')
        if not app.config.get('VEXORA_REQUIRE_AUTH', False) and not username:
            return None, None, 'admin'
        return user_id, username, role

    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if app.config.get('VEXORA_REQUIRE_AUTH', False):
                if not session.get('username') and not session.get('user_id'):
                    return jsonify({'success': False, 'error': 'Authentication required. Please log in.'}), 401
            return f(*args, **kwargs)
        return decorated_function

        # CORS Header Hook (Enables Cross-Origin Dev)
    # ==========================================
    @app.after_request
    def add_cors_headers(response):
        """Allows restricted origins or local development servers to access APIs securely."""
        raw_origins = os.environ.get('VEXORA_CORS_ORIGINS', 'http://127.0.0.1:5000,http://localhost:5000,http://127.0.0.1:5500,http://localhost:3000')
        allowed = [o.strip() for o in raw_origins.split(',') if o.strip()]
        origin = request.headers.get('Origin')
        if origin:
            if '*' in allowed or origin in allowed:
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
        else:
            response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    # ==========================================
    # CSRF Protection Hook & Token Endpoint
    # ==========================================
    @app.before_request
    def validate_csrf():
        if not app.config.get('VEXORA_ENFORCE_CSRF', False):
            return
        if request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            return
        # Skip CSRF check for public auth endpoints
        if request.path in ('/api/auth/login', '/api/auth/register', '/api/auth/google'):
            return
        # If no user session, let @login_required return 401 instead of 403
        if not session.get('username') and not session.get('user_id'):
            return
        expected_token = session.get('csrf_token')
        if not expected_token:
            return jsonify({'success': False, 'error': 'CSRF token missing from session.'}), 403
        client_token = request.headers.get('X-CSRF-Token') or request.headers.get('X-CSRFToken')
        if not client_token and request.is_json:
            client_token = (request.get_json(silent=True) or {}).get('csrf_token')
        if not client_token or not secrets.compare_digest(str(client_token), str(expected_token)):
            return jsonify({'success': False, 'error': 'CSRF token missing or invalid.'}), 403

    @app.route('/api/auth/csrf-token', methods=['GET'])
    def api_get_csrf_token():
        """Provides active session CSRF token for client-side state-changing requests."""
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
        return jsonify({'success': True, 'csrf_token': session['csrf_token']}), 200

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

    @app.route('/images/<path:filename>')
    def serve_images(filename):
        """Serves brand and logo image assets."""
        images_dir = FRONTEND_DIR / 'images'
        if not images_dir.exists():
            images_dir.mkdir(parents=True, exist_ok=True)
        return send_from_directory(images_dir, filename)

    @app.route('/favicon.ico')
    def serve_favicon():
        """Serves root favicon."""
        return send_from_directory(FRONTEND_DIR, 'favicon.ico')

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
    @login_required
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
    @login_required
    def api_list_cases():
        """Lists cases with optional priority, status, search, and RBAC filters."""
        priority = request.args.get('priority')
        status = request.args.get('status')
        search = request.args.get('search')
        user_id, username, role = _get_auth_context()
        cases = get_all_cases(priority=priority, status=status, search=search, username=username, role=role)
        return jsonify({
            'success': True,
            'count': len(cases),
            'data': cases
        }), 200

    @app.route('/api/cases', methods=['POST'])
    @login_required
    def api_create_case():
        """Creates a new investigation case with strict input validation."""
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or missing JSON payload in request body.'}), 400

        try:
            validated = validate_case_data(payload)
            custom_id = payload.get('id')
            user_id, username, role = _get_auth_context()
            validated['owner_username'] = username or 'alex.turner'
            validated['owner_id'] = user_id
            user = username or 'alex.turner'
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
    @login_required
    def api_get_case(case_id):
        """Retrieves details of a specific case with attached documents and findings (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_case_access(case_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        case = get_case_by_id(case_id)
        return jsonify({'success': True, 'data': case}), 200

    @app.route('/api/cases/<case_id>', methods=['PUT'])
    @login_required
    def api_update_case(case_id):
        """Updates an existing case (IDOR protected)."""
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or missing JSON payload.'}), 400

        try:
            user_id, username, role = _get_auth_context()
            allowed, res, code = check_case_access(case_id, user_id=user_id, username=username, role=role)
            if not allowed:
                return jsonify({'success': False, 'error': res}), code
            user = username or 'alex.turner'
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
    @login_required
    def api_delete_case(case_id):
        """Deletes an investigation case (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_case_access(case_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        user = username or 'alex.turner'
        success = delete_case(case_id, user=user)
        if not success:
            return jsonify({'success': False, 'error': f"Case '{case_id}' not found."}), 404
        return jsonify({'success': True, 'message': f"Case '{case_id}' deleted successfully."}), 200

    # ==========================================
    # Documents API Routes
    # ==========================================
    @app.route('/api/documents', methods=['GET'])
    @login_required
    def api_list_documents():
        """Lists documents with optional case_id and category filters (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        case_id = request.args.get('case_id')
        category = request.args.get('category')

        if case_id:
            allowed, res, code = check_case_access(case_id, user_id=user_id, username=username, role=role)
            if not allowed:
                return jsonify({'success': False, 'error': res}), code
            docs = get_all_documents(case_id=case_id, category=category)
        else:
            admin_roles = {'admin', 'system administrator', 'lead investigator', 'supervisor', 'senior forensic specialist'}
            is_admin = (not app.config.get('VEXORA_REQUIRE_AUTH', False)) or (role and role.strip().lower() in admin_roles)
            if is_admin:
                docs = get_all_documents(category=category)
            else:
                user_cases = get_all_cases(username=username, role=role)
                case_ids = {c['id'] for c in user_cases}
                all_docs = get_all_documents(category=category)
                docs = [d for d in all_docs if d.get('case_id') in case_ids or d.get('uploaded_by') == username]

        return jsonify({
            'success': True,
            'count': len(docs),
            'data': docs
        }), 200

    @app.route('/api/documents/upload', methods=['POST'])
    @login_required
    def api_upload_documents():
        """
        Ingests multi-format documents (PDF, JPG, PNG).
        Supports single file ('file') or batch uploads ('files').
        Validates formats and sizes, hashes with SHA-256, classifies, and saves to disk and SQLite.
        """
        raw_case_id = request.form.get('case_id') or request.args.get('case_id')
        case_id = raw_case_id.strip() if raw_case_id else None
        user = session.get('username', 'alex.turner')
        upload_folder = app.config.get('UPLOAD_FOLDER')

        # Strict validation: case_id is mandatory and must exist
        if not case_id:
            log_audit("UPLOAD_FAILED", "document", "upload_request", "Upload rejected: Select a case first.", user=user)
            return jsonify({'success': False, 'error': 'Select a case first.'}), 400

        target_case = get_case_by_id(case_id)
        if not target_case:
            log_audit("UPLOAD_FAILED", "document", "upload_request", f"Upload rejected: Case not found: '{case_id}'", user=user)
            return jsonify({'success': False, 'error': f"Case not found: '{case_id}'"}), 400

        user_id, username, role = _get_auth_context()
        allowed, res, code = check_case_access(case_id, user_id=user_id, username=username, role=role)
        if not allowed:
            log_audit("UPLOAD_FAILED", "document", "upload_request", f"Upload rejected: {res}", user=user)
            return jsonify({'success': False, 'error': res}), code

        # Collect files from multipart form
        file_list = []
        if 'files' in request.files:
            file_list = request.files.getlist('files')
        elif 'file' in request.files:
            file_list = [request.files['file']]

        if not file_list or all(f.filename == '' for f in file_list):
            log_audit("UPLOAD_FAILED", "document", "upload_request", "Upload rejected: No files provided in request.", user=user)
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
            err_msg = errors[0]['error']
            log_audit("UPLOAD_FAILED", "document", "upload_request", f"Upload rejected: {err_msg}", user=user)
            return jsonify({
                'success': False,
                'error': err_msg,
                'details': errors
            }), 400

        return jsonify({
            'success': True,
            'message': f"Successfully ingested {len(uploaded_docs)} document(s).",
            'count': len(uploaded_docs),
            'data': uploaded_docs,
            'id': uploaded_docs[0]['id'] if uploaded_docs else None,
            'document_id': uploaded_docs[0]['id'] if uploaded_docs else None,
            'case_id': uploaded_docs[0]['case_id'] if uploaded_docs else case_id,
            'errors': errors if errors else None
        }), 201

    @app.route('/api/documents', methods=['POST'])
    @login_required
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
    @login_required
    def api_get_document(doc_id):
        """Retrieves details of a specific document (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_document_access(doc_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        doc = res
        return jsonify({'success': True, 'data': doc}), 200

    @app.route('/api/documents/<doc_id>/download', methods=['GET'])
    @login_required
    def api_download_document(doc_id):
        """Safely streams document file from uploads folder (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_document_access(doc_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        doc = res
        if not doc or not doc.get('file_path'):
            return jsonify({'success': False, 'error': f"Document '{doc_id}' not found."}), 404

        upload_folder = Path(app.config.get('UPLOAD_FOLDER'))
        disk_filename = Path(doc['file_path']).name
        target_file = upload_folder / disk_filename

        if not target_file.exists():
            return jsonify({'success': False, 'error': f"Physical file '{disk_filename}' missing on disk."}), 404

        return send_from_directory(upload_folder, disk_filename, as_attachment=False, download_name=doc['filename'])

    @app.route('/api/evidence/<path:filename>', methods=['GET'])
    @login_required
    def api_get_evidence_file(filename):
        """Streams generated forensic visualization files (e.g. ELA difference maps) with traversal protection."""
        upload_folder = Path(app.config.get('UPLOAD_FOLDER', Config.UPLOAD_FOLDER))
        evidence_dir = upload_folder / 'evidence'
        if not evidence_dir.exists():
            evidence_dir.mkdir(parents=True, exist_ok=True)
        # Defense-in-depth against directory traversal
        target = (evidence_dir / filename).resolve()
        if not str(target).startswith(str(evidence_dir.resolve())) or not target.exists():
            return jsonify({'success': False, 'error': f"Evidence file '{filename}' not found."}), 404
        return send_from_directory(evidence_dir, filename)

    @app.route('/api/documents/<doc_id>/integrity', methods=['GET'])
    @login_required
    def api_check_document_integrity(doc_id):
        """
        Recomputes SHA-256 of the physical document file on disk and verifies
        it against the immutable stored hash captured at ingest time (IDOR protected).
        Records an INTEGRITY_CHECK event into the immutable audit trail.
        """
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_document_access(doc_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        doc = res
        if not doc:
            return jsonify({'success': False, 'error': f"Document '{doc_id}' not found."}), 404

        stored_hash = doc.get('file_hash') or ''
        upload_folder = Path(app.config.get('UPLOAD_FOLDER', Config.UPLOAD_FOLDER))
        raw_path = Path(doc['file_path']) if doc.get('file_path') else None

        target_file = None
        if raw_path:
            candidate = upload_folder / raw_path.name
            if candidate.exists() and candidate.is_file():
                target_file = candidate
            elif raw_path.exists() and raw_path.is_file():
                target_file = raw_path
            else:
                candidate_base = Config.BASE_DIR / raw_path
                if candidate_base.exists() and candidate_base.is_file():
                    target_file = candidate_base

        user = session.get('username', 'alex.turner')
        checked_at = datetime.now(timezone.utc).isoformat()

        if not target_file or not target_file.exists():
            log_audit(
                "INTEGRITY_CHECK_FAILED",
                "document",
                doc_id,
                f"Integrity check failed: physical file missing on disk (expected: {raw_path})",
                user=user
            )
            return jsonify({
                'success': False,
                'error': f"Physical file '{raw_path.name if raw_path else 'unknown'}' missing on disk.",
                'document_id': doc_id,
                'stored_hash': stored_hash,
                'current_hash': None,
                'match': False,
                'status': 'missing',
                'checked_at': checked_at
            }), 404

        try:
            file_bytes = target_file.read_bytes()
            current_hash = hashlib.sha256(file_bytes).hexdigest()
            md5_hash = hashlib.md5(file_bytes).hexdigest()
            match = (current_hash.lower() == stored_hash.lower())

            log_audit(
                "INTEGRITY_CHECK",
                "document",
                doc_id,
                f"SHA-256 verification: {'MATCH' if match else 'MISMATCH'} (stored={stored_hash[:12]}..., current={current_hash[:12]}...)",
                user=user
            )

            return jsonify({
                'success': True,
                'document_id': doc_id,
                'filename': doc.get('filename'),
                'stored_hash': stored_hash,
                'current_hash': current_hash,
                'match': match,
                'checked_at': checked_at,
                'status': 'verified' if match else 'tampered',
                'tamper_status': 'VERIFIED' if match else 'TAMPERED',
                'sha256_hash': current_hash,
                'md5_hash': md5_hash,
                'file_size_bytes': len(file_bytes),
                'standard_alignment': 'Aligned with ISO/IEC 27037 principles for digital evidence handling (no formal compliance claimed)'
            }), 200
        except Exception as e:
            app.logger.error(f"Error computing file integrity for {doc_id}: {e}")
            return jsonify({'success': False, 'error': f"Error computing file integrity: {str(e)}"}), 500

    @app.route('/api/documents/<doc_id>/custody', methods=['GET'])
    @login_required
    def api_get_document_custody(doc_id):
        """
        Retrieves ordered chronological chain of custody events for a specific document
        from the immutable audit trail (IDOR protected).
        """
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_document_access(doc_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        doc = res
        if not doc:
            return jsonify({'success': False, 'error': f"Document '{doc_id}' not found."}), 404

        filename = doc.get('filename') or ''
        case_id = doc.get('case_id') or ''

        # Query all audit events where this document is the primary entity or explicitly referenced
        query = """
            SELECT * FROM audit_logs
            WHERE entity_id = ?
               OR (details LIKE ? AND details NOT LIKE '%upload_request%')
            ORDER BY timestamp ASC, id ASC
        """
        term = f"%{doc_id}%"
        rows = query_db(query, (doc_id, term))

        if filename:
            name_term = f"%{filename}%"
            extra_query = """
                SELECT * FROM audit_logs
                WHERE details LIKE ?
                  AND id NOT IN (SELECT id FROM audit_logs WHERE entity_id = ? OR details LIKE ?)
                ORDER BY timestamp ASC, id ASC
            """
            extra_rows = query_db(extra_query, (name_term, doc_id, term))
            rows = sorted(list(rows) + list(extra_rows), key=lambda r: (r['timestamp'], r['id']))

        events = []
        for r in rows:
            events.append({
                'id': r['id'],
                'timestamp': r['timestamp'],
                'actor': r['user'],
                'action': r['action'],
                'entity_type': r['entity_type'],
                'entity_id': r['entity_id'],
                'details': r['details']
            })

        return jsonify({
            'success': True,
            'document_id': doc_id,
            'filename': filename,
            'case_id': case_id,
            'stored_hash': doc.get('file_hash'),
            'count': len(events),
            'events': events,
            'custody_chain': events
        }), 200

    @app.route('/api/documents/<doc_id>', methods=['DELETE'])
    @login_required
    def api_delete_document(doc_id):
        """Deletes a document record and removes physical file from disk (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_document_access(doc_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        doc = res
        user = username or 'alex.turner'
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
    @login_required
    def api_extract_document(doc_id):
        """
        Executes text, layout block, metadata, and entity extraction on the document (IDOR protected).
        Uses PyMuPDF for PDFs and Pillow/Tesseract for images.
        """
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_document_access(doc_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        doc = res

        upload_folder = Path(app.config.get('UPLOAD_FOLDER'))
        disk_filename = Path(doc['file_path']).name
        target_file = upload_folder / disk_filename

        if not target_file.exists():
            return jsonify({'success': False, 'error': f"Physical file '{disk_filename}' not found on disk."}), 404

        try:
            user = username or 'alex.turner'
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
    @login_required
    def api_get_extracted_document(doc_id):
        """Retrieves previously extracted forensic layout and entities for a document (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_document_access(doc_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code

        data = get_document_extraction(doc_id)
        if not data:
            return jsonify({'success': False, 'error': f"No extraction data found for document '{doc_id}'. Please trigger extraction first."}), 404
        return jsonify({'success': True, 'document_id': doc_id, 'data': data}), 200

    @app.route('/api/documents/<doc_id>/analyze', methods=['POST'])
    @login_required
    def api_analyze_document(doc_id):
        """
        Executes Phase 6 forensic & contextual intelligence analysis (IDOR protected):
        visual typography, font consistency, text overlaps, boundary checks,
        missing fields, conflicting identifiers, chronological and monetary consistency.
        """
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_document_access(doc_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        doc = res

        try:
            user = username or 'alex.turner'
            result = analyze_document(doc_id, user=user)
            if not result.get('success'):
                return jsonify(result), 400
            return jsonify(result), 200
        except Exception as e:
            app.logger.error(f"Analysis failure for {doc_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"Forensic analysis failed: {str(e)}"}), 500

    @app.route('/api/documents/<doc_id>/findings', methods=['GET'])
    @login_required
    def api_get_document_findings(doc_id):
        """Retrieves all forensic findings and anomalies for a specific document (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_document_access(doc_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        doc = res

        findings = get_findings_by_document(doc_id)
        try:
            from backend.explainability import format_explainable_finding, get_status_badge
            for f in findings:
                f['status_badge'] = get_status_badge(f)
                f['explainability'] = format_explainable_finding(f)
        except Exception:
            pass
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
    @login_required
    def api_list_findings():
        """Lists forensic findings and anomalies (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        case_id = request.args.get('case_id')
        severity = request.args.get('severity')

        if case_id:
            allowed, res, code = check_case_access(case_id, user_id=user_id, username=username, role=role)
            if not allowed:
                return jsonify({'success': False, 'error': res}), code
            findings = get_all_findings(case_id=case_id, severity=severity)
        else:
            admin_roles = {'admin', 'system administrator', 'lead investigator', 'supervisor', 'senior forensic specialist'}
            is_admin = (not app.config.get('VEXORA_REQUIRE_AUTH', False)) or (role and role.strip().lower() in admin_roles)
            if is_admin:
                findings = get_all_findings(severity=severity)
            else:
                user_cases = get_all_cases(username=username, role=role)
                case_ids = {c['id'] for c in user_cases}
                all_findings = get_all_findings(severity=severity)
                findings = [f for f in all_findings if f.get('case_id') in case_ids]

        try:
            from backend.explainability import format_explainable_finding, get_status_badge
            for f in findings:
                f['status_badge'] = get_status_badge(f)
                f['explainability'] = format_explainable_finding(f)
        except Exception:
            pass
        return jsonify({
            'success': True,
            'count': len(findings),
            'data': findings
        }), 200

    @app.route('/api/findings', methods=['POST'])
    @login_required
    def api_create_finding():
        """Creates a forensic finding record (IDOR protected)."""
        payload = request.get_json(silent=True)
        if not payload or not payload.get('title') or not payload.get('case_id'):
            return jsonify({'success': False, 'error': 'Both title and case_id are required.'}), 400

        user_id, username, role = _get_auth_context()
        allowed, res, code = check_case_access(payload['case_id'], user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code

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
    @login_required
    def api_get_finding(finding_id):
        """Retrieves a single forensic finding record (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_finding_access(finding_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        return jsonify({'success': True, 'data': res}), 200

    @app.route('/api/findings/<finding_id>', methods=['PATCH'])
    @login_required
    def api_update_finding(finding_id):
        """Updates status of a forensic finding ('Verified', 'Dismissed', 'Unresolved') (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_finding_access(finding_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
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

    @app.route('/api/findings/<finding_id>/review', methods=['POST', 'PATCH'])
    @login_required
    def api_review_finding(finding_id):
        """Records human investigator review decision (Accept / Dismiss as false positive / Needs more info) along with an optional reviewer note (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_finding_access(finding_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        payload = request.get_json(silent=True) or {}
        try:
            user = session.get('username') or username or 'alex.turner'
            updated = update_finding(finding_id, payload, user=user)
            if not updated:
                return jsonify({'success': False, 'error': f"Finding '{finding_id}' not found."}), 404
            return jsonify({
                'success': True,
                'message': f"Finding '{finding_id}' review decision recorded as '{updated.get('reviewer_decision') or updated['status']}'.",
                'data': updated
            }), 200
        except ValidationError as ve:
            return jsonify({'success': False, 'error': str(ve)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # ==========================================
    # Cross-Document Comparison & Evidence Routes (Phase 7)
    # ==========================================
    @app.route('/api/documents/compare', methods=['POST'])
    @login_required
    def api_compare_documents():
        """
        Executes pairwise cross-document comparison:
        analyzes monetary alignment, date synchronization, counterparty variations,
        identifier correlations, and duplicate files (IDOR protected).
        """
        payload = request.get_json(silent=True) or {}
        doc_a_id = payload.get('doc_a_id')
        doc_b_id = payload.get('doc_b_id')

        if not doc_a_id or not doc_b_id:
            return jsonify({'success': False, 'error': 'Both doc_a_id and doc_b_id are required in JSON payload.'}), 400

        if doc_a_id == doc_b_id:
            return jsonify({'success': False, 'error': 'Cannot compare a document against itself. Please select two distinct documents.'}), 400

        user_id, username, role = _get_auth_context()
        allowed_a, res_a, code_a = check_document_access(doc_a_id, user_id=user_id, username=username, role=role)
        if not allowed_a:
            return jsonify({'success': False, 'error': f"Document A access denied: {res_a}"}), code_a
        allowed_b, res_b, code_b = check_document_access(doc_b_id, user_id=user_id, username=username, role=role)
        if not allowed_b:
            return jsonify({'success': False, 'error': f"Document B access denied: {res_b}"}), code_b

        try:
            user = session.get('username', 'alex.turner')
            result = compare_two_documents(doc_a_id, doc_b_id, user=user)
            if not result.get('success'):
                return jsonify(result), 400
            return jsonify(result), 200
        except Exception as e:
            app.logger.error(f"Comparison error between {doc_a_id} and {doc_b_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"Cross-document comparison failed: {str(e)}"}), 500

    @app.route('/api/cases/<case_id>/analyze', methods=['POST'])
    @login_required
    def api_analyze_case_documents(case_id):
        """Executes full-case analysis on all unanalyzed documents and runs cross-document discrepancy discovery (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_case_access(case_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        case = res

        try:
            from backend.reporter import _ensure_case_analysis
            user = session.get('username', 'alex.turner')
            _ensure_case_analysis(case_id, user=user)
            updated = get_case_by_id(case_id)
            all_findings = []
            for d in updated.get('documents', []):
                all_findings.extend(get_findings_by_document(d['id']))
            return jsonify({
                'success': True,
                'case_id': case_id,
                'documents_count': len(updated.get('documents', [])),
                'findings_count': len(all_findings),
                'findings': all_findings
            }), 200
        except Exception as e:
            app.logger.error(f"Case analysis failure for {case_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/cases/<case_id>/compare', methods=['GET'])
    @login_required
    def api_compare_case_documents(case_id):
        """Executes full-case cross-document discrepancy discovery across all assigned files (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_case_access(case_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        case = res

        try:
            user = session.get('username', 'alex.turner')
            result = compare_case_documents(case_id, user=user)
            return jsonify(result), 200
        except Exception as e:
            app.logger.error(f"Case comparison error for {case_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"Case comparison failed: {str(e)}"}), 500

    @app.route('/api/evidence-graph', methods=['GET'])
    @login_required
    def api_evidence_graph():
        """Retrieves transparent evidence provenance nodes linking findings to document pages (IDOR protected)."""
        case_id = request.args.get('case_id')
        user_id, username, role = _get_auth_context()
        if case_id:
            allowed, res, code = check_case_access(case_id, user_id=user_id, username=username, role=role)
            if not allowed:
                return jsonify({'success': False, 'error': res}), code
        try:
            nodes = get_evidence_provenance_nodes(case_id=case_id)
            return jsonify({
                'success': True,
                'count': len(nodes),
                'case_id': case_id,
                'data': nodes
            }), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/cases/<case_id>/relationships', methods=['GET'])
    @login_required
    def api_case_relationships(case_id):
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_case_access(case_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        """
        Phase F: Cross-document correlation & relationship graph.
        Protected by ENABLE_CORRELATOR feature flag.
        """
        from backend.config import Config
        enabled = getattr(Config, 'ENABLE_CORRELATOR', False)
        if not enabled:
            return jsonify({
                'success': False,
                'error': 'Cross-document correlator is disabled. Enable via ENABLE_CORRELATOR=true.'
            }), 403

        try:
            from backend.correlator import build_case_relationship_graph
            graph = build_case_relationship_graph(case_id)
            graph['data'] = {
                'nodes': graph.get('nodes', []),
                'edges': graph.get('edges', []),
                'metrics': graph.get('metrics', {})
            }
            return jsonify(graph), 200
        except Exception as e:
            app.logger.error(f"Failed to build relationship graph for case {case_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"Failed to build relationship graph: {str(e)}"}), 500

    @app.route('/api/cases/<case_id>/timeline', methods=['GET'])
    @login_required
    def api_case_timeline(case_id):
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_case_access(case_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        """
        Synthesizes an ordered cross-document chronological event timeline
        and identifies temporal sequence anomalies across case documents.
        """
        try:
            from backend.correlator import build_case_timeline
            timeline = build_case_timeline(case_id)
            return jsonify(timeline), 200
        except Exception as e:
            app.logger.error(f"Failed to build timeline for case {case_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"Failed to build case timeline: {str(e)}"}), 500

    # ==========================================
    # Investigation Dossier & Report Routes (Phase 8)
    # ==========================================
    @app.route('/api/cases/<case_id>/dossier', methods=['GET'])
    @login_required
    def api_get_case_dossier(case_id):
        """
        Retrieves complete structured JSON investigation dossier (IDOR protected):
        case metadata, evidence inventory, extracted entities, visual & contextual findings,
        cross-document discrepancies, provenance nodes, risk scores, and mandatory disclaimer.
        """
        try:
            user_id, username, role = _get_auth_context()
            allowed, res, code = check_case_access(case_id, user_id=user_id, username=username, role=role)
            if not allowed:
                return jsonify({'success': False, 'error': res}), code
            dossier = generate_case_dossier_data(case_id)
            return jsonify({
                'success': True,
                'case_id': case_id,
                'data': dossier
            }), 200
        except ValueError as ve:
            return jsonify({'success': False, 'error': str(ve)}), 404
        except Exception as e:
            app.logger.error(f"Failed to generate dossier data for case {case_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"Failed to generate dossier data: {str(e)}"}), 500

    @app.route('/api/cases/<case_id>/report', methods=['POST'])
    @login_required
    def api_generate_case_report(case_id):
        """
        Generates a publication-ready investigation dossier report (IDOR protected).
        """
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_case_access(case_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        case = res

        payload = request.get_json(silent=True) or {}
        report_format = payload.get('format', 'pdf').lower().strip()
        user = session.get('username', 'Lead Investigator')

        if report_format not in ('pdf', 'html'):
            return jsonify({'success': False, 'error': "Invalid report format. Supported formats are 'pdf' and 'html'."}), 400

        try:
            if report_format == 'pdf':
                result = generate_dossier_pdf(case_id, user=user)
            else:
                result = generate_dossier_html(case_id, user=user)

            result['download_url'] = f"/api/reports/{result['report_id']}/download"
            result['view_url'] = f"/api/reports/{result['report_id']}/view"
            return jsonify(result), 201
        except ValueError as ve:
            return jsonify({'success': False, 'error': str(ve)}), 400
        except Exception as e:
            app.logger.error(f"Report generation failed for case {case_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"Report generation failed: {str(e)}"}), 500

    @app.route('/api/reports', methods=['GET'])
    @login_required
    def api_list_reports():
        """Lists generated investigation reports, optionally filtered by case_id (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        case_id = request.args.get('case_id')
        if case_id:
            allowed, res, code = check_case_access(case_id, user_id=user_id, username=username, role=role)
            if not allowed:
                return jsonify({'success': False, 'error': res}), code
            reports = get_reports_by_case(case_id)
        else:
            admin_roles = {'admin', 'system administrator', 'lead investigator', 'supervisor', 'senior forensic specialist'}
            is_admin = (not app.config.get('VEXORA_REQUIRE_AUTH', False)) or (role and role.strip().lower() in admin_roles)
            if is_admin:
                limit = request.args.get('limit', 50, type=int)
                reports = get_all_reports(limit=limit)
            else:
                user_cases = get_all_cases(username=username, role=role)
                case_ids = {c['id'] for c in user_cases}
                all_reps = get_all_reports(limit=100)
                reports = [r for r in all_reps if r.get('case_id') in case_ids]

        return jsonify({
            'success': True,
            'count': len(reports),
            'data': reports
        }), 200

    @app.route('/api/reports/<report_id>', methods=['GET'])
    @login_required
    def api_get_report_metadata(report_id):
        """Retrieves metadata for a specific generated report (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        report = get_report_by_id(report_id)
        if not report:
            return jsonify({'success': False, 'error': f"Report '{report_id}' not found."}), 404
        if report.get('case_id'):
            allowed, res, code = check_case_access(report['case_id'], user_id=user_id, username=username, role=role)
            if not allowed:
                return jsonify({'success': False, 'error': res}), code

        return jsonify({
            'success': True,
            'data': report,
            'download_url': f"/api/reports/{report_id}/download",
            'view_url': f"/api/reports/{report_id}/view"
        }), 200

    @app.route('/api/reports/<report_id>/download', methods=['GET'])
    @login_required
    def api_download_report(report_id):
        """Streams and downloads a generated report file (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        report = get_report_by_id(report_id)
        if not report:
            return jsonify({'success': False, 'error': f"Report '{report_id}' not found."}), 404
        if report.get('case_id'):
            allowed, res, code = check_case_access(report['case_id'], user_id=user_id, username=username, role=role)
            if not allowed:
                return jsonify({'success': False, 'error': res}), code

        file_path = Path(report['file_path'])
        if not file_path.exists():
            return jsonify({'success': False, 'error': "Report file was not found on local storage."}), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_path.name
        )

    @app.route('/api/reports/<report_id>/view', methods=['GET'])
    @login_required
    def api_view_report(report_id):
        """Serves a generated report inline for in-browser preview (IDOR protected)."""
        user_id, username, role = _get_auth_context()
        report = get_report_by_id(report_id)
        if not report:
            return jsonify({'success': False, 'error': f"Report '{report_id}' not found."}), 404
        if report.get('case_id'):
            allowed, res, code = check_case_access(report['case_id'], user_id=user_id, username=username, role=role)
            if not allowed:
                return jsonify({'success': False, 'error': res}), code

        file_path = Path(report['file_path'])
        if not file_path.exists():
            return jsonify({'success': False, 'error': "Report file was not found on local storage."}), 404

        mime_type = 'application/pdf' if report['file_format'] == 'pdf' else 'text/html'
        return send_file(
            file_path,
            as_attachment=False,
            mimetype=mime_type
        )


    # ==========================================
    # Audit Trail API Routes (Phase 9)
    # ==========================================
    @app.route('/api/audit-logs', methods=['GET'])
    @login_required
    def api_audit_logs():
        """
        Retrieves chronological audit records with optional filtering
        by action, entity_type, user, and limit (Admin restricted).
        """
        user_id, username, role = _get_auth_context()
        admin_roles = {'admin', 'system administrator', 'lead investigator', 'supervisor', 'senior forensic specialist'}
        if app.config.get('VEXORA_REQUIRE_AUTH', False) and (not role or role.strip().lower() not in admin_roles):
            return jsonify({'success': False, 'error': 'Administrative privileges required to access audit trails.'}), 403

        action = request.args.get('action')
        entity_type = request.args.get('entity_type')
        user = request.args.get('user')
        limit = request.args.get('limit', 100, type=int)

        logs = get_audit_logs(action=action, entity_type=entity_type, user=user, limit=limit)
        return jsonify({
            'success': True,
            'count': len(logs),
            'filters': {
                'action': action,
                'entity_type': entity_type,
                'user': user,
                'limit': limit
            },
            'data': logs
        }), 200

    @app.route('/api/audit-logs/export', methods=['GET'])
    @login_required
    def api_export_audit_logs():
        user_id, username, role = _get_auth_context()
        admin_roles = {'admin', 'system administrator', 'lead investigator', 'supervisor', 'senior forensic specialist'}
        if app.config.get('VEXORA_REQUIRE_AUTH', False) and (not role or role.strip().lower() not in admin_roles):
            return jsonify({'success': False, 'error': 'Administrative privileges required to export audit trails.'}), 403
        """
        Exports the entire immutable investigation audit trail in CSV or JSON format
        for courtroom archival and forensic compliance verification.
        """
        export_format = request.args.get('format', 'csv').lower().strip()
        limit = request.args.get('limit', 500, type=int)
        logs = get_audit_logs(limit=limit)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if export_format == 'json':
            json_str = json.dumps({'success': True, 'count': len(logs), 'exported_at': datetime.now().isoformat(), 'data': logs}, indent=2)
            return Response(
                json_str,
                mimetype='application/json',
                headers={'Content-Disposition': f'attachment; filename="VEXORA_Audit_Trail_{timestamp}.json"'}
            )

        # Default to RFC 4180 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Audit ID', 'Timestamp', 'Action', 'Entity Type', 'Entity ID', 'Investigator / User', 'Details'])

        for log in logs:
            writer.writerow([
                log['id'],
                log['timestamp'],
                log['action'],
                log['entity_type'],
                log['entity_id'] or '',
                log['user'] or 'System',
                log['details'] or ''
            ])

        csv_content = output.getvalue()
        output.close()

        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename="VEXORA_Audit_Trail_{timestamp}.csv"'}
        )

    # ==========================================
    # System Diagnostics & Health Check (Phase 9)
    # ==========================================
    @app.route('/api/system/diagnostics', methods=['GET'])
    @login_required
    def api_system_diagnostics():
        user_id, username, role = _get_auth_context()
        admin_roles = {'admin', 'system administrator', 'lead investigator', 'supervisor', 'senior forensic specialist'}
        if app.config.get('VEXORA_REQUIRE_AUTH', False) and (not role or role.strip().lower() not in admin_roles):
            return jsonify({'success': False, 'error': 'Administrative privileges required to view diagnostics.'}), 403
        """
        Executes an end-to-end self-diagnostic check across the database,
        storage directories, and forensic extraction engines.
        """
        import sys
        try:
            import pymupdf
            mupdf_ver = getattr(pymupdf, '__version__', 'Installed')
        except Exception:
            mupdf_ver = 'Not Available'

        # Check database table counts
        db_stats = {}
        try:
            for tbl in ['users', 'cases', 'documents', 'findings', 'comparisons', 'reports', 'audit_logs']:
                row = query_db(f"SELECT COUNT(*) AS count FROM {tbl}", one=True)
                db_stats[tbl] = row['count'] if row else 0
            db_status = 'Healthy'
        except Exception as e:
            db_status = f'Error: {str(e)}'

        # Check directories
        upload_dir = Path(Config.UPLOAD_FOLDER)
        reports_dir = Path(Config.REPORTS_FOLDER)

        storage_health = {
            'upload_folder': str(upload_dir),
            'upload_folder_writable': upload_dir.exists() and os.access(upload_dir, os.W_OK),
            'reports_folder': str(reports_dir),
            'reports_folder_writable': reports_dir.exists() and os.access(reports_dir, os.W_OK)
        }

        all_healthy = (
            db_status == 'Healthy' and
            storage_health['upload_folder_writable'] and
            storage_health['reports_folder_writable']
        )

        # V2 Diagnostics & Feature Flags Status (Phase H)
        try:
            from backend.banner import get_v2_features_status
            v2_status = get_v2_features_status(app)
        except Exception:
            v2_status = {}

        return jsonify({
            'success': True,
            'status': 'Operational' if all_healthy else 'Degraded',
            'engine_version': 'VEXORA v1.0 (Phase 9 Fully Integrated)',
            'python_version': sys.version.split()[0],
            'pymupdf_version': mupdf_ver,
            'v2_features': v2_status,
            'tesseract_available': v2_status.get('tesseract_available', False),
            'tesseract_detail': v2_status.get('tesseract_detail', 'Unknown'),
            'database': {
                'status': db_status,
                'engine': 'SQLite 3 Relational',
                'table_counts': db_stats
            },
            'storage': storage_health,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

        # Session Fixation Defense & Expiration Configuration
        session.clear()
        session.permanent = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        csrf_tok = secrets.token_hex(32)
        session['csrf_token'] = csrf_tok

        log_audit("USER_LOGIN", "auth", str(user['id']), f"Investigator '{user['username']}' authenticated successfully.", user['username'])

        return jsonify({
            'success': True,
            'message': 'Authentication successful.',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'badge_number': user['badge_number'],
                'csrf_token': csrf_tok
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

    @app.route('/api/auth/logout', methods=['POST'])
    def api_logout():
        """Terminates active session, clears cookies, and records logout audit event."""
        username = session.get('username', 'Anonymous')
        session.clear()
        log_audit("USER_LOGOUT", "auth", "session", f"Investigator '{username}' logged out.", username)
        resp = jsonify({'success': True, 'message': 'Logged out successfully.'})
        cookie_name = app.config.get('SESSION_COOKIE_NAME', 'vexora_session')
        resp.delete_cookie(cookie_name, path='/')
        return resp, 200

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

    @app.route('/api/auth/google', methods=['GET', 'POST'])
    def api_google_demo_login():
        """
        Google SSO authentication endpoint.
        Returns 501 Not Implemented if real Google OAuth is unconfigured, unless
        VEXORA_ALLOW_DEMO_LOGIN=true is explicitly configured for offline demonstration.
        """
        has_google_oauth = bool(app.config.get('GOOGLE_CLIENT_ID') or os.environ.get('GOOGLE_CLIENT_ID'))
        raw_demo_flag = app.config.get('VEXORA_ALLOW_DEMO_LOGIN', None)
        if raw_demo_flag is not None:
            if isinstance(raw_demo_flag, str):
                allow_demo_sso = raw_demo_flag.lower() in ('true', '1')
            else:
                allow_demo_sso = bool(raw_demo_flag)
        else:
            # Secure by default: require real OAuth when auth is enforced; allow demo SSO only in offline/demo mode
            allow_demo_sso = not app.config.get('VEXORA_REQUIRE_AUTH', False)

        if not has_google_oauth and not allow_demo_sso:
            return jsonify({
                'success': False,
                'error': 'Google OAuth 2.0 is not configured on this server. Please use standard investigator credentials.'
            }), 501

        user = query_db("SELECT id, username, email, role, badge_number FROM users WHERE username = 'alex.turner'", one=True)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            user_data = dict(user)
        else:
            user_data = {
                'username': 'alex.turner',
                'email': 'turner@vexora.internal',
                'role': 'Senior Forensic Specialist',
                'badge_number': 'VEX-782'
            }
        user_data['auth_note'] = 'local demo login (not verified by Google)'
        log_audit("DEMO_OAUTH_LOGIN", "auth", str(user_data.get('id', 'mock')), "Investigator authenticated via local demo OAuth mechanism.", user_data['username'])
        return jsonify({
            'success': True,
            'message': 'Local demo sign-in successful (not verified by Google).',
            'auth_mode': 'demo_unverified',
            'user': user_data
        }), 200

    # ==========================================
    # Phase A: Visual Evidence Overlay Routes
    # ==========================================
    @app.route('/api/findings/<finding_id>/evidence-image', methods=['GET'])
    @login_required
    def api_get_finding_evidence_image(finding_id):
        """
        Renders the document page where this finding was detected, highlighting its
        bounding box in red with its rule ID badge (IDOR protected).
        """
        try:
            user_id, username, role = _get_auth_context()
            allowed, res, code = check_finding_access(finding_id, user_id=user_id, username=username, role=role)
            if not allowed:
                return jsonify({'success': False, 'error': res, 'code': 'NOT_FOUND' if code == 404 else 'FORBIDDEN'}), code
            from backend.evidence import get_finding_evidence_image
            zoom = request.args.get('zoom', 2.0, type=float)
            png_bytes, error_dict = get_finding_evidence_image(finding_id, zoom=zoom)
            if error_dict:
                status_code = 404 if error_dict.get('code') in ('NOT_FOUND', 'DOCUMENT_NOT_FOUND', 'FILE_NOT_FOUND') else 200
                return jsonify(error_dict), status_code
            return Response(png_bytes, mimetype='image/png')
        except Exception as e:
            app.logger.error(f"Error serving evidence image for finding {finding_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"Failed to render evidence image: {str(e)}"}), 500

    @app.route('/api/documents/<doc_id>/crop', methods=['GET'])
    @login_required
    def api_get_document_crop(doc_id):
        """Extracts a cropped image snippet of a specific region or matched text on a document page, with a highlight outline around the target, suitable for side-by-side comparison (IDOR protected)."""
        try:
            user_id, username, role = _get_auth_context()
            allowed, res, code = check_document_access(doc_id, user_id=user_id, username=username, role=role)
            if not allowed:
                return jsonify({'success': False, 'error': res}), code
            from backend.evidence import get_document_crop
            page_num = request.args.get('page', 1, type=int)
            query = request.args.get('query')
            coords = request.args.get('coords')
            zoom = request.args.get('zoom', 2.0, type=float)
            png_bytes, error_dict = get_document_crop(doc_id, page_number=page_num, text_query=query, coordinates=coords, zoom=zoom)
            if error_dict:
                status_code = 404 if error_dict.get('code') in ('DOCUMENT_NOT_FOUND', 'FILE_NOT_FOUND') else 400
                return jsonify(error_dict), status_code
            return Response(png_bytes, mimetype='image/png')
        except Exception as e:
            app.logger.error(f"Error serving crop for document {doc_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"Failed to render crop: {str(e)}"}), 500

    @app.route('/api/documents/<doc_id>/pages/<int:page_num>/overlay', methods=['GET'])
    @login_required
    def api_get_document_page_overlay(doc_id, page_num):
        """
        Renders a document page with all forensic findings on that page highlighted (IDOR protected).
        """
        try:
            user_id, username, role = _get_auth_context()
            allowed, res, code = check_document_access(doc_id, user_id=user_id, username=username, role=role)
            if not allowed:
                return jsonify({'success': False, 'error': res}), code
            from backend.evidence import get_document_page_overlay
            zoom = request.args.get('zoom', 2.0, type=float)
            png_bytes, error_dict = get_document_page_overlay(doc_id, page_number=page_num, zoom=zoom)
            if error_dict:
                status_code = 404 if error_dict.get('code') in ('DOCUMENT_NOT_FOUND', 'FILE_NOT_FOUND') else 400
                return jsonify(error_dict), status_code
            return Response(png_bytes, mimetype='image/png')
        except Exception as e:
            app.logger.error(f"Error serving page overlay for document {doc_id} page {page_num}: {str(e)}")
            return jsonify({'success': False, 'error': f"Failed to render page overlay: {str(e)}"}), 500

    # ==========================================
    # Phase C: LLM Reasoning Layer Routes
    # ==========================================
    @app.route('/api/system/ai-status', methods=['GET'])
    def api_get_ai_status():
        """
        Reports LLM reasoning engine telemetry without exposing secrets:
        enabled, provider, model, has_api_key, and privacy redaction status.
        """
        try:
            from backend.llm import get_ai_status
            return jsonify(get_ai_status()), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/demo/add', methods=['POST'])
    @login_required
    def api_demo_add():
        """
        Non-destructive alternative: Seeds the showcase demo case CAS-DEMO-2026
        without erasing existing cases, documents, or findings.
        Requires authenticated session when auth is enabled.
        """
        try:
            from tools.reset_demo import seed_demo_case
            res = seed_demo_case(preserve_existing=True)
            return jsonify({
                'success': True,
                'message': 'Demo case CAS-DEMO-2026 added (existing data preserved).',
                'data': res
            }), 200
        except Exception as e:
            app.logger.error(f"Demo add error: {str(e)}")
            return jsonify({'success': False, 'error': f"Failed to add demo data: {str(e)}"}), 500

    @app.route('/api/demo/reset', methods=['POST'])
    @login_required
    def api_demo_reset():
        """
        Phase 3: Resets database and seeds realistic demo case with 3 genuine docs + 1 tampered doc.
        Protected by VEXORA_ALLOW_DEMO_RESET environment setting and requires Admin privileges when auth enabled.
        """
        user_id, username, role = _get_auth_context()
        admin_roles = {'admin', 'system administrator', 'lead investigator', 'supervisor', 'senior forensic specialist'}
        if app.config.get('VEXORA_REQUIRE_AUTH', False) and (not role or role.strip().lower() not in admin_roles):
            return jsonify({'success': False, 'error': 'Administrative privileges required to execute demo reset.'}), 403

        allow_reset = app.config.get('VEXORA_ALLOW_DEMO_RESET', getattr(Config, 'VEXORA_ALLOW_DEMO_RESET', False))

        if not allow_reset:
            return jsonify({
                'success': False,
                'error': 'Demo database wipe and reset is disabled in this environment (VEXORA_ALLOW_DEMO_RESET=false).'
            }), 403

        try:
            from tools.reset_demo import reset_demo_database
            res = reset_demo_database()
            return jsonify({'success': True, 'message': 'Demo dataset successfully reset and seeded.', 'data': res}), 200
        except Exception as e:
            app.logger.error(f"Demo reset error: {str(e)}")
            return jsonify({'success': False, 'error': f"Failed to reset demo data: {str(e)}"}), 500

    @app.route('/api/system/ai-test', methods=['POST'])
    @login_required
    def api_system_ai_test():
        """
        Phase I: Tests live connectivity to configured LLM provider with a minimal prompt.
        Restricted to administrative investigators.
        Never leaks API keys or secrets.
        """
        user_id, username, role = _get_auth_context()
        admin_roles = {'admin', 'system administrator', 'lead investigator', 'supervisor', 'senior forensic specialist'}
        if app.config.get('VEXORA_REQUIRE_AUTH', False) and (not role or role.strip().lower() not in admin_roles):
            return jsonify({'success': False, 'error': 'Administrative privileges required to run system AI tests.'}), 403

        try:
            from backend.llm import test_ai_connection
            result = test_ai_connection()
            return jsonify(result), 200
        except Exception as e:
            from backend.llm import get_model_name
            prov = getattr(Config, 'VEXORA_LLM_PROVIDER', 'gemini')
            return jsonify({
                'ok': False,
                'provider': prov,
                'model': get_model_name(prov),
                'latency_ms': 0.0,
                'error': f"AI test execution failed: {str(e)}",
                'disclaimer': 'AI-assessed, requires human review'
            }), 200

    @app.route('/api/documents/<doc_id>/ai-insights', methods=['GET'])
    @login_required
    def api_get_document_ai_insights(doc_id):
        """
        Phase I: Retrieves stored AI insights (e.g. structured field extractions) for a document (IDOR protected).
        """
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_document_access(doc_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        doc = res

        try:
            from backend.models import get_ai_insights_by_document
            insights = get_ai_insights_by_document(doc_id)
            return jsonify({
                'success': True,
                'document_id': doc_id,
                'count': len(insights),
                'data': insights
            }), 200
        except Exception as e:
            app.logger.error(f"Failed to fetch AI insights for {doc_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"Failed to retrieve AI insights: {str(e)}"}), 500

    @app.route('/api/documents/<doc_id>/ai-extract', methods=['POST'])
    @login_required
    def api_document_ai_extract(doc_id):
        """
        Executes LLM-based structured field extraction with anti-hallucination quote verification (IDOR protected).
        Saves verified fields in ai_insights table. Drops any ungrounded fields.
        """
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_document_access(doc_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        doc = res

        try:
            from backend.llm import extract_fields_llm
            text = doc.get('extracted_text')
            if not text:
                try:
                    from backend.extractor import extract_document_content
                    ext_res = extract_document_content(doc['file_path'])
                    text = ext_res.get('text', '')
                except Exception:
                    text = ""

            if not text:
                return jsonify({'success': False, 'error': 'No extractable text found in document.'}), 400

            user = username or 'Lead Investigator'
            result = extract_fields_llm(text, doc_type=doc.get('category', 'Document'), document_id=doc_id, user=user)
            if result is None:
                return jsonify({
                    'success': False,
                    'message': 'AI reasoning service unavailable or disabled. Verify VEXORA_LLM_API_KEY and ENABLE_LLM.',
                    'disclaimer': 'AI-assessed, requires human review'
                }), 200

            return jsonify(result), 200
        except Exception as e:
            app.logger.error(f"AI extraction error for {doc_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"AI extraction failed: {str(e)}"}), 500

    @app.route('/api/findings/<finding_id>/explain', methods=['POST'])
    @login_required
    def api_explain_finding(finding_id):
        """
        Generates a 2-4 sentence plain-language explanation of why this finding warrants review (IDOR protected),
        identifying plausible innocent alternative hypotheses and next verification steps.
        """
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_finding_access(finding_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        finding = res

        try:
            nearby_text = ""
            doc_id = finding.get('document_id')
            if doc_id:
                doc = get_document_by_id(doc_id)
                if doc:
                    nearby_text = doc.get('extracted_text') or ""

            from backend.llm import explain_finding
            user = username or 'Lead Investigator'
            result = explain_finding(finding, nearby_text=nearby_text, document_id=doc_id, user=user)
            from backend.explainability import format_explainable_finding, get_status_badge
            fallback = format_explainable_finding(finding)
            status_badge = get_status_badge(finding)
            if result is None:
                return jsonify({
                    'success': False,
                    'message': 'AI explanation unavailable or disabled. Verify VEXORA_LLM_API_KEY and ENABLE_LLM.',
                    'finding_id': finding_id,
                    'disclaimer': 'AI-assessed, requires human review',
                    'fallback': fallback,
                    'status_badge': status_badge,
                    'structured_card': fallback
                }), 200

            result['status_badge'] = status_badge
            result['structured_card'] = {
                **fallback,
                'why_it_matters': result.get('explanation', fallback['why_it_matters']),
                'verification_step': result.get('next_verification_step', fallback['verification_step'])
            }
            return jsonify({'success': True, **result}), 200
        except Exception as e:
            app.logger.error(f"AI explain error for {finding_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"AI explanation failed: {str(e)}"}), 500

    @app.route('/api/cases/<case_id>/ai-crosscheck', methods=['POST'])
    @login_required
    def api_case_ai_crosscheck(case_id):
        """
        Executes multi-document contextual cross-examination to identify logical,
        chronological, and arithmetic inconsistencies across case records (IDOR protected).
        """
        user_id, username, role = _get_auth_context()
        allowed, res, code = check_case_access(case_id, user_id=user_id, username=username, role=role)
        if not allowed:
            return jsonify({'success': False, 'error': res}), code
        case = res

        try:
            docs = get_all_documents(case_id=case_id)
            if not docs:
                return jsonify({'success': False, 'error': f"Case '{case_id}' has no uploaded documents."}), 400

            from backend.llm import contextual_crosscheck
            user = session.get('username', 'Lead Investigator')
            findings = contextual_crosscheck(docs, case_id=case_id, user=user)

            return jsonify({
                'success': True,
                'case_id': case_id,
                'count': len(findings),
                'findings': findings,
                'disclaimer': 'AI-assessed, requires human review'
            }), 200
        except Exception as e:
            app.logger.error(f"AI crosscheck error for {case_id}: {str(e)}")
            return jsonify({'success': False, 'error': f"AI crosscheck failed: {str(e)}"}), 500

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
    try:
        from backend.banner import print_startup_banner
        print_startup_banner(port=port, app_instance=app)
    except Exception:
        print(f"[*] Starting VEXORA Backend & API Server on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
