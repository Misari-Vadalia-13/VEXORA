"""
VEXORA — Configuration Module
Defines application configuration settings, filesystem paths,
and runtime parameters for the Flask backend and SQLite database.
"""

import os
from pathlib import Path

# Base project directory (c:\VEXORA)
BASE_DIR = Path(__file__).resolve().parent.parent

# Backend and database paths
BACKEND_DIR = BASE_DIR / 'backend'
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
    """Base application configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'vexora-forensics-dev-secret-key-2026')
    DATABASE = str(DATABASE_PATH)
    UPLOAD_FOLDER = str(UPLOAD_FOLDER)
    REPORTS_FOLDER = str(REPORTS_FOLDER)
    FRONTEND_DIR = str(FRONTEND_DIR)
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH
    JSON_SORT_KEYS = False
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')

class TestConfig(Config):
    """Configuration used specifically for automated test suites."""
    TESTING = True
    DATABASE = str(TEST_DATABASE_PATH)  # Isolated SQLite file for repeatable tests

