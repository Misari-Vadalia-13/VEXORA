"""
VEXORA — Image Forensics Module (Phase D)
Detects pixel-level alterations, compression artifacts, and cloned content in scanned documents & photos:
- IMG-001: Error Level Analysis (ELA) via JPEG recompression disparity
- IMG-002: Block-level noise and sharpness inconsistency (Laplacian variance)
- IMG-003: Copy-move forgery detection using ORB keypoint displacement clustering
- IMG-004: Signature region check (ink presence, location, and printed text overlap)

Non-negotiable constraints:
- Guarded imports for opencv-python-headless, numpy, and Pillow.
- Returns status "unavailable" or empty list if libraries are missing.
- All rules labeled "heuristic" with explicit limitation disclaimers in findings.
- Never asserts "confirmed fraud" or "forgery".
- Seamlessly runs on standalone images (.png, .jpg, etc.) or rasterized PDF pages.
"""

import os
import io
import math
import logging
from pathlib import Path

# 1. Guarded External Imports
try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    from PIL import Image, ImageChops
except ImportError:
    Image = None
    ImageChops = None

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

from backend.config import Config
from backend.evidence_class import get_evidence_class

logger = logging.getLogger(__name__)

# Forensic Rules Catalog
IMAGE_FORENSIC_RULES = {
    'IMG-001': {
        'id': 'IMG-001',
        'title': 'Error Level Analysis (ELA) Compression Disparity',
        'severity': 'High',
        'category': 'Visual Forensics',
        'confidence': 0.86,
        'evidence_class': 'Potential Manipulation',
        'limitation': 'Heuristic limitation: ELA can flag legitimately recompressed images, high-contrast borders, or re-saved graphics.',
        'recommendation': 'Examine whether the highlighted region was digitally spliced from a source with different JPEG compression history.'
    },
    'IMG-002': {
        'id': 'IMG-002',
        'title': 'Block-Level Sharpness Inconsistency Detected',
        'severity': 'Medium',
        'category': 'Visual Forensics',
        'confidence': 0.82,
        'evidence_class': 'Observation',
        'limitation': 'Heuristic limitation: Scanner focal plane drift or non-uniform page lighting can introduce legitimate variance.',
        'recommendation': 'Cross-reference high-sharpness blocks against surrounding paragraph texture to confirm patch insertion.'
    },
    'IMG-003': {
        'id': 'IMG-003',
        'title': 'Potential Copy-Move Cloned Region Detected',
        'severity': 'High',
        'category': 'Visual Forensics',
        'confidence': 0.89,
        'evidence_class': 'Potential Manipulation',
        'limitation': 'Heuristic limitation: Repetitive background patterns, identical company logos, or decorative borders can produce false keypoint clusters.',
        'recommendation': 'Inspect matched keypoint coordinates to confirm if a stamp, signature, or numerical figure was duplicated across the page.'
    },
    'IMG-004': {
        'id': 'IMG-004',
        'title': 'Signature Region Presence & Overlap Check',
        'severity': 'Low',
        'category': 'Contextual Forensics',
        'confidence': 0.80,
        'evidence_class': 'Observation',
        'limitation': 'Heuristic limitation: Freeform pen stroke weight, ballpoint ink hue, and scanner binarization vary widely across documents.',
        'recommendation': 'Verify signature authenticity against authorized signatory registry cards.'
    }
}


def is_image_forensics_available():
    """Checks if all required image analysis dependencies are operational."""
    return bool(cv2 is not None and np is not None and Image is not None)


# =====================================================================
# 1. IMG-001: Error Level Analysis (ELA)
# =====================================================================

def check_error_level_analysis(pil_image, quality=90, threshold_multiplier=2.8, page_num=1):
    """
    IMG-001: Recompresses image at a fixed JPEG quality (90) and computes the pixel-level
    error surface compared to the original. Spliced elements saved with different compression
    histories exhibit markedly elevated error levels relative to the page median.
    """
    if Image is None or np is None or pil_image is None:
        return []

    findings = []
    rule = IMAGE_FORENSIC_RULES['IMG-001']

    try:
        if isinstance(pil_image, np.ndarray):
            if len(pil_image.shape) == 2:
                orig = Image.fromarray(pil_image).convert('RGB')
            else:
                orig = Image.fromarray(cv2.cvtColor(pil_image, cv2.COLOR_BGR2RGB))
        elif hasattr(pil_image, 'convert'):
            orig = pil_image.convert('RGB')
        else:
            return []

        w, h = orig.size
        if w < 60 or h < 60:
            return []

        # In-memory JPEG recompression
        buf = io.BytesIO()
        orig.save(buf, format='JPEG', quality=quality)
        buf.seek(0)
        recompressed = Image.open(buf).convert('RGB')

        # Calculate absolute pixel difference
        diff = ImageChops.difference(orig, recompressed)
        diff_gray = diff.convert('L')
        diff_arr = np.array(diff_gray, dtype=np.float32)

        # Divide into non-overlapping blocks to compute local compression error
        block_size = 32
        block_records = []
        for by in range(0, h - block_size + 1, block_size):
            for bx in range(0, w - block_size + 1, block_size):
                b = diff_arr[by:by + block_size, bx:bx + block_size]
                b_mean = float(np.mean(b))
                block_records.append((bx, by, bx + block_size, by + block_size, b_mean))

        if not block_records:
            return []

        means = [r[4] for r in block_records]
        page_median = float(np.median(means))
        page_std = float(np.std(means))

        threshold = max(page_median * threshold_multiplier, page_median + (2.0 * page_std), 2.0)

        anomalous_blocks = [r for r in block_records if r[4] > threshold]

        if anomalous_blocks:
            # Enclosing bounding box of contiguous anomalies
            x0 = min(b[0] for b in anomalous_blocks)
            y0 = min(b[1] for b in anomalous_blocks)
            x1 = max(b[2] for b in anomalous_blocks)
            y1 = max(b[3] for b in anomalous_blocks)

            # Only report if region is substantial (> 400 px^2)
            if (x1 - x0) * (y1 - y0) >= 400:
                max_err = max(b[4] for b in anomalous_blocks)
                findings.append({
                    'rule_id': rule['id'],
                    'title': rule['title'],
                    'severity': rule['severity'],
                    'category': rule['category'],
                    'status': 'Potential Anomaly',
                    'confidence': rule['confidence'],
                    'evidence_class': rule['evidence_class'],
                    'page_number': page_num,
                    'coordinates': [int(x0), int(y0), int(x1), int(y1)],
                    'description': (
                        f"Error Level Analysis identified an anomalous compression residue "
                        f"clustering at [{x0}, {y0}, {x1}, {y1}]. Block error is {round(max_err, 1)} "
                        f"(page median: {round(page_median, 1)}). Suggests this patch was saved under a "
                        f"different JPEG quantization history than the host document. [{rule['limitation']}]."
                    ),
                    'evidence': f"ELA block error {round(max_err, 1)} vs page median {round(page_median, 1)}"
                })
    except Exception as e:
        logger.warning(f"[IMG-001 Error] ELA failed: {e}")

    return findings


# =====================================================================
# 2. IMG-002: Noise & Sharpness Inconsistency
# =====================================================================

def check_noise_and_sharpness_inconsistency(cv_image, block_size=64, page_num=1):
    """
    IMG-002: Evaluates the consistency of high-frequency texture and Laplacian variance
    across non-overlapping image blocks. Digital inserts pasted into an existing document
    frequently display sharpness or sensor noise disparities compared to the host page.
    """
    if cv2 is None or np is None or cv_image is None:
        return []

    findings = []
    rule = IMAGE_FORENSIC_RULES['IMG-002']

    try:
        if len(cv_image.shape) == 3:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = cv_image

        h, w = gray.shape
        if h < (block_size * 2) or w < (block_size * 2):
            return []

        variances = []
        block_coords = []

        for y in range(0, h - block_size + 1, block_size):
            for x in range(0, w - block_size + 1, block_size):
                block = gray[y:y + block_size, x:x + block_size]
                # Filter out pure uniform white background blocks (mean > 250 with low std)
                if np.mean(block) > 250 and np.std(block) < 3.0:
                    continue

                lap_var = cv2.Laplacian(block, cv2.CV_64F).var()
                variances.append(lap_var)
                block_coords.append((x, y, x + block_size, y + block_size, lap_var))

        # Compute median variance across content-bearing blocks (excluding blank margins)
        content_variances = [v for v in variances if v > 0.5]
        if len(content_variances) < 3:
            return []

        median_var = float(np.median(content_variances))
        if median_var < 0.5:
            return []

        outlier_blocks = []
        for x0, y0, x1, y1, v in block_coords:
            if v > 0.5:
                ratio = v / median_var
                # Sharpness disparity > 3.5x higher than page content median
                if ratio > 3.5 and v > 50.0:
                    outlier_blocks.append((x0, y0, x1, y1, ratio))

        if outlier_blocks:
            # Group into bounding box
            x0 = min(b[0] for b in outlier_blocks)
            y0 = min(b[1] for b in outlier_blocks)
            x1 = max(b[2] for b in outlier_blocks)
            y1 = max(b[3] for b in outlier_blocks)
            max_ratio = max(b[4] for b in outlier_blocks)

            findings.append({
                'rule_id': rule['id'],
                'title': rule['title'],
                'severity': rule['severity'],
                'category': rule['category'],
                'status': 'Observation',
                'confidence': rule['confidence'],
                'evidence_class': rule['evidence_class'],
                'page_number': page_num,
                'coordinates': [int(x0), int(y0), int(x1), int(y1)],
                'description': (
                    f"Sharpness and high-frequency edge variance in region [{x0}, {y0}, {x1}, {y1}] "
                    f"is {round(max_ratio, 1)}x higher than the document median. Often indicates a sharp "
                    f"digital snippet pasted onto a lower-resolution or soft-scanned page. [{rule['limitation']}]."
                ),
                'evidence': f"Block Laplacian variance ratio: {round(max_ratio, 1)}x (median {round(median_var, 1)})"
            })
    except Exception as e:
        logger.warning(f"[IMG-002 Error] Sharpness analysis failed: {e}")

    return findings


# =====================================================================
# 3. IMG-003: Copy-Move Forgery Detection (ORB Keypoint Matching)
# =====================================================================

def check_copy_move_orb(cv_image, min_matches=6, min_distance=45.0, page_num=1):
    """
    IMG-003: Identifies cloned or duplicated regions within a single image using ORB
    keypoint descriptor matching and spatial displacement vector clustering.
    Cloned text, numbers, or rubber stamps generate parallel keypoint vectors.
    """
    if cv2 is None or np is None or cv_image is None:
        return []

    findings = []
    rule = IMAGE_FORENSIC_RULES['IMG-003']

    try:
        if len(cv_image.shape) == 3:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = cv_image

        h, w = gray.shape
        if h < 100 or w < 100:
            return []

        orb = cv2.ORB_create(nfeatures=1200)
        keypoints, descriptors = orb.detectAndCompute(gray, None)

        if descriptors is None or len(keypoints) < 20:
            return []

        # Brute Force Matcher with Hamming Distance
        bf = cv2.BFMatcher(cv2.NORM_HAMMING)
        raw_matches = bf.knnMatch(descriptors, descriptors, k=3)

        displacement_pairs = []

        for m_tuple in raw_matches:
            if len(m_tuple) < 3:
                continue
            # m_tuple[0] is match with itself (distance 0)
            m = m_tuple[1]
            n = m_tuple[2]

            # Lowe's ratio test
            if m.distance < 0.78 * n.distance:
                pt1 = keypoints[m.queryIdx].pt
                pt2 = keypoints[m.trainIdx].pt

                dx = pt2[0] - pt1[0]
                dy = pt2[1] - pt1[1]
                dist = math.hypot(dx, dy)

                # Must be separated by minimum physical distance
                if dist >= min_distance:
                    angle = math.atan2(dy, dx)
                    displacement_pairs.append((pt1, pt2, dist, angle))

        if len(displacement_pairs) >= min_matches:
            # Cluster by displacement distance and angle
            # Look for clusters with consistent displacement vectors (±15 degrees, ±15 px)
            clusters = []
            for p1, p2, dist, angle in displacement_pairs:
                matched_cluster = False
                for c in clusters:
                    ref_dist, ref_angle, members = c
                    # Angle difference accounting for circular wrap
                    diff_angle = abs(angle - ref_angle)
                    if diff_angle > math.pi:
                        diff_angle = (2 * math.pi) - diff_angle

                    if abs(dist - ref_dist) < 25.0 and diff_angle < 0.35:
                        members.append((p1, p2))
                        matched_cluster = True
                        break
                if not matched_cluster:
                    clusters.append((dist, angle, [(p1, p2)]))

            # Filter for clusters with >= min_matches
            clone_clusters = [c for c in clusters if len(c[2]) >= min_matches]

            if clone_clusters:
                best_cluster = max(clone_clusters, key=lambda c: len(c[2]))
                members = best_cluster[2]
                all_pts = [p for pair in members for p in pair]

                x0 = int(min(p[0] for p in all_pts))
                y0 = int(min(p[1] for p in all_pts))
                x1 = int(max(p[0] for p in all_pts))
                y1 = int(max(p[1] for p in all_pts))

                findings.append({
                    'rule_id': rule['id'],
                    'title': rule['title'],
                    'severity': rule['severity'],
                    'category': rule['category'],
                    'status': 'Potential Anomaly',
                    'confidence': rule['confidence'],
                    'evidence_class': rule['evidence_class'],
                    'page_number': page_num,
                    'coordinates': [x0, y0, x1, y1],
                    'description': (
                        f"ORB feature keypoint matching detected {len(members)} coherent cloned feature vectors "
                        f"with consistent spatial offset between regions. Suggests digital copy-move duplication of "
                        f"a graphical element, stamp, or numerical figure. [{rule['limitation']}]."
                    ),
                    'evidence': f"{len(members)} matched keypoint pairs clustered at offset distance ~{int(best_cluster[0])}px"
                })
    except Exception as e:
        logger.warning(f"[IMG-003 Error] Copy-move detection failed: {e}")

    return findings


# =====================================================================
# 4. IMG-004: Signature Region Verification
# =====================================================================

def check_signature_region(cv_image, page_num=1):
    """
    IMG-004: Scans the lower section of a document page for handwritten signature strokes.
    Evaluates stroke presence, location, and potential overlap with printed text baseline rules.
    If the document format or quality does not allow reliable signature extraction,
    returns an explicit unsupported notice per specification.
    """
    if cv2 is None or np is None or cv_image is None:
        return []

    findings = []
    rule = IMAGE_FORENSIC_RULES['IMG-004']

    try:
        if len(cv_image.shape) == 3:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = cv_image

        h, w = gray.shape
        # If image is too small or unsuited for signature analysis
        if h < 200 or w < 200:
            findings.append({
                'rule_id': rule['id'],
                'title': rule['title'],
                'severity': 'Low',
                'category': rule['category'],
                'status': 'Observation',
                'confidence': 0.50,
                'evidence_class': rule['evidence_class'],
                'page_number': page_num,
                'coordinates': None,
                'description': "signature analysis: unsupported for this document (resolution below minimum forensic threshold).",
                'evidence': f"Dimensions: {w}x{h} px"
            })
            return findings

        # Focus inspection on the bottom third of the page
        roi_y0 = int(h * 0.65)
        roi_y1 = h
        roi = gray[roi_y0:roi_y1, 0:w]

        # Adaptive thresholding to detect thin curved ink strokes
        thresh = cv2.adaptiveThreshold(
            roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 21, 10
        )

        # Detect connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(thresh)

        # Look for connected components characteristic of cursive / pen strokes
        signature_components = []
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            cw = stats[i, cv2.CC_STAT_WIDTH]
            ch = stats[i, cv2.CC_STAT_HEIGHT]
            # Handwritten strokes have moderate area and non-rectangular aspect ratios
            if 150 < area < 8000 and cw > 15 and ch > 10:
                aspect = cw / float(ch)
                if 0.3 < aspect < 6.0:
                    bx = stats[i, cv2.CC_STAT_LEFT]
                    by = stats[i, cv2.CC_STAT_TOP] + roi_y0
                    signature_components.append((bx, by, bx + cw, by + ch, area))

        if signature_components:
            # Cluster strokes into a signature bounding box
            x0 = min(c[0] for c in signature_components)
            y0 = min(c[1] for c in signature_components)
            x1 = max(c[2] for c in signature_components)
            y1 = max(c[3] for c in signature_components)

            # Check if signature overlaps printed text lines
            # Printed lines have long horizontal structural profiles
            roi_sig = thresh[y0 - roi_y0:y1 - roi_y0, x0:x1] if (y1 - roi_y0) <= thresh.shape[0] else thresh[y0 - roi_y0:, x0:x1]
            has_line_overlap = False
            if roi_sig.size > 0:
                horiz_proj = np.sum(roi_sig > 0, axis=1)
                # Dense continuous horizontal stripe indicates underlying printed line
                if np.max(horiz_proj) > (roi_sig.shape[1] * 0.75):
                    has_line_overlap = True

            overlap_msg = "Signature physically overlaps printed text or underline." if has_line_overlap else "Signature is positioned cleanly in signature block."
            severity = 'Medium' if has_line_overlap else 'Low'

            findings.append({
                'rule_id': rule['id'],
                'title': f"Signature Identified ({'Overlapping Printed Text' if has_line_overlap else 'Clean Placement'})",
                'severity': severity,
                'category': rule['category'],
                'status': 'Observation',
                'confidence': rule['confidence'],
                'evidence_class': rule['evidence_class'],
                'page_number': page_num,
                'coordinates': [int(x0), int(y0), int(x1), int(y1)],
                'description': (
                    f"Signature ink strokes detected at coordinates [{x0}, {y0}, {x1}, {y1}]. "
                    f"{overlap_msg} [{rule['limitation']}]."
                ),
                'evidence': f"Ink cluster of {len(signature_components)} components at [{x0}, {y0}, {x1}, {y1}]"
            })
        else:
            findings.append({
                'rule_id': rule['id'],
                'title': rule['title'],
                'severity': 'Low',
                'category': rule['category'],
                'status': 'Observation',
                'confidence': 0.70,
                'evidence_class': rule['evidence_class'],
                'page_number': page_num,
                'coordinates': None,
                'description': "signature analysis: unsupported for this document (no candidate ink strokes detected in designated signature zones).",
                'evidence': "No handwriting components found in lower 35% of page"
            })
    except Exception as e:
        logger.warning(f"[IMG-004 Error] Signature check failed: {e}")

    return findings


# =====================================================================
# 5. Master Image Forensics Coordinator
# =====================================================================

def run_image_forensics(file_path):
    """
    Master runner for Phase D image forensics.
    Executes ELA, sharpness inconsistency, copy-move matching, and signature checks.
    Supports standalone raster images (.png, .jpg, .jpeg, .tiff, .bmp) as well as
    embedded or rasterized pages of PDF files.
    Returns standard VEXORA finding dictionaries.
    """
    if not is_image_forensics_available():
        logger.warning("[Image Forensics] OpenCV/NumPy/Pillow dependencies not available.")
        return []

    p = Path(file_path)
    if not p.exists():
        return []

    ext = p.suffix.lower().lstrip('.')
    findings = []

    # Case A: Standalone Raster Image File
    if ext in {'png', 'jpg', 'jpeg', 'tiff', 'bmp'}:
        try:
            pil_img = Image.open(file_path)
            cv_img = cv2.imread(str(file_path))
            if cv_img is None:
                # Fallback for unicode file paths on Windows
                cv_img = np.array(pil_img.convert('RGB'))[:, :, ::-1]

            findings.extend(check_error_level_analysis(pil_img, page_num=1))
            findings.extend(check_noise_and_sharpness_inconsistency(cv_img, page_num=1))
            findings.extend(check_copy_move_orb(cv_img, page_num=1))
            findings.extend(check_signature_region(cv_img, page_num=1))
        except Exception as e:
            logger.warning(f"[Image Forensics] Error processing image {file_path}: {e}")

    # Case B: Multi-page PDF Document (Rasterize up to first 3 pages)
    elif ext == 'pdf' and fitz is not None:
        try:
            doc = fitz.open(file_path)
            max_pages = min(len(doc), 3)
            for page_idx in range(max_pages):
                page = doc[page_idx]
                page_num = page_idx + 1

                # Render page at 150 DPI for forensic sharpness
                pix = page.get_pixmap(dpi=150)
                img_data = pix.tobytes("png")
                pil_img = Image.open(io.BytesIO(img_data))
                cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

                findings.extend(check_error_level_analysis(pil_img, page_num=page_num))
                findings.extend(check_noise_and_sharpness_inconsistency(cv_img, page_num=page_num))
                findings.extend(check_copy_move_orb(cv_img, page_num=page_num))
                findings.extend(check_signature_region(cv_img, page_num=page_num))
            doc.close()
        except Exception as e:
            logger.warning(f"[Image Forensics] Error rasterizing PDF {file_path}: {e}")

    return findings
