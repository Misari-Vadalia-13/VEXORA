"""
VEXORA — Automated Clean Submission Packaging Script
Packages all source code, frontend assets, documentation, tests, tools, and benchmark reports
into a clean, judge-ready distribution ZIP file, strictly excluding .git, .venv, .env,
and temporary build artifacts.
"""

import os
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
DIST_DIR.mkdir(parents=True, exist_ok=True)
ZIP_PATH = DIST_DIR / "vexora_submission_final.zip"

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "dist"
}

EXCLUDED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log"
}

EXCLUDED_FILES = {
    ".env",
    ".env.local"
}

def package_submission():
    print(f"[*] Packaging VEXORA clean submission into: {ZIP_PATH}")
    file_count = 0
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(ZIP_PATH, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith('.git')]

            rel_root = Path(root).relative_to(PROJECT_ROOT)

            # Skip dist or backups folder if large
            if str(rel_root).startswith("dist") or str(rel_root).startswith("backups"):
                continue

            for file in files:
                if file in EXCLUDED_FILES:
                    continue
                if any(file.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
                    continue

                abs_file = Path(root) / file
                rel_file = abs_file.relative_to(PROJECT_ROOT)

                zipf.write(abs_file, arcname=str(rel_file))
                file_count += 1
                total_uncompressed_bytes += abs_file.stat().st_size

    zip_size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    raw_size_mb = total_uncompressed_bytes / (1024 * 1024)
    print(f"[✓] Package complete: {file_count} files archived.")
    print(f"[✓] Uncompressed size: {raw_size_mb:.2f} MB")
    print(f"[✓] Compressed ZIP size: {zip_size_mb:.2f} MB ({ZIP_PATH})")

if __name__ == '__main__':
    package_submission()
