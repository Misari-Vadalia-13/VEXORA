-- VEXORA SQLite Database Schema
-- Defines core relational tables for Users, Cases, Documents, Findings, and Audit Trail

-- 1. Users Table (Forensic Analysts & System Investigators)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Forensic Analyst',
    badge_number TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Investigation Cases Table
CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    type TEXT NOT NULL,
    priority TEXT NOT NULL CHECK(priority IN ('Critical', 'High', 'Medium', 'Low')),
    status TEXT NOT NULL CHECK(status IN ('Active', 'In Review', 'Pending', 'Archived', 'Solved')),
    investigator TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Ingested Documents Table
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    case_id TEXT,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_path TEXT,
    file_hash TEXT,
    category TEXT DEFAULT 'Uncategorized',
    classification_confidence REAL DEFAULT 0.0,
    status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Processing', 'Analyzed', 'Flagged', 'Clean')),
    uploaded_by TEXT DEFAULT 'Lead Investigator',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL
);

-- 4. Forensic Findings & Evidence Table
CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    document_id TEXT,
    title TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('Critical', 'High', 'Medium', 'Low', 'Info')),
    category TEXT NOT NULL,
    description TEXT,
    confidence REAL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'Unresolved' CHECK(status IN ('Unresolved', 'Verified', 'Dismissed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
);

-- 5. Audit Trail & Activity Log Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details TEXT,
    user TEXT DEFAULT 'System',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for optimal querying performance
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_priority ON cases(priority);
CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents(case_id);
CREATE INDEX IF NOT EXISTS idx_findings_case_id ON findings(case_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
