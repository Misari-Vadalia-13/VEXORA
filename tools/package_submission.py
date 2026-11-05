"""
VEXORA — Automated Clean Submission Packaging Script
Packages all source code, frontend assets, documentation, tests, tools, benchmark reports,
and sample documents into a clean, judge-ready distribution ZIP file.
Strictly excludes:
- .venv, venv, env
- .git
- .env, .env.local, .env.vault
- __pycache__, *.pyc, *.pyo, *.pyd
- Temporary files (*.tmp, *~, *.bak, scratch/)
- Unnecessary backups (backend/backups, backups/)
- Local IDE caches (.vscode, .idea, .pytest_cache)
- Duplicate generated reports (reports/archive/)
- Build/dist artifacts (dist/)
"""

import os
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
DIST_DIR.mkdir(parents=True, exist_ok=True)
ZIP_PATH = DIST_DIR / "vexora_submission_final.zip"

EXCLUDED_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "dist",
    "scratch"
}

EXCLUDED_PATH_PREFIXES = [
    "backups",
    "backend/backups",
    "backend\\backups",
    "reports/archive",
    "reports\\archive",
    "dist",
    "scratch"
]

EXCLUDED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
    ".tmp",
    ".bak",
    ".swp"
}

EXCLUDED_FILES = {
    ".env",
    ".env.local",
    ".env.vault",
    ".DS_Store",
    "Thumbs.db"
}

def is_path_excluded(rel_path_str: str) -> bool:
    norm = rel_path_str.replace('\\', '/')
    for prefix in EXCLUDED_PATH_PREFIXES:
        if norm == prefix or norm.startswith(prefix + '/'):
            return True
    return False

def package_submission():
    print(f"[*] Packaging VEXORA clean submission into: {ZIP_PATH}")
    file_count = 0
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(ZIP_PATH, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # Prune excluded directory names in-place
            dirs[:] = [
                d for d in dirs
                if d not in EXCLUDED_DIR_NAMES and not d.startswith('.git')
            ]

            rel_root = Path(root).relative_to(PROJECT_ROOT)
            rel_root_str = str(rel_root)

            # Skip excluded paths (e.g. backend/backups, reports/archive)
            if is_path_excluded(rel_root_str):
                continue

            for file in sorted(files):
                # Exclude specific files
                if file in EXCLUDED_FILES or file.startswith("~") or file.endswith("~"):
                    continue
                # Exclude specific extensions
                if any(file.lower().endswith(ext) for ext in EXCLUDED_EXTENSIONS):
                    continue

                abs_file = Path(root) / file
                rel_file = abs_file.relative_to(PROJECT_ROOT)
                rel_file_str = str(rel_file)

                if is_path_excluded(rel_file_str):
                    continue

                zipf.write(abs_file, arcname=rel_file_str)
                file_count += 1
                total_uncompressed_bytes += abs_file.stat().st_size

    zip_size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    raw_size_mb = total_uncompressed_bytes / (1024 * 1024)
    print(f"[✓] Package complete: {file_count} files archived.")
    print(f"[✓] Uncompressed size: {raw_size_mb:.2f} MB")
    print(f"[✓] Compressed ZIP size: {zip_size_mb:.2f} MB ({ZIP_PATH})")

    # Audit the contents of the generated ZIP to guarantee zero forbidden files
    forbidden_hits = []
    with zipfile.ZipFile(ZIP_PATH, 'r') as check_zip:
        for name in check_zip.namelist():
            norm_name = name.replace('\\', '/')
            if any(forbidden in norm_name for forbidden in ['.venv', '.git/', '__pycache__', '.env', 'backups/', 'archive/']):
                # Allow .env.example
                if norm_name == '.env.example' or norm_name.endswith('/.env.example'):
                    continue
                forbidden_hits.append(norm_name)

    if forbidden_hits:
        print(f"[!] WARNING: Forbidden files found in package: {forbidden_hits[:5]}")
    else:
        print(f"[✓] Verification passed: Zero forbidden files (.venv, .git, .env, backups, caches) in archive!")

if __name__ == '__main__':
    package_submission()
