"""
VEXORA — Demo Data Reset & Seeding Utility
Resets or seeds the SQLite database with a showcase case:
- 3 Genuine Documents (Invoice, Matching Purchase Order, Bank Statement)
- 1 Tampered Document (Font Shift / Altered Total Invoice)
Performs full extraction, forensic analysis, and cross-document comparison
so the application is 100% demo-ready for live judging immediately.

Safety Features (Part A):
- Automatic pre-wipe backup to backend/backups/vexora_YYYYMMDD_HHMMSS.db (keeping 5 newest)
- Non-destructive alternative seed_demo_case(preserve_existing=True)
"""

import os
import sys
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.config import Config
from backend.database import init_db, execute_db, query_db
from backend.models import create_case, create_document
from backend.extractor import extract_document_content
from backend.analyzer import analyze_document
from backend.comparator import compare_case_documents
from backend.classifier import classify_document

DEMO_DATASET_DIR = BASE_DIR / 'demo_dataset'
UPLOADS_DIR = BASE_DIR / 'uploads'


def backup_database():
    """
    Part A: Safely creates a timestamped copy of the active SQLite database
    in backend/backups/ before any destructive reset operation.
    Retains only the 5 most recent backups.
    """
    try:
        db_path = Path(Config.DATABASE)
        if not db_path.exists():
            return None

        backups_dir = db_path.parent / 'backups'
        backups_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backups_dir / f"vexora_{timestamp}.db"
        shutil.copy2(str(db_path), str(backup_file))
        print(f"[*] Pre-wipe backup created: {backup_file}")

        # Keep only the 5 newest backups
        all_backups = sorted(
            [f for f in backups_dir.glob("vexora_*.db") if f.is_file()],
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        for old_backup in all_backups[5:]:
            try:
                old_backup.unlink()
                print(f"[*] Rotated old backup: {old_backup.name}")
            except Exception as e:
                print(f"[-] Could not delete old backup {old_backup.name}: {e}")

        return str(backup_file)
    except Exception as e:
        print(f"[-] Backup error: {e}")
        return None


def seed_demo_case(preserve_existing=False):
    """
    Seeds the Hero Demonstration Case (CAS-DEMO-2026).
    If preserve_existing is True, does NOT delete any existing cases or documents.
    If preserve_existing is False, backs up the database and clears all tables before seeding.
    """
    case_id = "CAS-DEMO-2026"
    backup_file = None

    if not preserve_existing:
        backup_file = backup_database()
        print("[*] Reinitializing VEXORA database schema...")
        init_db()
        print("[*] Clearing existing records from database...")
        for table in ['findings', 'evidence_traceability', 'comparisons', 'entities', 'ai_insights', 'reports', 'audit_logs', 'documents', 'cases']:
            try:
                execute_db(f"DELETE FROM {table}")
            except Exception:
                pass
    else:
        # Non-destructive: check if demo case already exists
        init_db()
        existing = query_db("SELECT id FROM cases WHERE id = ?", (case_id,))
        if existing:
            print(f"[*] Demo case '{case_id}' already exists in database. Skipping duplicate seed.")
            return {
                'case_id': case_id,
                'already_exists': True,
                'message': f"Demo case '{case_id}' already exists in your workspace. Existing data preserved."
            }

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Ensure sample files exist in demo_dataset
    from tools.make_samples import generate_all_samples as generate_samples
    if not (DEMO_DATASET_DIR / 'genuine_01_invoice.pdf').exists():
        print("[*] Generating benchmark demo dataset...")
        generate_samples()

    # 2. Create the Hero Demo Case
    case_payload = {
        'id': case_id,
        'title': 'Acquisition Financial & Forensic Due Diligence (Apex Global)',
        'type': 'Procurement Fraud & Tampering Audit',
        'priority': 'Critical',
        'status': 'Active',
        'investigator': 'Misari Vadalia',
        'description': (
            'Comprehensive forensic examination of commercial supplier invoices, matching purchase orders, '
            'and banking settlement statements for Apex Global Industries. Involves cross-checking reported '
            'amounts against verified accounting ledger entries.'
        )
    }

    # Direct database insertion to enforce exact ID
    execute_db(
        """
        INSERT OR REPLACE INTO cases (id, title, type, priority, status, investigator, description, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            case_payload['id'],
            case_payload['title'],
            case_payload['type'],
            case_payload['priority'],
            case_payload['status'],
            case_payload['investigator'],
            case_payload['description']
        )
    )

    demo_files = [
        # 3 Genuine Documents
        {
            'src': 'genuine_01_invoice.pdf',
            'doc_id': 'DOC-2026-DEMO-01',
            'filename': 'Invoice_INV-2026-001_Apex.pdf',
            'category': 'Invoice',
            'is_tampered': False
        },
        {
            'src': 'genuine_01_matching_po.pdf',
            'doc_id': 'DOC-2026-DEMO-02',
            'filename': 'Purchase_Order_PO-2026-001_Apex.pdf',
            'category': 'Purchase Order',
            'is_tampered': False
        },
        {
            'src': 'genuine_03_bank_statement.pdf',
            'doc_id': 'DOC-2026-DEMO-03',
            'filename': 'Bank_Statement_Jan2026_Apex.pdf',
            'category': 'Bank Statement',
            'is_tampered': False
        },
        # 1 Tampered Document
        {
            'src': 'tampered_01_font_shift.pdf',
            'doc_id': 'DOC-2026-DEMO-04',
            'filename': 'Tampered_Invoice_INV-2026-0091.pdf',
            'category': 'Invoice',
            'is_tampered': True
        }
    ]

    print(f"[*] Ingesting and analyzing {len(demo_files)} showcase documents...")
    ingested_docs = []

    for item in demo_files:
        src_path = DEMO_DATASET_DIR / item['src']
        if not src_path.exists():
            print(f"[-] Missing source file: {src_path}")
            continue

        dest_filename = f"{item['doc_id']}_{item['filename']}"
        dest_path = UPLOADS_DIR / dest_filename
        shutil.copy2(str(src_path), str(dest_path))

        file_bytes = dest_path.read_bytes()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        file_size = len(file_bytes)

        # Ingest document record
        execute_db(
            """
            INSERT OR REPLACE INTO documents 
            (id, case_id, filename, file_type, file_size, file_path, file_hash, category, classification_confidence, status, uploaded_by, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                item['doc_id'],
                case_id,
                item['filename'],
                'pdf',
                file_size,
                str(dest_path),
                file_hash,
                item['category'],
                98.5,
                'Pending',
                'Misari Vadalia'
            )
        )

        # Run extraction & analysis
        print(f"    -> Analyzing {item['filename']}...")
        analyze_document(item['doc_id'], user='Misari Vadalia')
        ingested_docs.append(item['doc_id'])

    # 3. Execute Cross-Document Comparison across the case
    print("[*] Running cross-document comparison and correlation matrix...")
    try:
        compare_case_documents(case_id, user='Misari Vadalia')
    except Exception as e:
        print(f"    [-] Case comparison note: {e}")

    print(f"[✓] VEXORA Demo Case '{case_id}' successfully prepared with {len(ingested_docs)} documents.")
    return {
        'case_id': case_id,
        'documents_count': len(ingested_docs),
        'status': 'Demo Seed Ready',
        'backup_file': backup_file,
        'already_exists': False
    }


def reset_demo_database():
    """Wipes and seeds the database with a high-fidelity demonstration case."""
    return seed_demo_case(preserve_existing=False)


if __name__ == '__main__':
    reset_demo_database()
