"""
VEXORA — Visual Evidence Overlay Engine (Phase A)
Renders PDF and image document pages with high-resolution visual bounding boxes,
rule ID label tags, and coordinate traceability.
"""

import io
import os
import json
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

from backend.models import get_finding_by_id, get_findings_by_document, get_document_by_id
from backend.analyzer import resolve_document_file_path

logger = logging.getLogger(__name__)


def parse_coordinates(coords_raw):
    """
    Safely parses bounding box coordinates from list, tuple, or JSON string.
    Expected format: [x0, y0, x1, y1] (float numbers).
    Returns [x0, y0, x1, y1] as floats, or None if invalid or absent.
    """
    if coords_raw is None:
        return None

    coords = None
    if isinstance(coords_raw, (list, tuple)):
        coords = coords_raw
    elif isinstance(coords_raw, str):
        trimmed = coords_raw.strip()
        if not trimmed or trimmed.lower() in ('none', 'null', ''):
            return None
        try:
            parsed = json.loads(trimmed)
            if isinstance(parsed, (list, tuple)):
                coords = parsed
        except Exception:
            # Fallback: comma or space separated numbers
            try:
                parts = [float(p.strip()) for p in trimmed.strip('[]()').split(',') if p.strip()]
                if len(parts) >= 4:
                    coords = parts[:4]
            except Exception:
                return None

    if coords and len(coords) >= 4:
        try:
            return [float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])]
        except (ValueError, TypeError):
            return None

    return None


def render_page_overlay(file_path, page_number=1, findings=None, zoom=2.0):
    """
    Renders a specific page of a PDF or image file with highlighted bounding boxes
    and rule ID badges for all provided findings.
    
    Parameters:
    - file_path: Path to the target document (PDF or image).
    - page_number: 1-indexed page number to render.
    - findings: Optional finding dictionary or list of finding dictionaries.
    - zoom: Resolution scale factor for PDF rendering (default 2.0 = ~144 DPI).

    Returns:
    - PNG bytes of the highlighted page image.
    """
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Document file '{file_path}' does not exist on disk.")

    ext = path_obj.suffix.lower().lstrip('.')

    # 1. Render base page to PIL Image
    if ext == 'pdf':
        if fitz is None:
            raise RuntimeError("PyMuPDF (fitz) is not installed in the Python runtime.")

        doc = fitz.open(str(path_obj))
        page_idx = max(0, page_number - 1)
        if page_idx >= len(doc):
            doc.close()
            raise IndexError(f"Page number {page_number} is out of bounds for document with {len(doc)} pages.")

        page = doc[page_idx]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        base_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        coord_scale = zoom
    else:
        # Standard raster image (PNG, JPG, TIFF, BMP)
        base_img = Image.open(str(path_obj)).convert("RGB")
        coord_scale = 1.0

    # Normalize findings list
    finding_list = []
    if findings:
        if isinstance(findings, dict):
            finding_list = [findings]
        elif isinstance(findings, list):
            finding_list = findings

    # If no findings, return clean page
    if not finding_list:
        out_buf = io.BytesIO()
        base_img.save(out_buf, format="PNG", optimize=True)
        return out_buf.getvalue()

    # 2. Draw Highlights & Bounding Boxes using an RGBA transparent overlay
    overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.load_default()

    img_w, img_h = base_img.size

    for f in finding_list:
        # Check if finding belongs to requested page
        f_page = f.get('page_number', 1)
        if f_page != page_number:
            continue

        raw_coords = f.get('coordinates')
        parsed = parse_coordinates(raw_coords)
        if not parsed:
            continue

        # Convert PDF points / image coords to pixels using scale factor
        x0 = max(0.0, min(parsed[0], parsed[2]) * coord_scale)
        y0 = max(0.0, min(parsed[1], parsed[3]) * coord_scale)
        x1 = min(float(img_w), max(parsed[0], parsed[2]) * coord_scale)
        y1 = min(float(img_h), max(parsed[1], parsed[3]) * coord_scale)

        # Minimum visible box dimensions (at least 8px high/wide)
        if (x1 - x0) < 8.0:
            x1 = min(float(img_w), x0 + 16.0)
        if (y1 - y0) < 8.0:
            y1 = min(float(img_h), y0 + 16.0)

        # Color mapping based on finding severity
        sev = str(f.get('severity', 'Medium')).capitalize()
        if sev in ('Critical', 'High'):
            box_border = (239, 68, 68, 230)      # Vivid Crimson
            box_fill = (239, 68, 68, 45)         # Semi-transparent red highlight
            badge_bg = (185, 28, 28, 240)        # Dark red badge
        elif sev == 'Medium':
            box_border = (245, 158, 11, 230)     # Amber
            box_fill = (245, 158, 11, 45)
            badge_bg = (180, 83, 9, 240)
        else:
            box_border = (59, 130, 246, 230)     # Blue / Info
            box_fill = (59, 130, 246, 45)
            badge_bg = (29, 78, 216, 240)

        # Draw highlight fill and outer border rectangle
        draw.rectangle([x0, y0, x1, y1], fill=box_fill, outline=box_border, width=3)

        # Draw rule identifier label badge
        rule_label = f"[{f.get('rule_id', 'RULE')}] {sev}"
        label_bbox = draw.textbbox((0, 0), rule_label, font=font)
        lbl_w = label_bbox[2] - label_bbox[0] + 10
        lbl_h = label_bbox[3] - label_bbox[1] + 6

        # Position label badge above bounding box (or inside top if near image ceiling)
        badge_y0 = y0 - lbl_h - 2 if y0 >= lbl_h + 4 else y0 + 2
        badge_y1 = badge_y0 + lbl_h
        badge_x0 = max(0.0, min(x0, float(img_w - lbl_w)))
        badge_x1 = badge_x0 + lbl_w

        # Draw badge pill and white text
        draw.rectangle([badge_x0, badge_y0, badge_x1, badge_y1], fill=badge_bg)
        draw.text((badge_x0 + 5, badge_y0 + 2), rule_label, fill=(255, 255, 255, 255), font=font)

    # 3. Composite overlay on base image and export PNG
    final_img = Image.alpha_composite(base_img.convert("RGBA"), overlay).convert("RGB")
    out_buf = io.BytesIO()
    final_img.save(out_buf, format="PNG", optimize=True)
    return out_buf.getvalue()


def get_finding_evidence_image(finding_id, zoom=2.0):
    """
    Renders an evidence image for a specific finding by ID.
    Returns:
    - (png_bytes, None) on success.
    - (None, error_dict) if coordinates are missing, file not found, or finding absent.
    """
    finding = get_finding_by_id(finding_id)
    if not finding:
        return None, {
            'success': False,
            'error': f"Finding '{finding_id}' was not found in the repository.",
            'code': 'NOT_FOUND'
        }

    # Verify presence of valid visual coordinates or visual evidence artifacts
    raw_coords = finding.get('coordinates')
    parsed_coords = parse_coordinates(raw_coords)

    # Check if a visual artifact (e.g. ELA difference map) was generated for this finding
    vis_path = finding.get('visualization_path')
    ev_url = finding.get('evidence_url')
    if not parsed_coords:
        candidate_path = None
        if vis_path and os.path.exists(vis_path):
            candidate_path = vis_path
        elif ev_url:
            filename = os.path.basename(ev_url)
            try:
                from flask import current_app
                raw_up = current_app.config.get('UPLOAD_FOLDER')
                upload_folder = Path(raw_up) if raw_up else Path(Config.UPLOAD_FOLDER)
            except Exception:
                from backend.config import Config
                upload_folder = Path(Config.UPLOAD_FOLDER)
            possible = upload_folder / 'evidence' / filename
            if possible.exists():
                candidate_path = str(possible)
        elif finding.get('evidence') and 'saved: ' in str(finding.get('evidence')):
            try:
                fn = str(finding.get('evidence')).split('saved: ')[1].split(')')[0].strip()
                try:
                    from flask import current_app
                    upload_folder = Path(current_app.config.get('UPLOAD_FOLDER'))
                except Exception:
                    from backend.config import Config
                    upload_folder = Path(Config.UPLOAD_FOLDER)
                possible = upload_folder / 'evidence' / fn
                if possible.exists():
                    candidate_path = str(possible)
            except Exception:
                pass

        if candidate_path and os.path.exists(candidate_path):
            try:
                with open(candidate_path, 'rb') as f:
                    return f.read(), None
            except Exception as e:
                logger.warning(f"Failed to read visual evidence artifact {candidate_path}: {e}")

    if not parsed_coords:
        return None, {
            'success': False,
            'error': 'No visual bounding box coordinates available for this finding.',
            'message': 'This finding was generated by a contextual or metadata forensic rule that inspects document-level logic rather than physical bounding boxes.',
            'finding_id': finding_id,
            'rule_id': finding.get('rule_id'),
            'page_number': finding.get('page_number', 1),
            'severity': finding.get('severity'),
            'code': 'NO_COORDINATES'
        }

    # Resolve document physical file path
    doc_id = finding.get('document_id')
    if not doc_id:
        return None, {
            'success': False,
            'error': f"Finding '{finding_id}' is not linked to an ingested document.",
            'code': 'NO_DOCUMENT'
        }

    doc = get_document_by_id(doc_id)
    if not doc:
        return None, {
            'success': False,
            'error': f"Document '{doc_id}' linked to finding '{finding_id}' was not found.",
            'code': 'DOCUMENT_NOT_FOUND'
        }

    file_path = resolve_document_file_path(doc)
    if not file_path or not os.path.exists(file_path):
        return None, {
            'success': False,
            'error': f"Original file for document '{doc.get('filename')}' was not found on storage.",
            'code': 'FILE_NOT_FOUND'
        }

    try:
        page_num = finding.get('page_number', 1) or 1
        png_bytes = render_page_overlay(
            file_path=file_path,
            page_number=page_num,
            findings=[finding],
            zoom=zoom
        )
        return png_bytes, None
    except Exception as e:
        logger.error(f"[VEXORA Evidence Overlay Error] {e}", exc_info=True)
        return None, {
            'success': False,
            'error': f"Failed to render evidence overlay image: {str(e)}",
            'code': 'RENDER_ERROR'
        }


def get_document_page_overlay(doc_id, page_number=1, zoom=2.0):
    """
    Renders an overlay image for a document page containing all findings on that page.
    Returns:
    - (png_bytes, None) on success.
    - (None, error_dict) if document or file not found.
    """
    doc = get_document_by_id(doc_id)
    if not doc:
        return None, {
            'success': False,
            'error': f"Document '{doc_id}' was not found in the repository.",
            'code': 'DOCUMENT_NOT_FOUND'
        }

    file_path = resolve_document_file_path(doc)
    if not file_path or not os.path.exists(file_path):
        return None, {
            'success': False,
            'error': f"Original file for document '{doc.get('filename')}' was not found on storage.",
            'code': 'FILE_NOT_FOUND'
        }

    try:
        findings = get_findings_by_document(doc_id)
        png_bytes = render_page_overlay(
            file_path=file_path,
            page_number=page_number,
            findings=findings,
            zoom=zoom
        )
        return png_bytes, None
    except Exception as e:
        logger.error(f"[VEXORA Page Overlay Error] {e}", exc_info=True)
        return None, {
            'success': False,
            'error': f"Failed to render page overlay: {str(e)}",
            'code': 'RENDER_ERROR'
        }
