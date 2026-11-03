"""
VEXORA — System Banner & Diagnostics Module (Phase H)
Provides startup diagnostic banner formatting and feature flag telemetry.
Inspects V2 feature flags and external dependencies (such as Tesseract OCR)
to provide transparent status reporting at boot time and via /api/system/diagnostics.
"""

import os
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def check_tesseract_binary():
    """
    Checks whether the Tesseract OCR executable is available on the host system.
    Searches system PATH and standard Windows installation directories.
    Returns a tuple of (is_available: bool, detail_string: str).
    """
    # 1. Check system PATH via shutil.which
    path_bin = shutil.which('tesseract')
    if path_bin:
        return True, f"Found in PATH ({path_bin})"

    # 2. Check standard Windows installation directories
    candidate_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            return True, f"Found at {p}"

    # 3. Guarded check via pytesseract module
    try:
        import pytesseract
        ver = pytesseract.get_tesseract_version()
        return True, f"Found via pytesseract (v{ver})"
    except Exception:
        pass

    return False, "Not Found (Install Tesseract or set PATH for native image OCR)"


def get_v2_features_status(app_instance=None):
    """
    Inspects all V2 feature flags from environment / Config / app.config.
    Returns a dictionary of boolean flag statuses and dependency states.
    """
    from backend.config import Config

    cfg_source = app_instance.config if (app_instance and hasattr(app_instance, 'config')) else None

    def _get_flag(key, default=False):
        if cfg_source and key in cfg_source:
            val = cfg_source[key]
        else:
            val = getattr(Config, key, default)
        if isinstance(val, bool):
            return val
        return str(val).lower() in ('true', '1', 'yes')

    tess_avail, tess_detail = check_tesseract_binary()

    # OpenCV / NumPy availability
    try:
        import cv2
        import numpy as np
        cv_avail = True
        cv_detail = f"OpenCV v{cv2.__version__}, NumPy v{np.__version__}"
    except Exception:
        cv_avail = False
        cv_detail = "Not Available"

    return {
        'ENABLE_EVIDENCE_OVERLAY': _get_flag('ENABLE_EVIDENCE_OVERLAY', False),
        'ENABLE_EXTENDED_FORENSICS': _get_flag('ENABLE_EXTENDED_FORENSICS', False),
        'ENABLE_IMAGE_FORENSICS': _get_flag('ENABLE_IMAGE_FORENSICS', False),
        'ENABLE_CORRELATOR': _get_flag('ENABLE_CORRELATOR', False),
        'ENABLE_LLM': _get_flag('ENABLE_LLM', False),
        'VEXORA_STRICT_OCR': _get_flag('VEXORA_STRICT_OCR', False),
        'VEXORA_LLM_REDACT': _get_flag('VEXORA_LLM_REDACT', True),
        'VEXORA_LLM_PROVIDER': getattr(Config, 'VEXORA_LLM_PROVIDER', 'gemini'),
        'tesseract_available': tess_avail,
        'tesseract_detail': tess_detail,
        'opencv_available': cv_avail,
        'opencv_detail': cv_detail
    }


def print_startup_banner(port=5000, app_instance=None):
    """
    Prints a clear, formatted startup banner to stdout listing the ON/OFF state
    of every V2 feature flag and whether Tesseract OCR was found.
    """
    status = get_v2_features_status(app_instance)

    def _tag(val):
        return "[ON] " if val else "[OFF]"

    print("=" * 76)
    print("  VEXORA — AI-Powered Document Forensics & Contextual Intelligence")
    print(f"  Running locally at: http://127.0.0.1:{port}")
    print("=" * 76)
    print("  V2 FEATURE FLAGS:")
    print(f"    • {_tag(status['ENABLE_EVIDENCE_OVERLAY'])} Evidence Overlays      (ENABLE_EVIDENCE_OVERLAY)")
    print(f"    • {_tag(status['ENABLE_EXTENDED_FORENSICS'])} Extended PDF Forensics (ENABLE_EXTENDED_FORENSICS)")
    print(f"    • {_tag(status['ENABLE_IMAGE_FORENSICS'])} Image Forensics        (ENABLE_IMAGE_FORENSICS)")
    print(f"    • {_tag(status['ENABLE_CORRELATOR'])} Cross-Doc Correlator   (ENABLE_CORRELATOR)")
    print(f"    • {_tag(status['ENABLE_LLM'])} LLM Reasoning Layer   (ENABLE_LLM)")
    print(f"    • {_tag(status['VEXORA_STRICT_OCR'])} Strict OCR Mode        (VEXORA_STRICT_OCR)")
    print(f"    • {_tag(status['VEXORA_LLM_REDACT'])} LLM PII Redaction      (VEXORA_LLM_REDACT)")
    print("  SYSTEM ENGINES & DEPENDENCIES:")
    print(f"    • Tesseract OCR Binary : {status['tesseract_detail']}")
    print(f"    • Computer Vision      : {status['opencv_detail']}")
    print(f"    • LLM Provider Config  : {status['VEXORA_LLM_PROVIDER']}")
    print("=" * 76)
