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

    return {
        'username': username.strip().lower(),
        'email': email.strip().lower(),
        'password': password,
        'role': data.get('role', 'Forensic Analyst').strip(),
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

def save_document_extraction(doc_id, extraction_data, user="System"):
    """Saves structured extraction results and full text into SQLite."""
    doc = query_db("SELECT * FROM documents WHERE id = ?", (doc_id,), one=True)
    if not doc:
        return None

    full_text = extraction_data.get('full_text', '')
    serialized_json = json.dumps(extraction_data)

    execute_db(
        """
        UPDATE documents
        SET extracted_text = ?, extracted_data = ?, status = 'Analyzed'
        WHERE id = ?
        """,
        (full_text, serialized_json, doc_id)
    )

    page_count = extraction_data.get('page_count', 1)
    word_count = extraction_data.get('total_words', 0)
    log_audit("DOCUMENT_EXTRACTED", "document", doc_id, f"Extracted {page_count} page(s), {word_count} word(s).", user)
    return get_document_by_id(doc_id)

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
    return query_db(query, args)

def create_finding(data, user="System"):
    """Adds a new forensic finding record."""
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

    execute_db(
        """
        INSERT INTO findings (id, case_id, document_id, title, severity, category, description, confidence, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            finding_id,
            data['case_id'],
            data.get('document_id'),
            data['title'],
            data.get('severity', 'High'),
            data.get('category', 'Forensic Anomaly'),
            data.get('description', ''),
            float(data.get('confidence', 0.0)),
            data.get('status', 'Unresolved'),
            now
        )
    )

    log_audit("FINDING_FLAGGED", "finding", finding_id, f"Anomaly flagged: {data['title']}", user)
    return query_db("SELECT * FROM findings WHERE id = ?", (finding_id,), one=True)

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

def get_audit_logs(limit=50):
    """Retrieves recent audit logs in descending chronological order."""
    return query_db("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
