"""
VEXORA — Visual Document Rendering & Bounding Box Annotator
Renders high-fidelity page images directly from uploaded PDFs and scanned raster files using PyMuPDF.
Draws crisp red bounding boxes and forensic tags directly over anomaly coordinates for:
1. Live Interactive Web UI Document Viewer.
2. Direct embedding into generated Investigation Dossier PDF reports.
"""

from io import BytesIO
from pathlib import Path
import pymupdf
from PIL import Image, ImageDraw, ImageFont

def get_document_page_info(file_path):
    """
    Returns total page count and dimensions for each page of the document.
    """
    path = Path(file_path)
    if not path.exists():
        return {'success': False, 'error': f"File not found: {file_path}"}

    ext = path.suffix.lower().replace('.', '')
    pages = []

    if ext == 'pdf':
        try:
            doc = pymupdf.open(str(path))
            for i in range(doc.page_count):
                p = doc[i]
                pages.append({
                    'page_number': i + 1,
                    'width': round(p.rect.width, 1),
                    'height': round(p.rect.height, 1)
                })
            doc.close()
            return {'success': True, 'format': 'PDF', 'page_count': len(pages), 'pages': pages}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    else:
        try:
            img = Image.open(str(path))
            w, h = img.size
            return {
                'success': True,
                'format': ext.upper(),
                'page_count': 1,
                'pages': [{'page_number': 1, 'width': float(w), 'height': float(h)}]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

def render_page_image(file_path, page_num=1, zoom=2.0):
    """
    Renders a raw, unannotated page image to PNG bytes.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower().replace('.', '')

    if ext == 'pdf':
        doc = pymupdf.open(str(path))
        try:
            if page_num < 1 or page_num > doc.page_count:
                page_num = 1
            page = doc[page_num - 1]
            mat = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            return pix.tobytes("png")
        finally:
            doc.close()
    else:
        img = Image.open(str(path)).convert('RGB')
        buf = BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

def render_annotated_page_image(file_path, page_num=1, findings=None, zoom=2.0):
    """
    Renders the document page with all relevant forensic findings highlighted
    using high-visibility red bounding boxes and rule identifier labels.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    findings = findings or []
    ext = path.suffix.lower().replace('.', '')

    # Filter findings for this specific page with non-zero bounding boxes
    page_findings = [
        f for f in findings
        if f.get('page_number', 1) == page_num and f.get('bounding_box') and any(coord > 0 for coord in f['bounding_box'])
    ]

    if ext == 'pdf':
        doc = pymupdf.open(str(path))
        try:
            if page_num < 1 or page_num > doc.page_count:
                page_num = 1
            page = doc[page_num - 1]

            # Draw visual bounding boxes on page
            for f in page_findings:
                bbox = f['bounding_box']
                rect = pymupdf.Rect(bbox[0], bbox[1], bbox[2], bbox[3])

                # Color: Red for Critical/High, Amber/Orange for Medium/Low
                sev = (f.get('severity') or 'Medium').lower()
                if sev in ('critical', 'high'):
                    color = (0.88, 0.12, 0.12)  # Bright Red
                else:
                    color = (0.95, 0.55, 0.10)  # Warning Amber

                # Draw outer bounding box
                page.draw_rect(rect, color=color, width=2.0)

                # Draw label badge at top-left
                label_text = f" {f.get('rule_id', 'ANOMALY')} "
                badge_h = 12.0
                badge_w = min(120.0, max(45.0, len(label_text) * 6.5))
                badge_y0 = max(0.0, rect.y0 - badge_h)
                badge_rect = pymupdf.Rect(rect.x0, badge_y0, rect.x0 + badge_w, rect.y0)

                # Fill badge background
                page.draw_rect(badge_rect, color=color, fill=color)

                # Write white label text inside badge
                page.insert_text(
                    pymupdf.Point(rect.x0 + 2, rect.y0 - 2.5),
                    label_text,
                    fontsize=8,
                    color=(1, 1, 1),
                    fontname="helv"
                )

            mat = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            return pix.tobytes("png")
        finally:
            doc.close()
    else:
        # Scanned Image Annotation using PIL
        img = Image.open(str(path)).convert('RGB')
        draw = ImageDraw.Draw(img)

        for f in page_findings:
            bbox = f['bounding_box']
            x0, y0, x1, y1 = bbox[0], bbox[1], bbox[2], bbox[3]

            sev = (f.get('severity') or 'Medium').lower()
            outline_color = (225, 29, 72) if sev in ('critical', 'high') else (245, 158, 11)

            # Draw 3-pixel wide outline
            for off in range(3):
                draw.rectangle([x0 - off, y0 - off, x1 + off, y1 + off], outline=outline_color)

            # Draw tag badge
            label_text = f" {f.get('rule_id', 'ANOMALY')} "
            draw.rectangle([x0, max(0, y0 - 18), x0 + 80, y0], fill=outline_color)
            draw.text((x0 + 4, max(0, y0 - 16)), label_text, fill=(255, 255, 255))

        buf = BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
