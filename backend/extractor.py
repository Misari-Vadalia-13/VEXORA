"""
VEXORA — Document Text & Layout Extraction Module
Extracts digital PDF text, block coordinates, metadata, and page layouts using PyMuPDF.
Processes scanned images using Pillow and Tesseract OCR with robust fallback handling.
"""

import os
from pathlib import Path
import pymupdf
from PIL import Image
import pytesseract

from backend.ner import extract_entities_from_text, merge_entities

class ExtractionError(Exception):
    """Raised when document extraction encounters an unrecoverable format or corruption error."""
    pass

def extract_pdf_document(source):
    """
    Extracts text, structural blocks, metadata, and entities from a digital PDF.
    `source` can be a filesystem path (str/Path) or raw bytes.
    """
    try:
        if isinstance(source, (str, Path)):
            doc = pymupdf.open(str(source))
        else:
            doc = pymupdf.open(stream=source, filetype="pdf")
    except Exception as e:
        raise ExtractionError(f"Failed to parse PDF document: {str(e)}")

    try:
        page_count = doc.page_count
        raw_meta = doc.metadata or {}

        metadata = {
            'title': raw_meta.get('title') or '',
            'author': raw_meta.get('author') or '',
            'creation_date': raw_meta.get('creationDate') or '',
            'modification_date': raw_meta.get('modDate') or '',
            'producer': raw_meta.get('producer') or '',
            'creator': raw_meta.get('creator') or '',
            'page_count': page_count
        }

        pages = []
        page_entities_list = []
        full_text_chunks = []

        for page_idx in range(page_count):
            page_num = page_idx + 1
            page = doc[page_idx]

            # 1. Extract raw page text
            page_text = page.get_text("text").strip()
            full_text_chunks.append(page_text)

            # 2. Extract structured bounding blocks
            # tuple: (x0, y0, x1, y1, "lines of text", block_no, block_type)
            raw_blocks = page.get_text("blocks")
            blocks = []

            for b in raw_blocks:
                # block_type 0 is text; 1 is image
                if len(b) >= 7 and b[6] == 0:
                    text_content = b[4].strip()
                    if text_content:
                        blocks.append({
                            'block_number': b[5],
                            'bbox': [round(b[0], 1), round(b[1], 1), round(b[2], 1), round(b[3], 1)],
                            'text': text_content,
                            'type': 'text'
                        })

            # 3. Named Entity Recognition for this page
            page_entities = extract_entities_from_text(page_text, page_number=page_num)
            page_entities_list.append(page_entities)

            words = page_text.split()
            pages.append({
                'page_number': page_num,
                'width': round(page.rect.width, 1),
                'height': round(page.rect.height, 1),
                'text': page_text,
                'word_count': len(words),
                'character_count': len(page_text),
                'blocks': blocks,
                'entities': page_entities
            })

        full_text = "\n\n--- Page Break ---\n\n".join(full_text_chunks)
        total_words = sum(p['word_count'] for p in pages)
        total_characters = sum(p['character_count'] for p in pages)
        unified_entities = merge_entities(page_entities_list)

        return {
            'success': True,
            'format': 'PDF',
            'page_count': page_count,
            'total_words': total_words,
            'total_characters': total_characters,
            'metadata': metadata,
            'pages': pages,
            'entities': unified_entities,
            'full_text': full_text
        }
    finally:
        doc.close()

def is_tesseract_available():
    """Checks whether the Tesseract OCR executable is available and executable on the host system."""
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False

def extract_image_document(source, filename="scanned_artifact.png"):
    """
    Extracts text, word-level confidence scores, and entities from a scanned image (PNG, JPG).
    Uses pytesseract.image_to_data for genuine word-level confidence metrics.
    Fails loudly and honestly if Tesseract is not installed on the host system.
    """
    try:
        if isinstance(source, (str, Path)):
            with Image.open(str(source)) as opened_img:
                img = opened_img.copy()
                img.format = opened_img.format
        else:
            from io import BytesIO
            with Image.open(BytesIO(source)) as opened_img:
                img = opened_img.copy()
                img.format = opened_img.format
    except Exception as e:
        raise ExtractionError(f"Failed to decode image file: {str(e)}")

    width, height = img.size
    img_format = img.format or Path(filename).suffix.replace('.', '').upper()
    mode = img.mode

    words = []
    blocks = []
    word_confidences = []
    ocr_text = ""
    ocr_available = is_tesseract_available()
    ocr_engine = "Tesseract-OCR (image_to_data word confidence)" if ocr_available else "None (Tesseract OCR binary not found on system PATH)"

    if ocr_available:
        try:
            # Extract per-word bounding boxes and real word-level confidence scores
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            n_boxes = len(data.get('text', []))

            for i in range(n_boxes):
                txt = (data['text'][i] or '').strip()
                conf = data['conf'][i]
                try:
                    conf_val = float(conf)
                except (ValueError, TypeError):
                    conf_val = -1.0

                if txt and conf_val >= 0:
                    words.append(txt)
                    word_confidences.append(conf_val)
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    blocks.append({
                        'block_number': i,
                        'bbox': [float(x), float(y), float(x + w), float(y + h)],
                        'text': txt,
                        'confidence': round(conf_val / 100.0, 3),  # Real per-word confidence (0.0 to 1.0)
                        'type': 'ocr_word'
                    })
            ocr_text = " ".join(words).strip()
        except Exception:
            ocr_available = False
            ocr_engine = "Tesseract-OCR Execution Failed"

    avg_conf = round(sum(word_confidences) / len(word_confidences), 2) if word_confidences else 0.0
    entities = extract_entities_from_text(ocr_text, page_number=1) if ocr_text else {'organizations': [], 'persons': [], 'dates': [], 'monetary_values': [], 'identifiers': []}

    pages = [{
        'page_number': 1,
        'width': float(width),
        'height': float(height),
        'text': ocr_text,
        'word_count': len(words),
        'character_count': len(ocr_text),
        'average_word_confidence': avg_conf,
        'ocr_available': ocr_available,
        'blocks': blocks,
        'entities': entities
    }]

    return {
        'success': True,
        'format': img_format,
        'ocr_engine': ocr_engine,
        'ocr_available': ocr_available,
        'page_count': 1,
        'total_words': len(words),
        'total_characters': len(ocr_text),
        'average_confidence': avg_conf,
        'metadata': {
            'dimensions': f"{width}x{height}",
            'mode': mode,
            'format': img_format,
            'page_count': 1,
            'ocr_word_count': len(words),
            'ocr_average_confidence': avg_conf,
            'ocr_available': ocr_available
        },
        'pages': pages,
        'entities': entities,
        'full_text': ocr_text
    }

def extract_document_content(file_path):
    """
    Unified extraction dispatcher: automatically inspects file extension,
    executes PDF extraction or Image OCR, and returns standardized forensic data.
    """
    path = Path(file_path)
    if not path.exists():
        raise ExtractionError(f"File not found on disk: {file_path}")

    ext = path.suffix.lower().replace('.', '')

    if ext == 'pdf':
        return extract_pdf_document(path)
    elif ext in ('png', 'jpg', 'jpeg', 'tiff', 'bmp'):
        return extract_image_document(path, filename=path.name)
    else:
        raise ExtractionError(f"Unsupported file format for extraction: '{ext}'")
