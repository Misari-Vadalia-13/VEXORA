"""
VEXORA — Image Forensics Engine for Scanned Artifacts
Provides heuristic forensic analysis for scanned and raster documents (PNG, JPG, TIFF):
1. Error Level Analysis (ELA) (IMG-R201) — Identifies compression discrepancy across image regions.
2. Noise Inconsistency Analysis (IMG-R202) — Flags non-uniform high-frequency variance indicative of splicing.
3. Signature Presence & Density Check (IMG-R203) — Inspects designated signature zone for ink strokes.

NOTE: All methods in this module are explicitly heuristics and marked as:
"Heuristic Analysis: Requires forensic specialist verification."
"""

import os
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageChops, ImageEnhance
import numpy as np

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

IMAGE_FORENSIC_RULES = {
    'IMG-R201': {
        'id': 'IMG-R201',
        'title': 'Error Level Analysis (ELA) Compression Inconsistency',
        'category': 'Image Forensics (Heuristic)',
        'severity': 'Medium',
        'rule_weight': 0.82,
        'recommendation': 'High-variance compression regions suggest localized re-saving or digital insertion of text/figures.'
    },
    'IMG-R202': {
        'id': 'IMG-R202',
        'title': 'Noise Pattern Inconsistency (Potential Splicing/Copy-Move)',
        'category': 'Image Forensics (Heuristic)',
        'severity': 'Medium',
        'rule_weight': 0.79,
        'recommendation': 'Non-uniform noise distribution across tiles suggests digital composition from different source scans.'
    },
    'IMG-R203': {
        'id': 'IMG-R203',
        'title': 'Missing or Blank Required Signature Block',
        'category': 'Compliance Forensics (Heuristic)',
        'severity': 'High',
        'rule_weight': 0.90,
        'recommendation': 'Document contains formal signatory declarations but signature ink density is absent in the execution zone.'
    }
}

def compute_error_level_analysis(image_path_or_bytes, quality=90, scale=10):
    """
    Computes Error Level Analysis (ELA) by recompressing the image to JPEG at `quality`,
    calculating the absolute difference with the original, and amplifying brightness.
    Returns summary statistics and any high-variance anomaly bounds.
    """
    try:
        if isinstance(image_path_or_bytes, (str, Path)):
            original = Image.open(str(image_path_or_bytes)).convert('RGB')
        else:
            original = Image.open(BytesIO(image_path_or_bytes)).convert('RGB')

        # Save to buffer at JPEG quality
        buffer = BytesIO()
        original.save(buffer, 'JPEG', quality=quality)
        buffer.seek(0)
        resaved = Image.open(buffer).convert('RGB')

        # Compute difference
        diff = ImageChops.difference(original, resaved)
        enhancer = ImageEnhance.Brightness(diff)
        enhanced_diff = enhancer.enhance(scale)

        # Convert to numpy for statistical analysis
        diff_arr = np.array(enhanced_diff, dtype=np.float32)
        mean_diff = float(np.mean(diff_arr))
        std_diff = float(np.std(diff_arr))
        max_diff = float(np.max(diff_arr))

        # Check for localized high-variance blocks (32x32 tiles)
        h, w, _ = diff_arr.shape
        tile_size = 32
        suspicious_tiles = []

        if h >= tile_size and w >= tile_size:
            for y in range(0, h - tile_size + 1, tile_size):
                for x in range(0, w - tile_size + 1, tile_size):
                    tile = diff_arr[y:y+tile_size, x:x+tile_size]
                    tile_mean = np.mean(tile)
                    if tile_mean > mean_diff + (2.5 * std_diff) and tile_mean > 15.0:
                        suspicious_tiles.append([float(x), float(y), float(x + tile_size), float(y + tile_size)])

        is_anomalous = len(suspicious_tiles) > 0 and len(suspicious_tiles) < (h * w / (tile_size * tile_size) * 0.35)

        return {
            'success': True,
            'is_anomalous': is_anomalous,
            'mean_diff': round(mean_diff, 2),
            'std_diff': round(std_diff, 2),
            'max_diff': round(max_diff, 2),
            'suspicious_tiles_count': len(suspicious_tiles),
            'primary_bbox': suspicious_tiles[0] if suspicious_tiles else [0.0, 0.0, 0.0, 0.0]
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def compute_noise_inconsistency(image_path_or_bytes):
    """
    Analyzes high-frequency noise variance across 32x32 tiles.
    Uniform scans have consistent noise; digital insertions typically have much lower (cleaner)
    or wildly higher noise variance.
    """
    if not OPENCV_AVAILABLE:
        return {'success': False, 'error': 'OpenCV is required for noise inconsistency analysis.'}

    try:
        if isinstance(image_path_or_bytes, (str, Path)):
            img = cv2.imread(str(image_path_or_bytes), cv2.IMREAD_GRAYSCALE)
        else:
            arr = np.frombuffer(image_path_or_bytes, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)

        if img is None:
            return {'success': False, 'error': 'Could not decode image.'}

        h, w = img.shape
        # Compute Laplacian to extract high frequency noise
        laplacian = cv2.Laplacian(img, cv2.CV_64F)

        tile_size = 32
        variances = []
        tiles_coords = []

        for y in range(0, h - tile_size + 1, tile_size):
            for x in range(0, w - tile_size + 1, tile_size):
                tile = laplacian[y:y+tile_size, x:x+tile_size]
                var = np.var(tile)
                variances.append(var)
                tiles_coords.append([float(x), float(y), float(x + tile_size), float(y + tile_size)])

        if not variances:
            return {'success': True, 'is_anomalous': False}

        median_var = float(np.median(variances))
        var_std = float(np.std(variances))

        # Discrepant tiles that strongly diverge from median noise floor
        anomalous_tiles = []
        for idx, v in enumerate(variances):
            if v > median_var + (3.0 * var_std) and v > 50.0:
                anomalous_tiles.append(tiles_coords[idx])

        is_anomalous = len(anomalous_tiles) > 0 and len(anomalous_tiles) < len(variances) * 0.20

        return {
            'success': True,
            'is_anomalous': is_anomalous,
            'median_noise_variance': round(median_var, 2),
            'anomalous_tiles_count': len(anomalous_tiles),
            'primary_bbox': anomalous_tiles[0] if anomalous_tiles else [0.0, 0.0, 0.0, 0.0]
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def check_signature_presence(image_path_or_bytes, blocks=None, full_text=""):
    """
    Checks for the presence of ink strokes in designated signature zones.
    Looks for labels such as "Signature", "Authorized Signatory", "Signed by".
    Inspects the rectangular region adjacent or below the label for ink density.
    """
    signature_keywords = ['signature', 'authorized signatory', 'authorised signatory', 'signed by']
    has_sig_declaration = any(kw in full_text.lower() for kw in signature_keywords)

    if not has_sig_declaration:
        return {'applicable': False}

    # Find the block coordinate of the signature label
    sig_block_bbox = None
    if blocks:
        for b in blocks:
            txt = (b.get('text') or '').lower()
            if any(kw in txt for kw in signature_keywords):
                sig_block_bbox = b.get('bbox')
                break

    if not sig_block_bbox:
        return {'applicable': False}

    try:
        if isinstance(image_path_or_bytes, (str, Path)):
            img = Image.open(str(image_path_or_bytes)).convert('L')
        else:
            img = Image.open(BytesIO(image_path_or_bytes)).convert('L')

        w, h = img.size
        # Bounding box below label: [x0, y1, x1, y1 + 60]
        x0, y0, x1, y1 = sig_block_bbox
        zone_x0 = max(0, int(x0))
        zone_y0 = min(h - 5, int(y1))
        zone_x1 = min(w, int(x1 + 60))
        zone_y1 = min(h, int(y1 + 80))

        if zone_y1 <= zone_y0 or zone_x1 <= zone_x0:
            return {'applicable': False}

        crop = img.crop((zone_x0, zone_y0, zone_x1, zone_y1))
        arr = np.array(crop)
        # Ink pixels are dark (< 180 out of 255)
        ink_pixels = np.sum(arr < 180)
        total_pixels = arr.size
        ink_ratio = float(ink_pixels) / float(total_pixels) if total_pixels > 0 else 0.0

        is_blank = ink_ratio < 0.008  # Less than 0.8% ink in signature box

        return {
            'applicable': True,
            'is_blank': is_blank,
            'ink_ratio': round(ink_ratio, 4),
            'signature_bbox': [float(zone_x0), float(zone_y0), float(zone_x1), float(zone_y1)]
        }
    except Exception as e:
        return {'applicable': False, 'error': str(e)}

def analyze_image_forensics(image_path_or_bytes, blocks=None, full_text=""):
    """
    Orchestrates all heuristic image forensics for raster scans.
    Returns findings with explicit heuristic disclaimer.
    """
    findings = []

    # 1. Error Level Analysis
    ela_res = compute_error_level_analysis(image_path_or_bytes)
    if ela_res.get('is_anomalous'):
        rule = IMAGE_FORENSIC_RULES['IMG-R201']
        findings.append({
            'rule_id': rule['id'],
            'title': rule['title'],
            'category': rule['category'],
            'severity': rule['severity'],
            'confidence': rule['rule_weight'],
            'rule_weight': rule['rule_weight'],
            'description': f"ELA revealed localized compression disparity (mean diff: {ela_res['mean_diff']}, max: {ela_res['max_diff']}). Region may contain spliced elements. [Heuristic analysis, requires forensic review]",
            'recommendation': rule['recommendation'],
            'page_number': 1,
            'bounding_box': ela_res.get('primary_bbox', [0.0, 0.0, 0.0, 0.0]),
            'evidence_type': 'image_ela'
        })

    # 2. Noise Inconsistency
    noise_res = compute_noise_inconsistency(image_path_or_bytes)
    if noise_res.get('is_anomalous'):
        rule = IMAGE_FORENSIC_RULES['IMG-R202']
        findings.append({
            'rule_id': rule['id'],
            'title': rule['title'],
            'category': rule['category'],
            'severity': rule['severity'],
            'confidence': rule['rule_weight'],
            'rule_weight': rule['rule_weight'],
            'description': f"High-frequency noise variance non-uniformity detected ({noise_res['anomalous_tiles_count']} divergent tiles). [Heuristic analysis, requires forensic review]",
            'recommendation': rule['recommendation'],
            'page_number': 1,
            'bounding_box': noise_res.get('primary_bbox', [0.0, 0.0, 0.0, 0.0]),
            'evidence_type': 'image_noise'
        })

    # 3. Signature Presence Check
    sig_res = check_signature_presence(image_path_or_bytes, blocks=blocks, full_text=full_text)
    if sig_res.get('applicable') and sig_res.get('is_blank'):
        rule = IMAGE_FORENSIC_RULES['IMG-R203']
        findings.append({
            'rule_id': rule['id'],
            'title': rule['title'],
            'category': rule['category'],
            'severity': rule['severity'],
            'confidence': rule['rule_weight'],
            'rule_weight': rule['rule_weight'],
            'description': f"Document references formal signatory authorization, but signature bounding box contains virtually no ink density ({sig_res['ink_ratio']*100:.2f}%). Execution block appears unexecuted or whited out. [Heuristic analysis]",
            'recommendation': rule['recommendation'],
            'page_number': 1,
            'bounding_box': sig_res.get('signature_bbox', [0.0, 0.0, 0.0, 0.0]),
            'evidence_type': 'signature_check'
        })

    return findings
