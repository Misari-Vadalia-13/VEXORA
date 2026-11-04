"""
VEXORA — Configuration Module
Defines application configuration settings, filesystem paths,
and runtime parameters for the Flask backend and SQLite database.
"""

import os
from pathlib import Path

# Base project directory (c:\VEXORA)
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment variable and threading safety guard for Windows OpenBLAS
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')

# Optional .env loader for local development secrets
_env_file = BASE_DIR / '.env'
if _env_file.exists():
    try:
        with open(_env_file, 'r', encoding='utf-8') as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _v = _line.split('=', 1)
                    _k, _v = _k.strip(), _v.strip().strip('"\'')
                    import sys
                    is_testing = ('unittest' in sys.modules) or any('unittest' in arg for arg in sys.argv)
                    if _k and _k not in os.environ and not (is_testing and _k == 'VEXORA_STRICT_OCR'):
                        os.environ[_k] = _v
    except Exception:
        pass

# Backend and database paths
BACKEND_DIR = BASE_DIR / 'backend'

# Configurable database path via VEXORA_DB_PATH (defaults to backend/vexora.db)
_custom_db = os.environ.get('VEXORA_DB_PATH')
if _custom_db:
    _p = Path(_custom_db)
    DATABASE_PATH = _p if _p.is_absolute() else (BASE_DIR / _p)
else:
    DATABASE_PATH = BACKEND_DIR / 'vexora.db'

SCHEMA_PATH = BACKEND_DIR / 'schema.sql'

# Ingestion and report folders
UPLOAD_FOLDER = BASE_DIR / 'uploads'
REPORTS_FOLDER = BASE_DIR / 'reports'
FRONTEND_DIR = BASE_DIR / 'frontend'

# Allowed document file extensions for forensic intake
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'}

# Maximum allowed file upload size (16 Megabytes)
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

TEST_DATABASE_PATH = BACKEND_DIR / 'test_vexora.db'

class Config:
    # Security check for production environments
    if os.environ.get('FLASK_ENV') == 'production':
        _sec = os.environ.get('SECRET_KEY')
        if not _sec or _sec == 'vexora-forensics-dev-secret-key-2026':
            raise RuntimeError("CRITICAL: Production environment requires an explicitly configured, non-default SECRET_KEY.")

    """Base application configuration class."""
    BASE_DIR = BASE_DIR
    BACKEND_DIR = BACKEND_DIR
    SECRET_KEY = os.environ.get('SECRET_KEY', 'vexora-forensics-dev-secret-key-2026')
    DATABASE = str(DATABASE_PATH)
    UPLOAD_FOLDER = str(UPLOAD_FOLDER)
    REPORTS_FOLDER = str(REPORTS_FOLDER)
    FRONTEND_DIR = str(FRONTEND_DIR)
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH
    JSON_SORT_KEYS = False
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')

    # Security & Cookie Attributes
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in ('true', '1', 'yes')
    VEXORA_ALLOW_DEMO_RESET = os.environ.get('VEXORA_ALLOW_DEMO_RESET', 'true').lower() in ('true', '1', 'yes')
    VEXORA_REQUIRE_AUTH = os.environ.get('VEXORA_REQUIRE_AUTH', 'false').lower() in ('true', '1', 'yes')

    # Feature Flags (V2 Additive Extensions)
    ENABLE_EVIDENCE_OVERLAY = os.environ.get('ENABLE_EVIDENCE_OVERLAY', 'false').lower() in ('true', '1', 'yes')
    ENABLE_EXTENDED_FORENSICS = os.environ.get('ENABLE_EXTENDED_FORENSICS', 'false').lower() in ('true', '1', 'yes')
    ENABLE_IMAGE_FORENSICS = os.environ.get('ENABLE_IMAGE_FORENSICS', 'false').lower() in ('true', '1', 'yes')
    ENABLE_LLM = os.environ.get('ENABLE_LLM', 'false').lower() in ('true', '1', 'yes')
    VEXORA_LLM_PROVIDER = os.environ.get('VEXORA_LLM_PROVIDER', 'gemini').lower()
    VEXORA_LLM_MODEL = os.environ.get('VEXORA_LLM_MODEL', '')
    VEXORA_LLM_API_KEY = os.environ.get('VEXORA_LLM_API_KEY') or os.environ.get('GEMINI_API_KEY') or os.environ.get('OPENAI_API_KEY') or ''
    VEXORA_LLM_REDACT = os.environ.get('VEXORA_LLM_REDACT', 'true').lower() in ('true', '1', 'yes')
    VEXORA_STRICT_OCR = os.environ.get('VEXORA_STRICT_OCR', 'false').lower() in ('true', '1', 'yes')
    ENABLE_CORRELATOR = os.environ.get('ENABLE_CORRELATOR', 'false').lower() in ('true', '1', 'yes')
    VEXORA_CORS_ORIGINS = os.environ.get('VEXORA_CORS_ORIGINS', 'http://127.0.0.1:5000,http://localhost:5000,http://127.0.0.1:5500,http://localhost:3000')

class TestConfig(Config):
    """Configuration used specifically for automated test suites."""
    TESTING = True
    DATABASE = str(TEST_DATABASE_PATH)  # Isolated SQLite file for repeatable tests
