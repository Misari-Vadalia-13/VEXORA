import threading
from functools import wraps

_model_write_lock = threading.Lock()

def _synchronized_model(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        with _model_write_lock:
            return fn(*args, **kwargs)
    return wrapper
"""
VEXORA — Models & Business Logic Layer
Provides data access methods, parameterized query helpers,
and strict input validation for Cases, Documents, Findings, and Audit Logs.
"""

import re
import json
from datetime import datetime
from backend.database import query_db, execute_db

# Allowed enum values
VALID_PRIORITIES = {'Critical', 'High', 'Medium', 'Low'}
VALID_CASE_STATUSES = {'Active', 'In Review', 'Pending', 'Archived', 'Solved'}
VALID_DOCUMENT_STATUSES = {'Pending', 'Processing', 'Analyzed', 'Flagged', 'Clean'}
VALID_FINDING_SEVERITIES = {'Critical', 'High', 'Medium', 'Low', 'Info'}
VALID_FINDING_STATUSES = {'Unresolved', 'Verified', 'Dismissed'}

class ValidationError(Exception):
    """Raised when incoming client payload fails validation criteria."""
    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field

# ==========================================
# 1. Input Validation Helpers
# ==========================================

def validate_case_data(data):
    """
    Validates payload for creating or updating an investigation case.
    Raises ValidationError if invalid.
    """
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a valid JSON object.")

    title = data.get('title')
    if not title or not isinstance(title, str) or not title.strip():
        raise ValidationError("Case title is required and cannot be empty.", field="title")
    if len(title.strip()) < 3 or len(title.strip()) > 200:
        raise ValidationError("Case title must be between 3 and 200 characters.", field="title")

    case_type = data.get('type') or data.get('case_type')
    if not case_type or not isinstance(case_type, str) or not case_type.strip():
        raise ValidationError("Case type is required.", field="type")

    priority = data.get('priority', 'Medium')
    if priority not in VALID_PRIORITIES:
        raise ValidationError(f"Invalid priority '{priority}'. Must be one of: {', '.join(sorted(VALID_PRIORITIES))}.", field="priority")

    status = data.get('status', 'Active')
    if status not in VALID_CASE_STATUSES:
        raise ValidationError(f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_CASE_STATUSES))}.", field="status")

    investigator = data.get('investigator', 'Lead Investigator')
    if not isinstance(investigator, str) or not investigator.strip():
        investigator = 'Lead Investigator'

    return {
        'title': title.strip(),
        'type': case_type.strip(),
        'priority': priority,
        'status': status,
        'investigator': investigator.strip(),
        'description': (data.get('description') or '').strip()
    }

def validate_user_registration(data):
    """Validates user signup / registration data."""
    if not isinstance(data, dict):
        raise ValidationError("Request payload must be a JSON object.")

    username = data.get('username')
    if not username or not isinstance(username, str) or len(username.strip()) < 3:
        raise ValidationError("Username must be at least 3 characters long.", field="username")

    email = data.get('email')
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not email or not re.match(email_regex, email.strip()):
        raise ValidationError("A valid email address is required.", field="email")

    password = data.get('password')
    if not password or len(password) < 6:
        raise ValidationError("Password must be at least 6 characters long.", field="password")

    # Role escalation security guard: prevent self-assigning administrative privileges
    requested_role = (data.get('role') or 'Forensic Analyst').strip()
    disallowed_admin_roles = {'admin', 'administrator', 'system administrator', 'superuser', 'root'}
    if requested_role.lower() in disallowed_admin_roles:
        raise ValidationError("Administrative roles cannot be self-assigned during registration.", field="role")

    return {
        'username': username.strip().lower(),
        'email': email.strip().lower(),
        'password': password,
        'role': requested_role,
        'badge_number': data.get('badge_number', 'VEX-000').strip()
    }

# ==========================================
# 2. Case Repository & Operations
# ==========================================

def generate_case_id():
    """Generates a sequential human-readable case ID e.g. CAS-2026-0892."""
    year = datetime.now().year
    row = query_db(
        "SELECT id FROM cases WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
        (f"CAS-{year}-%",),
        one=True
    )
    if row and row['id']:
        try:
            parts = row['id'].split('-')
            last_num = int(parts[-1])
            return f"CAS-{year}-{last_num + 1:04d}"
        except (ValueError, IndexError):
            pass
    return f"CAS-{year}-0001"

def get_all_cases(priority=None, status=None, search=None):
    """Retrieves all cases with optional filtering."""
    query = "SELECT * FROM cases WHERE 1=1"
    args = []

    if priority and priority in VALID_PRIORITIES:
        query += " AND priority = ?"
        args.append(priority)

    if status and status in VALID_CASE_STATUSES:
        query += " AND status = ?"
        args.append(status)

    if search and search.strip():
        query += " AND (title LIKE ? OR id LIKE ? OR investigator LIKE ?)"
        term = f"%{search.strip()}%"
        args.extend([term, term, term])

    query += " ORDER BY created_at DESC"
    return query_db(query, args)

def get_case_by_id(case_id):
    """Retrieves a single case by its ID along with associated documents and findings."""
    case = query_db("SELECT * FROM cases WHERE id = ?", (case_id,), one=True)
    if not case:
        return None

    documents = query_db("SELECT * FROM documents WHERE case_id = ? ORDER BY uploaded_at DESC", (case_id,))
    findings = query_db("SELECT * FROM findings WHERE case_id = ? ORDER BY created_at DESC", (case_id,))

    case['documents'] = documents
    case['findings'] = findings
    case['document_count'] = len(documents)
    case['findings_count'] = len(findings)
    return case

@_synchronized_model
def create_case(validated_data, custom_id=None, user="System"):
    """Inserts a new investigation case into SQLite with audit logging."""
    case_id = custom_id or generate_case_id()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    execute_db(
        """
        INSERT INTO cases (id, title, type, priority, status, investigator, description, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case_id,
            validated_data['title'],
            validated_data['type'],
            validated_data['priority'],
            validated_data['status'],
            validated_data['investigator'],
            validated_data['description'],
            now,
            now
        )
    )

    log_audit("CASE_CREATED", "case", case_id, f"Case '{validated_data['title']}' created.", user)
    return get_case_by_id(case_id)

def update_case(case_id, update_data, user="System"):
    """Updates an existing case in SQLite with audit logging."""
    existing = query_db("SELECT * FROM cases WHERE id = ?", (case_id,), one=True)
    if not existing:
        return None

    # Merge existing with updates
    merged = {
        'title': update_data.get('title', existing['title']),
        'type': update_data.get('type', existing['type']),
        'priority': update_data.get('priority', existing['priority']),
        'status': update_data.get('status', existing['status']),
        'investigator': update_data.get('investigator', existing['investigator']),
        'description': update_data.get('description', existing['description'])
    }
    validated = validate_case_data(merged)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    execute_db(
        """
        UPDATE cases
        SET title = ?, type = ?, priority = ?, status = ?, investigator = ?, description = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            validated['title'],
            validated['type'],
            validated['priority'],
            validated['status'],
            validated['investigator'],
            validated['description'],
            now,
            case_id
        )
    )

    log_audit("CASE_UPDATED", "case", case_id, f"Case updated with status: {validated['status']}, priority: {validated['priority']}", user)
    return get_case_by_id(case_id)

def delete_case(case_id, user="System"):
    """Deletes or archives a case."""
    existing = query_db("SELECT * FROM cases WHERE id = ?", (case_id,), one=True)
    if not existing:
        return False

    execute_db("DELETE FROM cases WHERE id = ?", (case_id,))
    log_audit("CASE_DELETED", "case", case_id, f"Case '{existing['title']}' deleted from system.", user)
    return True

# ==========================================
# 3. Document Repository & Operations
# ==========================================

def generate_document_id():
    """Generates unique document identifier e.g. DOC-2026-0046."""
    year = datetime.now().year
    row = query_db(
        "SELECT id FROM documents WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
        (f"DOC-{year}-%",),
        one=True
    )
    if row and row['id']:
        try:
            parts = row['id'].split('-')
            last_num = int(parts[-1])
            return f"DOC-{year}-{last_num + 1:04d}"
        except (ValueError, IndexError):
            pass
    return f"DOC-{year}-0001"

def get_all_documents(case_id=None, category=None):
    """Retrieves all registered documents with optional filters."""
    query = """
        SELECT d.*, c.title AS case_title 
        FROM documents d 
        LEFT JOIN cases c ON d.case_id = c.id 
        WHERE 1=1
    """
    args = []

    if case_id:
        query += " AND d.case_id = ?"
        args.append(case_id)

    if category and category != 'all':
        query += " AND d.category = ?"
        args.append(category)

    query += " ORDER BY d.uploaded_at DESC"
    return query_db(query, args)

def get_document_by_id(doc_id):
    """Retrieves document details along with associated findings."""
    doc = query_db("SELECT * FROM documents WHERE id = ?", (doc_id,), one=True)
    if not doc:
        return None
    findings = query_db("SELECT * FROM findings WHERE document_id = ? ORDER BY created_at DESC", (doc_id,))
    doc['findings'] = findings
    return doc

@_synchronized_model
def create_document(data, user="System"):
    """Registers document metadata into the database."""
    doc_id = data.get('id') or generate_document_id()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    execute_db(
        """
        INSERT INTO documents (id, case_id, filename, file_type, file_size, file_path, file_hash, category, classification_confidence, status, uploaded_by, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            doc_id,
            data.get('case_id'),
            data['filename'],
            data.get('file_type', 'unknown').lower(),
            int(data.get('file_size', 0)),
            data.get('file_path', ''),
            data.get('file_hash', ''),
            data.get('category', 'Uncategorized'),
            float(data.get('classification_confidence', 0.0)),
            data.get('status', 'Pending'),
            data.get('uploaded_by', user),
            now
        )
    )

    log_audit("DOCUMENT_UPLOAD", "document", doc_id, f"Document '{data['filename']}' registered.", user)
    return get_document_by_id(doc_id)

def delete_document(doc_id, user="System"):
    """Deletes a document record from SQLite."""
    doc = query_db("SELECT * FROM documents WHERE id = ?", (doc_id,), one=True)
    if not doc:
        return False
    execute_db("DELETE FROM documents WHERE id = ?", (doc_id,))
    log_audit("DOCUMENT_DELETED", "document", doc_id, f"Document '{doc['filename']}' deleted from system.", user)
    return True

def update_document_status(doc_id, new_status, user="System"):
    """Updates document status in SQLite and logs audit trail."""
    if new_status not in VALID_DOCUMENT_STATUSES:
        raise ValidationError(f"Invalid document status '{new_status}'.")
    execute_db("UPDATE documents SET status = ? WHERE id = ?", (new_status, doc_id))
    log_audit("DOCUMENT_STATUS_UPDATED", "document", doc_id, f"Status updated to: {new_status}", user)
    return get_document_by_id(doc_id)

def update_document_category(doc_id, category, confidence=90.0, user="System"):
    """Updates document category and classification confidence in SQLite."""
    execute_db(
        "UPDATE documents SET category = ?, classification_confidence = ? WHERE id = ?",
        (category, confidence, doc_id)
    )
    log_audit("DOCUMENT_CLASSIFIED", "document", doc_id, f"Category refined to '{category}' (confidence: {confidence}%)", user)
    return get_document_by_id(doc_id)

def save_document_extraction(doc_id, extraction_data, user="System"):
    """Saves structured extraction results and full text into SQLite."""
    doc = query_db("SELECT * FROM documents WHERE id = ?", (doc_id,), one=True)
    if not doc:
        return None

    full_text = extraction_data.get('full_text', '')
    serialized_json = json.dumps(extraction_data)

    extraction_mode = extraction_data.get('extraction_mode')
    if not extraction_mode:
        if doc.get('file_type') == 'pdf':
            extraction_mode = 'digital_pdf'
        else:
            extraction_mode = 'simulated_fallback'

    try:
        execute_db(
            """
            UPDATE documents
            SET extracted_text = ?, extracted_data = ?, extraction_mode = ?, status = 'Analyzed'
            WHERE id = ?
            """,
            (full_text, serialized_json, extraction_mode, doc_id)
        )
    except Exception:
        execute_db(
            """
            UPDATE documents
            SET extracted_text = ?, extracted_data = ?, status = 'Analyzed'
            WHERE id = ?
            """,
            (full_text, serialized_json, doc_id)
        )

    # Phase E: Save entities into entities table
    save_document_entities(doc_id, doc.get('case_id'), extraction_data.get('entities', {}))

    page_count = extraction_data.get('page_count', 1)
    word_count = extraction_data.get('total_words', 0)
    log_audit("DOCUMENT_EXTRACTED", "document", doc_id, f"Extracted {page_count} page(s), {word_count} word(s). Mode: {extraction_mode}", user)
    return get_document_by_id(doc_id)

def save_document_entities(doc_id, case_id, entities_dict):
    """Additive persistence: inserts extracted entities and confidences into entities table."""
    if not entities_dict or not isinstance(entities_dict, dict):
        return
    try:
        import uuid
        execute_db("DELETE FROM entities WHERE document_id = ?", (doc_id,))
        for entity_type, items in entities_dict.items():
            if isinstance(items, list):
                for item in items:
                    val = item.get('value', '').strip()
                    if not val:
                        continue
                    ent_id = f"ENT-{uuid.uuid4().hex[:12].upper()}"
                    conf = item.get('confidence')
                    conf_str = str(conf) if conf is not None else None
                    page_num = item.get('page', 1)
                    execute_db(
                        """
                        INSERT INTO entities (id, document_id, case_id, entity_type, value, confidence, page_number)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (ent_id, doc_id, case_id, entity_type, val, conf_str, page_num)
                    )
    except Exception:
        pass

def get_entities_by_document(doc_id):
    """Retrieves entity records with confidence values for a document."""
    try:
        return query_db("SELECT * FROM entities WHERE document_id = ? ORDER BY page_number ASC", (doc_id,))
    except Exception:
        return []

def get_document_extraction(doc_id):
    """Retrieves and parses the structured extraction data for a document."""
    doc = query_db("SELECT id, filename, file_type, extracted_text, extracted_data FROM documents WHERE id = ?", (doc_id,), one=True)
    if not doc or not doc['extracted_data']:
        return None
    try:
        return json.loads(doc['extracted_data'])
    except Exception:
        return None

# ==========================================
# 4. Findings & Evidence Operations
# ==========================================

def _hydrate_finding_evidence_class(f):
    """Ensures finding dict contains an objective evidence_class label, falling back to rule map."""
    if not f or not isinstance(f, dict):
        return f
    try:
        from backend.evidence_class import get_evidence_class
        if not f.get('evidence_class'):
            f['evidence_class'] = get_evidence_class(f.get('rule_id'))
    except Exception:
        if not f.get('evidence_class'):
            f['evidence_class'] = 'Observation'
    return f

def get_all_findings(case_id=None, severity=None):
    """Retrieves findings with optional filters."""
    query = """
        SELECT f.*, c.title AS case_title, d.filename AS document_filename
        FROM findings f
        LEFT JOIN cases c ON f.case_id = c.id
        LEFT JOIN documents d ON f.document_id = d.id
        WHERE 1=1
    """
    args = []

    if case_id:
        query += " AND f.case_id = ?"
        args.append(case_id)

    if severity and severity in VALID_FINDING_SEVERITIES:
        query += " AND f.severity = ?"
        args.append(severity)

    query += " ORDER BY f.created_at DESC"
    results = query_db(query, args)
    return [_hydrate_finding_evidence_class(f) for f in results]

def get_finding_by_id(finding_id):
    """Retrieves a single finding by identifier."""
    res = query_db(
        """
        SELECT f.*, c.title AS case_title, d.filename AS document_filename
        FROM findings f
        LEFT JOIN cases c ON f.case_id = c.id
        LEFT JOIN documents d ON f.document_id = d.id
        WHERE f.id = ?
        """,
        (finding_id,),
        one=True
    )
    return _hydrate_finding_evidence_class(res)

def get_findings_by_document(doc_id):
    """Retrieves all forensic findings associated with a specific document."""
    results = query_db(
        """
        SELECT f.*, c.title AS case_title, d.filename AS document_filename
        FROM findings f
        LEFT JOIN cases c ON f.case_id = c.id
        LEFT JOIN documents d ON f.document_id = d.id
        WHERE f.document_id = ?
        ORDER BY f.page_number ASC, f.created_at ASC
        """,
        (doc_id,)
    )
    return [_hydrate_finding_evidence_class(f) for f in results]

@_synchronized_model
def create_finding(data, user="System"):
    """Adds a new forensic finding record with coordinate and rule traceability."""
    year = datetime.now().year
    row = query_db("SELECT id FROM findings WHERE id LIKE ? ORDER BY id DESC LIMIT 1", (f"FND-{year}-%",), one=True)
    if row and row['id']:
        try:
            parts = row['id'].split('-')
            num = int(parts[-1])
            finding_id = f"FND-{year}-{num + 1:03d}"
        except (ValueError, IndexError):
            finding_id = f"FND-{year}-001"
    else:
        finding_id = f"FND-{year}-001"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    coords = data.get('coordinates')
    if isinstance(coords, (list, dict)):
        coords = json.dumps(coords)

    severity = data.get('severity', 'High')
    if severity not in VALID_FINDING_SEVERITIES:
        severity = 'High'

    status = data.get('status', 'Unresolved')
    if status not in VALID_FINDING_STATUSES:
        status = 'Unresolved'

    case_id = data.get('case_id')
    if case_id:
        exists = query_db("SELECT id FROM cases WHERE id = ?", (case_id,), one=True)
        if not exists:
            case_id = None
    if not case_id:
        any_case = query_db("SELECT id FROM cases LIMIT 1", one=True)
        if any_case:
            case_id = any_case['id']

    # Resolve objective evidence class label
    ev_class = data.get('evidence_class')
    try:
        from backend.evidence_class import get_evidence_class
        ev_class = get_evidence_class(data.get('rule_id'), ev_class)
    except Exception:
        ev_class = ev_class or 'Observation'

    try:
        execute_db(
            """
            INSERT INTO findings (
                id, case_id, document_id, title, severity, category, description,
                confidence, status, page_number, coordinates, rule_id, evidence, evidence_class, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                finding_id,
                case_id,
                data.get('document_id'),
                data['title'],
                severity,
                data.get('category', 'Forensic Anomaly'),
                data.get('description', ''),
                float(data.get('confidence', 0.85)),
                status,
                int(data.get('page_number', 1)),
                coords,
                data.get('rule_id'),
                data.get('evidence'),
                ev_class,
                now
            )
        )
    except Exception:
        # Fallback for unmigrated schema
        execute_db(
            """
            INSERT INTO findings (
                id, case_id, document_id, title, severity, category, description,
                confidence, status, page_number, coordinates, rule_id, evidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                finding_id,
                case_id,
                data.get('document_id'),
                data['title'],
                severity,
                data.get('category', 'Forensic Anomaly'),
                data.get('description', ''),
                float(data.get('confidence', 0.85)),
                status,
                int(data.get('page_number', 1)),
                coords,
                data.get('rule_id'),
                data.get('evidence'),
                now
            )
        )

    log_audit("FINDING_FLAGGED", "finding", finding_id, f"Anomaly flagged: {data['title']}", user)
    return get_finding_by_id(finding_id)

def update_finding(finding_id, update_data, user="System"):
    """Updates status or notes for an existing finding."""
    existing = query_db("SELECT * FROM findings WHERE id = ?", (finding_id,), one=True)
    if not existing:
        return None

    new_status = update_data.get('status', existing['status'])
    if new_status not in VALID_FINDING_STATUSES:
        raise ValidationError(f"Invalid status '{new_status}'. Must be one of: {', '.join(sorted(VALID_FINDING_STATUSES))}.")

    execute_db(
        "UPDATE findings SET status = ? WHERE id = ?",
        (new_status, finding_id)
    )
    log_audit("FINDING_UPDATED", "finding", finding_id, f"Finding status updated to: {new_status}", user)
    return get_finding_by_id(finding_id)

def save_document_findings(doc_id, findings_list, user="System"):
    """
    Persists analysis findings for a document. Clears previous automated
    findings for this document to avoid duplication, then updates the document status.
    """
    doc = get_document_by_id(doc_id)
    if not doc:
        return []

    case_id = doc.get('case_id')
    if case_id:
        exists = query_db("SELECT id FROM cases WHERE id = ?", (case_id,), one=True)
        if not exists:
            case_id = None
    if not case_id:
        any_case = query_db("SELECT id FROM cases LIMIT 1", one=True)
        if any_case:
            case_id = any_case['id']

    # Clear prior findings for this document
    execute_db("DELETE FROM findings WHERE document_id = ?", (doc_id,))

    created_records = []
    has_critical = False
    has_high = False

    for item in findings_list:
        payload = dict(item)
        payload['case_id'] = case_id
        payload['document_id'] = doc_id
        rec = create_finding(payload, user=user)
        created_records.append(rec)
        sev = payload.get('severity', 'Low')
        if sev == 'Critical':
            has_critical = True
        elif sev == 'High':
            has_high = True

    # Update document status based on severity of findings
    if has_critical or has_high:
        new_status = 'Flagged'
    elif created_records:
        new_status = 'Analyzed'
    else:
        new_status = 'Clean'

    update_document_status(doc_id, new_status, user=user)
    log_audit("DOCUMENT_ANALYZED", "document", doc_id, f"Saved {len(created_records)} forensic findings (Status: {new_status}).", user)
    return created_records

# ==========================================
# 5. System Statistics & Aggregations
# ==========================================

def get_system_stats():
    """Calculates live KPI metrics for dashboard display."""
    total_cases = query_db("SELECT COUNT(*) AS count FROM cases", one=True)['count']
    active_cases = query_db("SELECT COUNT(*) AS count FROM cases WHERE status = 'Active'", one=True)['count']
    total_documents = query_db("SELECT COUNT(*) AS count FROM documents", one=True)['count']
    flagged_documents = query_db("SELECT COUNT(*) AS count FROM documents WHERE status = 'Flagged'", one=True)['count']
    total_findings = query_db("SELECT COUNT(*) AS count FROM findings", one=True)['count']
    critical_findings = query_db("SELECT COUNT(*) AS count FROM findings WHERE severity = 'Critical'", one=True)['count']

    risk_rate = round((flagged_documents / total_documents * 100), 1) if total_documents > 0 else 0.0

    # Check AI configuration state for live telemetry
    try:
        from backend.config import Config
        from backend.llm import get_model_name
        enabled = bool(getattr(Config, 'ENABLE_LLM', False))
        api_key = bool(getattr(Config, 'VEXORA_LLM_API_KEY', '') or os.environ.get('VEXORA_LLM_API_KEY') or os.environ.get('GEMINI_API_KEY') or os.environ.get('OPENAI_API_KEY'))
        prov = getattr(Config, 'VEXORA_LLM_PROVIDER', 'gemini')
        model = get_model_name(prov)
        ai_enabled = enabled and api_key
    except Exception:
        ai_enabled = False
        prov = 'gemini'
        model = 'gemini-2.5-flash'

    return {
        'total_cases': total_cases,
        'active_cases': active_cases,
        'total_documents': total_documents,
        'flagged_documents': flagged_documents,
        'total_findings': total_findings,
        'critical_findings': critical_findings,
        'high_risk_rate_percent': risk_rate,
        'system_status': 'Operational',
        'database_engine': 'SQLite 3 (Relational)',
        'ai_reasoning_active': ai_enabled,
        'ai_provider': prov,
        'ai_model': model,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# ==========================================
# 6. Audit Trail Logging
# ==========================================

def log_audit(action, entity_type, entity_id, details, user="System"):
    """Inserts an immutable audit record into audit_logs table."""
    try:
        execute_db(
            """
            INSERT INTO audit_logs (action, entity_type, entity_id, details, user)
            VALUES (?, ?, ?, ?, ?)
            """,
            (action, entity_type, entity_id, details, user)
        )
    except Exception as e:
        print(f"[Warning] Failed to log audit event: {e}")

def get_audit_logs(action=None, entity_type=None, user=None, limit=100):
    """
    Retrieves chronological audit logs with optional filtering by action, entity type, and user.
    """
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []

    if action:
        query += " AND action LIKE ?"
        params.append(f"%{action}%")
    if entity_type:
        query += " AND entity_type = ?"
        params.append(entity_type)
    if user:
        query += " AND user LIKE ?"
        params.append(f"%{user}%")

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    return query_db(query, tuple(params))


# ==========================================
# 7. Investigation Reports & Dossiers
# ==========================================

def create_report_record(report_id, case_id, title, file_path, file_format='pdf', file_size=0, user="Lead Investigator"):
    """
    Persists an investigation dossier record in the reports table
    and creates an immutable audit trail entry.
    """
    execute_db(
        """
        INSERT INTO reports (id, case_id, title, file_path, file_format, file_size, generated_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (report_id, case_id, title, file_path, file_format, file_size, user)
    )
    log_audit("REPORT_GENERATED", "report", report_id, f"Generated {file_format.upper()} dossier for case '{case_id}': {title}", user)
    return get_report_by_id(report_id)

def get_report_by_id(report_id):
    """Retrieves a single report by its ID."""
    return query_db("SELECT * FROM reports WHERE id = ?", (report_id,), one=True)

def get_reports_by_case(case_id):
    """Retrieves all reports generated for a specific case."""
    return query_db("SELECT * FROM reports WHERE case_id = ? ORDER BY created_at DESC", (case_id,))

def get_all_reports(limit=50):
    """Retrieves all generated reports across cases in descending order."""
    return query_db("SELECT * FROM reports ORDER BY created_at DESC LIMIT ?", (limit,))


# ==========================================
# 8. AI Insights (Phase C)
# ==========================================

def get_ai_insights_by_document(document_id):
    """Retrieves all AI insight records for a specific document."""
    rows = query_db("SELECT * FROM ai_insights WHERE document_id = ? ORDER BY created_at DESC", (document_id,))
    results = []
    for r in rows:
        item = dict(r)
        if item.get('data') and isinstance(item['data'], str):
            try:
                item['data'] = json.loads(item['data'])
            except Exception:
                pass
        results.append(item)
    return results

def get_ai_insights_by_case(case_id):
    """Retrieves all AI insight records for documents within a specific case."""
    rows = query_db(
        """
        SELECT ai.* FROM ai_insights ai
        JOIN documents d ON ai.document_id = d.id
        WHERE d.case_id = ?
        ORDER BY ai.created_at DESC
        """,
        (case_id,)
    )
    results = []
    for r in rows:
        item = dict(r)
        if item.get('data') and isinstance(item['data'], str):
            try:
                item['data'] = json.loads(item['data'])
            except Exception:
                pass
        results.append(item)
    return results


