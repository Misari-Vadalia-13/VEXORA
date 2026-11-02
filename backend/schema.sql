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
    extracted_text TEXT,
    extracted_data TEXT,
    extraction_mode TEXT DEFAULT NULL,
    uploaded_by TEXT DEFAULT 'Lead Investigator',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL
);

-- 4. Forensic Findings & Evidence Table
CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    case_id TEXT,
    document_id TEXT,
    title TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('Critical', 'High', 'Medium', 'Low', 'Info')),
    category TEXT NOT NULL,
    description TEXT,
    confidence REAL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'Unresolved' CHECK(status IN ('Unresolved', 'Verified', 'Dismissed')),
    page_number INTEGER DEFAULT 1,
    coordinates TEXT,
    rule_id TEXT,
    evidence TEXT,
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

-- 6. Cross-Document Comparisons Table
CREATE TABLE IF NOT EXISTS comparisons (
    id TEXT PRIMARY KEY,
    case_id TEXT,
    doc_a_id TEXT NOT NULL,
    doc_b_id TEXT NOT NULL,
    discrepancies_count INTEGER DEFAULT 0,
    matches_count INTEGER DEFAULT 0,
    results_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (doc_a_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (doc_b_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- 7. Investigation Reports & Dossiers Table
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_format TEXT NOT NULL DEFAULT 'pdf',
    file_size INTEGER DEFAULT 0,
    generated_by TEXT DEFAULT 'Lead Investigator',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);

-- 8. AI Insights Table (Phase C)
CREATE TABLE IF NOT EXISTS ai_insights (
    id TEXT PRIMARY KEY,
    document_id TEXT,
    insight_type TEXT,
    data TEXT,
    model_provider TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Indexes for optimal querying performance
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_priority ON cases(priority);
CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents(case_id);
CREATE INDEX IF NOT EXISTS idx_findings_case_id ON findings(case_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_comparisons_case_id ON comparisons(case_id);
CREATE INDEX IF NOT EXISTS idx_reports_case_id ON reports(case_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_ai_insights_doc ON ai_insights(document_id);

-- 9. Extracted Entities Table (Phase E)
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
);
CREATE INDEX IF NOT EXISTS idx_entities_document ON entities(document_id);

