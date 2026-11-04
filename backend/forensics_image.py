"""
VEXORA — Image Forensics Module (Phase D / Phase H Stabilized)
Detects pixel-level alterations, compression artifacts, and cloned content in scanned documents & photos:
- IMG-001: Error Level Analysis (ELA) via JPEG recompression disparity
- IMG-002: Block-level noise and sharpness inconsistency (Laplacian variance)
- IMG-003: Copy-move forgery detection using ORB keypoint displacement clustering
- IMG-004: Signature region check (ink presence, location, and printed text overlap)

Non-negotiable constraints & Phase H Principles:
- Gated execution: Analyzes standalone raster images and embedded PDF images only.
  Never rasterizes vector PDF pages into synthetic images.
- If a born-digital PDF has no embedded images, records a single Observation note.
- Copy-move ignores keypoint matches located in detected text areas.
- Severities capped at 'Medium' due to heuristic nature of pixel forensics.
- Guarded imports for opencv-python-headless, numpy, and Pillow.
- Never asserts "confirmed fraud" or "forgery".
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

import re
import time

try:
    from PIL import Image, ImageChops, ExifTags
except ImportError:
    Image = None
    ImageChops = None
    ExifTags = None

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
# Phase H: Capped severity of IMG-001 and IMG-003 at 'Medium' because pixel forensics are heuristics
IMAGE_FORENSIC_RULES = {
    'IMG-001': {
        'id': 'IMG-001',
        'title': 'Error Level Analysis (ELA) Compression Disparity',
        'severity': 'Medium',
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
        'severity': 'Medium',
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
    },
    'IMG-005': {
        'id': 'IMG-005',
        'title': 'Image EXIF Metadata & Provenance Analysis',
        'severity': 'Low',
        'category': 'Contextual Forensics',
        'confidence': 0.82,
        'evidence_class': 'Observation',
        'limitation': 'Heuristic limitation: EXIF tags can be stripped by privacy tools, social media, or web uploaders; software signatures do not prove unauthorized tampering.',
        'recommendation': 'Review EXIF modification history, camera make/model, and software tags against standard corporate imaging workflows.'
    }
}

# Categories of documents where absence of a signature is forensically noteworthy
SIGNATURE_EXPECTED_CATEGORIES = {
    'contract', 'agreement', 'deed', 'affidavit', 'lease', 'nda', 'mou',
    'power of attorney', 'employment agreement'
}


# Checks whether required computer vision libraries are installed and functional
def is_image_forensics_available():
    """Checks if all required image analysis dependencies are operational."""
    return bool(cv2 is not None and np is not None and Image is not None)


# =====================================================================
# 1. IMG-001: Error Level Analysis (ELA)
# =====================================================================

# Recompresses image at quality 90 to detect pixel-level compression disparity
def check_error_level_analysis(pil_image, quality=90, threshold_multiplier=2.8, page_num=1):
    """
    IMG-001: Recompresses image at a fixed JPEG quality (90) and computes the pixel-level
    error surface compared to the original. Spliced elements saved with different compression
    histories exhibit markedly elevated error levels relative to the page median.
    Severity capped at Medium per Phase H guidelines.
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

        threshold = max(page_median * threshold_multiplier, page_median + (3.0 * page_std), 4.5)

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

                # Persist ELA visualization difference map
                viz_path_str = None
                viz_url = None
                try:
                    scale = 15.0
                    ela_vis = np.clip(diff_arr * scale, 0, 255).astype(np.uint8)
                    if cv2 is not None:
                        ela_vis_bgr = cv2.applyColorMap(ela_vis, cv2.COLORMAP_JET)
                        cv2.rectangle(ela_vis_bgr, (int(x0), int(y0)), (int(x1), int(y1)), (0, 0, 255), 2)
                        cv2.putText(ela_vis_bgr, f"ELA MaxErr: {round(max_err, 1)}", (int(x0), max(15, int(y0) - 5)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
                    else:
                        ela_vis_bgr = np.stack([ela_vis] * 3, axis=-1)

                    upload_root = Config.UPLOAD_FOLDER
                    try:
                        from flask import current_app, has_app_context
                        if has_app_context() and current_app and current_app.config.get('UPLOAD_FOLDER'):
                            upload_root = current_app.config.get('UPLOAD_FOLDER')
                    except Exception:
                        pass
                    evidence_dir = Path(upload_root) / 'evidence'
                    evidence_dir.mkdir(parents=True, exist_ok=True)
                    fname = f"ela_diff_{int(x0)}_{int(y0)}_p{page_num}_{int(time.time() * 1000)}.png"
                    target_file = evidence_dir / fname
                    if cv2 is not None:
                        cv2.imwrite(str(target_file), ela_vis_bgr)
                    else:
                        Image.fromarray(ela_vis).save(str(target_file))
                    viz_path_str = str(target_file)
                    viz_url = f"/api/evidence/{fname}"
                except Exception as viz_err:
                    logger.debug(f"[IMG-001] Could not persist ELA visualization: {viz_err}")

                finding_entry = {
                    'rule_id': rule['id'],
                    'title': rule['title'],
                    'severity': 'Medium',
                    'category': rule['category'],
                    'status': 'Potential Anomaly',
                    'confidence': rule['confidence'],
                    'evidence_class': rule['evidence_class'],
                    'page_number': page_num,
                    'coordinates': [int(x0), int(y0), int(x1), int(y1)],
                    'description': (
                        f"[Heuristic Finding] Error Level Analysis identified an anomalous compression residue "
                        f"clustering at [{x0}, {y0}, {x1}, {y1}]. Block error is {round(max_err, 1)} "
                        f"(page median: {round(page_median, 1)}). Suggests this patch was saved under a "
                        f"different JPEG quantization history than the host document. [{rule['limitation']}]."
                    ),
                    'evidence': f"ELA block error {round(max_err, 1)} vs page median {round(page_median, 1)}"
                }
                if viz_path_str:
                    finding_entry['visualization_path'] = viz_path_str
                    finding_entry['evidence_url'] = viz_url
                findings.append(finding_entry)
    except Exception as e:
        logger.warning(f"[IMG-001 Error] ELA failed: {e}")

    return findings


# =====================================================================
# 2. IMG-002: Noise & Sharpness Inconsistency
# =====================================================================

# Evaluates Laplacian variance disparities across non-overlapping image blocks
def check_noise_and_sharpness_inconsistency(cv_image, block_size=64, page_num=1):
    """
    IMG-002: Evaluates the consistency of high-frequency texture and Laplacian variance
    across non-overlapping image blocks. Digital inserts pasted into an existing document
    frequently display sharpness or sensor noise disparities compared to the host page.
    Severity capped at Medium per Phase H guidelines.
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
                if ratio > 10.0 and v > 100.0:
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
                'severity': 'Medium',
                'category': rule['category'],
                'status': 'Observation',
                'confidence': rule['confidence'],
                'evidence_class': rule['evidence_class'],
                'page_number': page_num,
                'coordinates': [int(x0), int(y0), int(x1), int(y1)],
                'description': (
                    f"[Heuristic Finding] Sharpness and high-frequency edge variance in region [{x0}, {y0}, {x1}, {y1}] "
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

# Detects bounding boxes of printed text lines to suppress false copy-move matches from repeated letters
def _detect_text_line_boxes(gray_image):
    """
    Identifies rectangular bounding boxes of printed or rendered text lines.
    Used by check_copy_move_orb to filter out false keypoint matches caused by repeated typographical characters.
    """
    if cv2 is None or np is None or gray_image is None:
        return []
    try:
        _, thresh = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 5))
        connected = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            # Text lines typically have small height and horizontal aspect ratio
            if 5 <= h <= 35 and (w / max(1, h)) >= 1.4:
                boxes.append((x - 6, y - 3, x + w + 6, y + h + 3))
        return boxes
    except Exception:
        return []


# Identifies cloned or duplicated regions within a single image using ORB keypoint matching
def check_copy_move_orb(cv_image, min_matches=6, min_distance=45.0, page_num=1, text_boxes=None):
    """
    IMG-003: Identifies cloned or duplicated regions within a single image using ORB
    keypoint descriptor matching and spatial displacement vector clustering.
    Cloned text, numbers, or rubber stamps generate parallel keypoint vectors.
    Ignores matches whose keypoints fall within detected text areas to avoid matching repeated letters.
    Severity capped at Medium per Phase H guidelines.
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

        # Detect text areas if not supplied
        if text_boxes is None:
            text_boxes = _detect_text_line_boxes(gray)

        def _is_in_text(pt):
            for bx0, by0, bx1, by1 in text_boxes:
                if bx0 <= pt[0] <= bx1 and by0 <= pt[1] <= by1:
                    return True
            return False

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

                # Principled Phase H filter: ignore matches whose points overlap detected text areas
                if _is_in_text(pt1) or _is_in_text(pt2):
                    continue

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

            # Additional tightening: reject thin collinear 1D slivers (e.g. single dotted lines or borders)
            valid_clone_clusters = []
            for c in clone_clusters:
                dist, angle, members = c
                all_pts = [p for pair in members for p in pair]
                xs = [p[0] for p in all_pts]
                ys = [p[1] for p in all_pts]
                bbox_w = max(xs) - min(xs)
                bbox_h = max(ys) - min(ys)
                if bbox_w >= 15 and bbox_h >= 15:
                    valid_clone_clusters.append(c)

            # Priority 4 Upgrade: RANSAC Affine Geometric Consistency Verification
            geometrically_verified_clusters = []
            for c in valid_clone_clusters:
                dist, angle, members = c
                if len(members) >= 4:
                    src_pts = np.float32([pair[0] for pair in members]).reshape(-1, 1, 2)
                    dst_pts = np.float32([pair[1] for pair in members]).reshape(-1, 1, 2)
                    try:
                        M, inliers = cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=5.0)
                        inlier_count = int(np.sum(inliers)) if inliers is not None else 0
                        if inlier_count >= min_matches:
                            inlier_pairs = [members[i] for i in range(len(members)) if inliers[i][0] == 1]
                            geometrically_verified_clusters.append((dist, angle, inlier_pairs))
                    except Exception:
                        pass
                else:
                    geometrically_verified_clusters.append(c)

            if geometrically_verified_clusters:
                best_cluster = max(geometrically_verified_clusters, key=lambda c: len(c[2]))
                members = best_cluster[2]
                all_pts = [p for pair in members for p in pair]

                x0 = int(min(p[0] for p in all_pts))
                y0 = int(min(p[1] for p in all_pts))
                x1 = int(max(p[0] for p in all_pts))
                y1 = int(max(p[1] for p in all_pts))

                findings.append({
                    'rule_id': rule['id'],
                    'title': rule['title'],
                    'severity': 'Medium',
                    'category': rule['category'],
                    'status': 'Potential Anomaly',
                    'confidence': rule['confidence'],
                    'evidence_class': rule['evidence_class'],
                    'page_number': page_num,
                    'coordinates': [x0, y0, x1, y1],
                    'description': (
                        f"[Heuristic Finding] ORB feature keypoint matching detected {len(members)} coherent cloned feature vectors "
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

# Scans lower page section for handwritten signature strokes; only reports when found or when expected
def check_signature_region(cv_image, page_num=1, doc_category=None, expects_signature=False):
    """
    IMG-004: Scans the lower section of a document page for handwritten signature strokes.
    Evaluates stroke presence, location, and potential overlap with printed text baseline rules.
    Phase H: Only emits a finding when signature strokes are actually detected or when the
    document category explicitly expects a signature (e.g. Contract, Agreement).
    Does not emit noisy 'unsupported' findings on ordinary documents.
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
        # If image is below minimum threshold for signature analysis
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

        # Check whether this document type expects a signature
        cat_str = str(doc_category).lower() if doc_category else ''
        is_expected = bool(expects_signature or any(k in cat_str for k in SIGNATURE_EXPECTED_CATEGORIES))

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
            # Handwritten strokes have moderate area and non-rectangular aspect ratios;
            # Ignore full-width page borders (cw >= w * 0.70)
            if 150 < area < 8000 and 15 < cw < (w * 0.70) and ch > 10:
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
        elif is_expected:
            # Only emit missing signature notice if document category strictly expects one
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
                'description': "signature analysis: no candidate ink strokes detected in designated signature zones for document type expecting signature.",
                'evidence': "No handwriting components found in lower 35% of page"
            })
    except Exception as e:
        logger.warning(f"[IMG-004 Error] Signature check failed: {e}")

    return findings




# =====================================================================
# 5. IMG-005: Image EXIF Metadata & Provenance Analysis
# =====================================================================

def check_exif_metadata(pil_image_or_path, file_path=None, page_num=1):
    """
    IMG-005: Inspects EXIF metadata tags, capture device metadata, timestamps,
    and digital editing software signatures.
    
    Principles:
    - Missing EXIF is an investigative indicator, not proof of forgery.
    - Capped at 'Medium' severity for editing software and 'Low' for timestamp divergence.
    - Preserves objective evidence classes ('Observation' / 'Inconsistency').
    """
    if Image is None:
        return []

    findings = []
    rule = IMAGE_FORENSIC_RULES['IMG-005']

    try:
        opened_here = False
        if isinstance(pil_image_or_path, (str, Path)):
            pil_img = Image.open(str(pil_image_or_path))
            target_path = str(pil_image_or_path)
            opened_here = True
        elif hasattr(pil_image_or_path, 'getexif'):
            pil_img = pil_image_or_path
            target_path = str(file_path) if file_path else None
        else:
            return []

        exif_tags = {}
        raw_exif = None
        if hasattr(pil_img, 'getexif'):
            raw_exif = pil_img.getexif()

        if raw_exif:
            try:
                for tag_id, val in raw_exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id)) if ExifTags else str(tag_id)
                    exif_tags[tag_name] = str(val).strip()

                # Also inspect Exif sub-IFD (0x8769)
                try:
                    if ExifTags and hasattr(ExifTags, 'IFD') and hasattr(ExifTags.IFD, 'Exif'):
                        sub_ifd = raw_exif.get_ifd(ExifTags.IFD.Exif)
                    else:
                        sub_ifd = raw_exif.get_ifd(0x8769)
                    if sub_ifd:
                        for tag_id, val in sub_ifd.items():
                            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id)) if ExifTags else str(tag_id)
                            exif_tags[tag_name] = str(val).strip()
                except Exception:
                    pass
            except Exception:
                pass

        # Check 1: Third-party digital image manipulation software signature
        suspicious_editors = [
            'photoshop', 'gimp', 'canva', 'paint.net', 'pixlr', 'sejda',
            'ilovepdf', 'adobe lightroom', 'snapseed', 'facetune', 'coreldraw',
            'affinity photo'
        ]
        software_val = exif_tags.get('Software', '')
        matched_editor = None
        if software_val:
            s_lower = software_val.lower()
            for ed in suspicious_editors:
                if ed in s_lower:
                    matched_editor = ed
                    break

        if matched_editor:
            findings.append({
                'rule_id': rule['id'],
                'title': f"Image Editor Signature in EXIF ({matched_editor.capitalize()})",
                'severity': 'Medium',
                'category': rule['category'],
                'status': 'Observation',
                'confidence': 0.88,
                'evidence_class': 'Observation',
                'page_number': page_num,
                'coordinates': None,
                'description': (
                    f"[Heuristic Finding] EXIF metadata contains editing software signature: '{software_val}'. "
                    f"Camera captures and scanner hardware output do not natively encode third-party graphic editing software. [{rule['limitation']}]."
                ),
                'evidence': f"EXIF Software: '{software_val}'"
            })

        # Check 2: Original capture date vs file modification date divergence
        dt_orig = exif_tags.get('DateTimeOriginal') or exif_tags.get('DateTimeDigitized')
        dt_mod = exif_tags.get('DateTime')
        if dt_orig and dt_mod:
            c_orig = re.sub(r'[^\d]', '', dt_orig)[:8]
            c_mod = re.sub(r'[^\d]', '', dt_mod)[:8]
            if c_orig and c_mod and c_orig != c_mod:
                findings.append({
                    'rule_id': rule['id'],
                    'title': 'EXIF Capture vs Modification Date Divergence',
                    'severity': 'Low',
                    'category': rule['category'],
                    'status': 'Observation',
                    'confidence': 0.82,
                    'evidence_class': 'Inconsistency',
                    'page_number': page_num,
                    'coordinates': None,
                    'description': (
                        f"[Technical Observation] EXIF capture date ({dt_orig}) differs from subsequent modification date ({dt_mod}). "
                        f"Indicates file re-export or delayed metadata update. [{rule['limitation']}]."
                    ),
                    'evidence': f"DateTimeOriginal: {dt_orig} | DateTime: {dt_mod}"
                })

        # Check 3: Check if file is JPEG photo with completely stripped/missing EXIF
        if not exif_tags and target_path:
            p_str = target_path.lower()
            if p_str.endswith(('.jpg', '.jpeg')):
                findings.append({
                    'rule_id': rule['id'],
                    'title': 'EXIF Provenance Metadata Absent',
                    'severity': 'Low',
                    'category': rule['category'],
                    'status': 'Observation',
                    'confidence': 0.65,
                    'evidence_class': 'Observation',
                    'page_number': page_num,
                    'coordinates': None,
                    'description': (
                        "Image file contains no EXIF provenance metadata (camera make, model, or capture timestamp). "
                        "Note: Missing EXIF is an investigative indicator, not proof of forgery. Many web portals, social messaging "
                        "apps, and privacy tools strip EXIF by default."
                    ),
                    'evidence': 'No EXIF metadata block found in image container'
                })

    except Exception as e:
        logger.warning(f"[IMG-005 Error] EXIF analysis failed: {e}")
    finally:
        if 'opened_here' in locals() and opened_here and hasattr(pil_img, 'close'):
            try:
                pil_img.close()
            except Exception:
                pass

    return findings

# =====================================================================
# 6. Master Image Forensics Coordinator
# =====================================================================

# Coordinates image forensic checks; runs only on standalone raster images and embedded images inside PDFs
def run_image_forensics(file_path, doc_category=None):
    """
    Master runner for Phase D/H image forensics.
    Executes ELA, sharpness inconsistency, copy-move matching, and signature checks.
    Supports standalone raster images (.png, .jpg, .jpeg, .tiff, .bmp) as well as
    embedded raster images extracted from PDF files.

    Principled Gate (Phase H):
    - Never rasterizes born-digital vector PDF pages into synthetic images.
    - If a PDF has no embedded images, records a single Observation note.
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
            findings.extend(check_signature_region(cv_img, page_num=1, doc_category=doc_category))
            findings.extend(check_exif_metadata(pil_img, file_path=file_path, page_num=1))
        except Exception as e:
            logger.warning(f"[Image Forensics] Error processing image {file_path}: {e}")

    # Case B: Multi-page PDF Document — Extract EMBEDDED raster images only
    elif ext == 'pdf' and fitz is not None:
        try:
            doc = fitz.open(file_path)
            embedded_count = 0
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_num = page_idx + 1
                image_list = page.get_images(full=True)
                for img_info in image_list:
                    xref = img_info[0]
                    try:
                        base_image = doc.extract_image(xref)
                        if not base_image:
                            continue
                        img_bytes = base_image.get("image")
                        if not img_bytes:
                            continue
                        pil_img = Image.open(io.BytesIO(img_bytes))
                        w, h = pil_img.size
                        # Skip tiny icons or 1px spacer artifacts
                        if w < 50 or h < 50:
                            continue

                        embedded_count += 1
                        cv_img = cv2.cvtColor(np.array(pil_img.convert('RGB')), cv2.COLOR_RGB2BGR)

                        findings.extend(check_error_level_analysis(pil_img, page_num=page_num))
                        findings.extend(check_noise_and_sharpness_inconsistency(cv_img, page_num=page_num))
                        findings.extend(check_copy_move_orb(cv_img, page_num=page_num))
                    except Exception as img_err:
                        logger.warning(f"[Image Forensics] Error extracting image xref {xref} in {file_path}: {img_err}")

            doc.close()

            # Phase H Principled Gate: Born-digital PDF with no embedded images
            if embedded_count == 0:
                findings.append({
                    'rule_id': '',
                    'title': 'Image Forensics Not Applicable',
                    'severity': 'Info',
                    'category': 'Visual Forensics',
                    'status': 'Observation',
                    'confidence': 1.0,
                    'evidence_class': 'Observation',
                    'page_number': 1,
                    'coordinates': None,
                    'description': 'image forensics not applicable: born-digital PDF with no embedded images',
                    'evidence': 'Born-digital PDF with no embedded images'
                })
        except Exception as e:
            logger.warning(f"[Image Forensics] Error extracting embedded images from PDF {file_path}: {e}")

    return findings
