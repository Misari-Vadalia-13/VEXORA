"""
VEXORA — Database Management Module
Handles SQLite connection lifecycle, schema initialization,
seed data population, and parameterized SQL query execution.
"""

import sqlite3
import os
from pathlib import Path
from werkzeug.security import generate_password_hash
from backend.config import Config, SCHEMA_PATH, DATABASE_PATH

_last_active_db = None

def get_db(db_path=None):
    """
    Establishes and returns a connection to the SQLite database.
    Configures sqlite3.Row for dictionary-like column access and enables foreign keys.
    """
    global _last_active_db
    if db_path is not None:
        path = db_path
        _last_active_db = db_path
    else:
        try:
            from flask import current_app, has_app_context
            if has_app_context() and current_app and current_app.config.get('DATABASE'):
                path = current_app.config.get('DATABASE')
                _last_active_db = path
            else:
                path = _last_active_db or Config.DATABASE
        except Exception:
            path = _last_active_db or Config.DATABASE
    
    # Ensure the parent directory exists if using a filesystem path
    if path != ':memory:':
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path=None):
    """
    Executes schema.sql to create all tables and indexes.
    Safe to call multiple times because of IF NOT EXISTS constraints.
    """
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    conn = get_db(db_path)
    try:
        conn.executescript(schema_sql)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(documents)")
        cols = [row['name'] for row in cursor.fetchall()]
        if 'file_hash' not in cols and len(cols) > 0:
            cursor.execute("ALTER TABLE documents ADD COLUMN file_hash TEXT")
        if 'extracted_text' not in cols and len(cols) > 0:
            cursor.execute("ALTER TABLE documents ADD COLUMN extracted_text TEXT")
        if 'extracted_data' not in cols and len(cols) > 0:
            cursor.execute("ALTER TABLE documents ADD COLUMN extracted_data TEXT")
        if 'extraction_mode' not in cols and len(cols) > 0:
            cursor.execute("ALTER TABLE documents ADD COLUMN extraction_mode TEXT DEFAULT NULL")

        cursor.execute("PRAGMA table_info(findings)")
        f_cols = [row['name'] for row in cursor.fetchall()]
        if 'page_number' not in f_cols and len(f_cols) > 0:
            cursor.execute("ALTER TABLE findings ADD COLUMN page_number INTEGER DEFAULT 1")
        if 'coordinates' not in f_cols and len(f_cols) > 0:
            cursor.execute("ALTER TABLE findings ADD COLUMN coordinates TEXT")
        if 'rule_id' not in f_cols and len(f_cols) > 0:
            cursor.execute("ALTER TABLE findings ADD COLUMN rule_id TEXT")
        if 'evidence' not in f_cols and len(f_cols) > 0:
            cursor.execute("ALTER TABLE findings ADD COLUMN evidence TEXT")
        if 'evidence_class' not in f_cols and len(f_cols) > 0:
            cursor.execute("ALTER TABLE findings ADD COLUMN evidence_class TEXT DEFAULT NULL")

        # Phase C: Add ai_insights table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_insights (
                id TEXT PRIMARY KEY,
                document_id TEXT,
                insight_type TEXT,
                data TEXT,
                model_provider TEXT,
                created_at TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

        # Phase E: Extracted Entities table with nullable confidence column
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                document_id TEXT,
                case_id TEXT,
                entity_type TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence TEXT,
                page_number INTEGER DEFAULT 1,
                coordinates TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("PRAGMA table_info(entities)")
        e_cols = [row['name'] for row in cursor.fetchall()]
        if 'confidence' not in e_cols and len(e_cols) > 0:
            cursor.execute("ALTER TABLE entities ADD COLUMN confidence TEXT DEFAULT NULL")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_document ON entities(document_id)")
        conn.commit()
    finally:
        conn.close()

def seed_data(db_path=None):
    """
    Seeds baseline demonstration data (analyst user, cases, documents, findings, audit trail)
    if the database tables are currently empty.
    """
    conn = get_db(db_path)
    cursor = conn.cursor()

    try:
        # Check if users already exist
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            # Create primary forensic investigator account
            hashed_pw = generate_password_hash("Vexora@2026", method="scrypt")
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, role, badge_number)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("alex.turner", "turner@vexora.internal", hashed_pw, "Senior Forensic Specialist", "VEX-782")
            )

        # Check if cases already exist
        cursor.execute("SELECT COUNT(*) FROM cases")
        if cursor.fetchone()[0] == 0:
            initial_cases = [
                (
                    "CAS-2026-0891",
                    "Apex Global Offshore Procurement Audit",
                    "Financial Fraud",
                    "Critical",
                    "Active",
                    "Dr. Alex Turner",
                    "Investigation into $4.8M cross-border vendor billing anomalies, font inconsistencies, and altered SWIFT confirmations.",
                    "2026-10-18 09:14:22",
                    "2026-10-31 16:42:00"
                ),
                (
                    "CAS-2026-0888",
                    "Veridian Tech Acquisition Due Diligence",
                    "Contract Tampering",
                    "High",
                    "In Review",
                    "Elena Rostova",
                    "Forensic inspection of amended IP licensing schedules and retroactive digital signatures.",
                    "2026-10-12 11:20:00",
                    "2026-10-29 14:15:10"
                ),
                (
                    "CAS-2026-0875",
                    "Solari Energy Subsidies Verification",
                    "Compliance",
                    "Medium",
                    "Pending",
                    "Marcus Vance",
                    "Validation of governmental energy rebate claims and stamped customs declarations.",
                    "2026-10-05 14:02:18",
                    "2026-10-22 10:05:00"
                ),
                (
                    "CAS-2026-0842",
                    "Kroll Logistics Export Manifest Discrepancy",
                    "Export Control",
                    "Low",
                    "Solved",
                    "Dr. Alex Turner",
                    "Resolved investigation regarding duplicate bill of lading numbers and tariff codes.",
                    "2026-09-20 08:30:00",
                    "2026-10-15 17:00:00"
                )
            ]
            cursor.executemany(
                """
                INSERT INTO cases (id, title, type, priority, status, investigator, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                initial_cases
            )

        # Check if documents already exist
        cursor.execute("SELECT COUNT(*) FROM documents")
        if cursor.fetchone()[0] == 0:
            initial_documents = [
                (
                    "DOC-2026-0042",
                    "CAS-2026-0891",
                    "Apex_Invoice_INV-9921_Final.pdf",
                    "pdf",
                    4248576,
                    "uploads/Apex_Invoice_INV-9921_Final.pdf",
                    "Invoice",
                    98.4,
                    "Flagged",
                    "Dr. Alex Turner",
                    "2026-10-18 10:05:12"
                ),
                (
                    "DOC-2026-0043",
                    "CAS-2026-0891",
                    "SWIFT_Confirmation_Apex_Wire.pdf",
                    "pdf",
                    1843200,
                    "uploads/SWIFT_Confirmation_Apex_Wire.pdf",
                    "Bank Statement",
                    94.1,
                    "Flagged",
                    "Dr. Alex Turner",
                    "2026-10-18 10:12:44"
                ),
                (
                    "DOC-2026-0044",
                    "CAS-2026-0888",
                    "Veridian_IP_Agreement_Rev4.pdf",
                    "pdf",
                    6291456,
                    "uploads/Veridian_IP_Agreement_Rev4.pdf",
                    "Contract",
                    99.0,
                    "Processing",
                    "Elena Rostova",
                    "2026-10-25 15:30:00"
                ),
                (
                    "DOC-2026-0045",
                    "CAS-2026-0875",
                    "Customs_Clearance_Stamp_Scan.png",
                    "png",
                    3145728,
                    "uploads/Customs_Clearance_Stamp_Scan.png",
                    "Customs Declaration",
                    91.5,
                    "Clean",
                    "Marcus Vance",
                    "2026-10-26 09:44:00"
                )
            ]
            cursor.executemany(
                """
                INSERT INTO documents (id, case_id, filename, file_type, file_size, file_path, category, classification_confidence, status, uploaded_by, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                initial_documents
            )

        # Check if findings already exist
        cursor.execute("SELECT COUNT(*) FROM findings")
        if cursor.fetchone()[0] == 0:
            initial_findings = [
                (
                    "FND-2026-001",
                    "CAS-2026-0891",
                    "DOC-2026-0042",
                    "Dual-DPI Font Kerning Mismatch Detected",
                    "Critical",
                    "Font Anomaly",
                    "Subtotal line rendered in Helvetica Neue 300 DPI overlaid on 150 DPI scanned invoice background.",
                    97.8,
                    "Unresolved",
                    "2026-10-18 10:20:00"
                ),
                (
                    "FND-2026-002",
                    "CAS-2026-0891",
                    "DOC-2026-0042",
                    "Metadata Creation Date Precedes Vendor Registration",
                    "High",
                    "Metadata Tampering",
                    "PDF ModDate (2024-03-12) occurs 6 months prior to CreationDate (2024-09-18).",
                    99.2,
                    "Unresolved",
                    "2026-10-18 10:22:15"
                ),
                (
                    "FND-2026-003",
                    "CAS-2026-0891",
                    "DOC-2026-0043",
                    "Inter-Bank Clearing Code Checksum Failure",
                    "Critical",
                    "Check Digit Error",
                    "Routing code check digits fail ISO-9362 international specification algorithm.",
                    94.5,
                    "Unresolved",
                    "2026-10-18 10:35:00"
                ),
                (
                    "FND-2026-004",
                    "CAS-2026-0888",
                    "DOC-2026-0044",
                    "Digital Signature Timestamp Drift (>48 Hours)",
                    "Medium",
                    "Signature Anomaly",
                    "Cryptographic signing certificate timestamp deviates from internal PDF timestamp by 51.4 hours.",
                    88.0,
                    "Unresolved",
                    "2026-10-25 16:10:00"
                )
            ]
            cursor.executemany(
                """
                INSERT INTO findings (id, case_id, document_id, title, severity, category, description, confidence, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                initial_findings
            )

        # Check if audit logs already exist
        cursor.execute("SELECT COUNT(*) FROM audit_logs")
        if cursor.fetchone()[0] == 0:
            initial_logs = [
                ("SYSTEM_INIT", "system", "SYS-001", "VEXORA forensic relational database initialized successfully.", "System"),
                ("USER_LOGIN", "auth", "USR-001", "Forensic investigator alex.turner logged in from terminal session.", "alex.turner"),
                ("CASE_CREATED", "case", "CAS-2026-0891", "Investigation case 'Apex Global Offshore Procurement Audit' opened.", "alex.turner"),
                ("DOCUMENT_UPLOAD", "document", "DOC-2026-0042", "Document 'Apex_Invoice_INV-9921_Final.pdf' uploaded and registered.", "alex.turner"),
                ("FINDING_FLAGGED", "finding", "FND-2026-001", "Critical font mismatch anomaly detected in subtotal block.", "VEXORA-Engine")
            ]
            cursor.executemany(
                """
                INSERT INTO audit_logs (action, entity_type, entity_id, details, user)
                VALUES (?, ?, ?, ?, ?)
                """,
                initial_logs
            )

        conn.commit()
    finally:
        conn.close()

def query_db(query, args=(), one=False, db_path=None):
    """
    Executes a SELECT query with parameterized arguments to prevent SQL injection.
    Returns list of dicts (or single dict if one=True).
    """
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(query, args)
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        return (result[0] if result else None) if one else result
    finally:
        conn.close()

def execute_db(query, args=(), db_path=None):
    """
    Executes an INSERT, UPDATE, or DELETE query with parameterized arguments.
    Returns the cursor's lastrowid.
    """
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(query, args)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
