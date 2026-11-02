"""
VEXORA — Automated Benchmark Evaluation Engine (Phase G)
Evaluates forensic detection performance against the demo_dataset benchmark.
Reports honest numbers for:
- Detection rate (Recall) across tampered documents
- False alarm rate across genuine documents
- Precision, Specificity, and F1-Score
- Per-rule activation frequency table.
"""

import os
import sys
import csv
from pathlib import Path

# Ensure root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import Config
from backend.extractor import extract_document_content
from backend.analyzer import analyze_visual_structure, analyze_contextual_rules
from backend.forensics_pdf import run_extended_pdf_forensics
from backend.forensics_image import run_image_forensics
from backend.classifier import classify_document
from backend.classifier_content import classify_by_content

DATASET_DIR = PROJECT_ROOT / 'demo_dataset'
LABELS_PATH = DATASET_DIR / 'labels.csv'


def run_evaluation():
    if not LABELS_PATH.exists():
        print(f"[ERROR] Benchmark dataset labels not found at {LABELS_PATH}.")
        print("Please run: python tools/make_samples.py first.")
        return 1

    # Ensure extended forensics are enabled for evaluation
    Config.ENABLE_EXTENDED_FORENSICS = True
    Config.ENABLE_IMAGE_FORENSICS = True
    Config.ENABLE_CORRELATOR = True

    # Read ground truth annotations
    records = []
    with open(LABELS_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    print("\n" + "=" * 90)
    print(" VEXORA FORENSIC INTELLIGENCE SYSTEM — BENCHMARK EVALUATION REPORT")
    print("=" * 90)
    print(f"Target Dataset: {DATASET_DIR}")
    print(f"Total Test Documents: {len(records)}\n")

    results = []
    rule_counts = {}
    tp = 0
    fn = 0
    tn = 0
    fp = 0

    col_fmt = "{:<36} | {:<10} | {:<8} | {:<20} | {:<8}"
    print(col_fmt.format("Filename", "Type", "Ground", "Fired Rule(s)", "Verdict"))
    print("-" * 90)

    for rec in records:
        fname = rec['filename']
        fpath = DATASET_DIR / fname
        is_tampered = int(rec['is_tampered'])
        expected_rules = [r.strip() for r in rec['expected_rules'].split(',') if r.strip() and r.strip() != 'None']

        if not fpath.exists():
            print(f"Missing file: {fname}")
            continue

        ext = fpath.suffix.lower().lstrip('.')
        all_findings = []

        try:
            # 1. Extraction
            extraction = extract_document_content(str(fpath))
            full_text = extraction.get('full_text', '')

            # 2. Category
            cat, conf = classify_document(fname, file_type=ext)
            if cat in ('General Document', 'Uncategorized') and full_text:
                cat_c, _ = classify_by_content(full_text, file_type=ext)
                if cat_c != 'General Document':
                    cat = cat_c

            # 3. Visual & Contextual Rules
            vis_findings = analyze_visual_structure(str(fpath))
            all_findings.extend(vis_findings)

            ctx_findings = analyze_contextual_rules(cat, full_text, extraction, extraction.get('metadata'))
            all_findings.extend(ctx_findings)

            # 4. Extended PDF Rules
            if ext == 'pdf':
                pdf_findings = run_extended_pdf_forensics(str(fpath))
                all_findings.extend(pdf_findings)

            # 5. Image Forensics
            if ext in ('png', 'jpg', 'jpeg', 'tiff', 'bmp'):
                img_findings = run_image_forensics(str(fpath))
                all_findings.extend(img_findings)

        except Exception as e:
            all_findings.append({
                'rule_id': 'ERROR-EXT',
                'title': f'Processing Error: {str(e)}',
                'severity': 'Low'
            })

        # Tally unique rule IDs
        fired_rules = sorted(list({f['rule_id'] for f in all_findings if f.get('rule_id')}))
        for rid in fired_rules:
            rule_counts[rid] = rule_counts.get(rid, 0) + 1

        # Classify verdict
        has_anomalies = len(fired_rules) > 0
        verdict = ""
        if is_tampered == 1:
            if has_anomalies:
                tp += 1
                verdict = "TP (HIT)"
            else:
                fn += 1
                verdict = "FN (MISS)"
        else:
            if has_anomalies:
                fp += 1
                verdict = "FP (ALARM)"
            else:
                tn += 1
                verdict = "TN (CLEAN)"

        fired_str = ", ".join(fired_rules) if fired_rules else "None (Clean)"
        if len(fired_str) > 20:
            fired_str = fired_str[:17] + "..."

        type_str = "Tampered" if is_tampered == 1 else "Genuine"
        ground_str = "Anomaly" if is_tampered == 1 else "Genuine"
        print(col_fmt.format(fname[:36], type_str, ground_str, fired_str, verdict))

        results.append({
            'filename': fname,
            'is_tampered': is_tampered,
            'fired_rules': fired_rules,
            'verdict': verdict
        })

    # Summary Statistics
    total_docs = len(records)
    total_tampered = tp + fn
    total_genuine = tn + fp

    accuracy = ((tp + tn) / total_docs * 100) if total_docs > 0 else 0.0
    recall = (tp / total_tampered * 100) if total_tampered > 0 else 0.0
    precision = (tp / (tp + fp) * 100) if (tp + fp) > 0 else 0.0
    specificity = (tn / total_genuine * 100) if total_genuine > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    print("\n" + "=" * 90)
    print(" SUMMARY FORENSIC PERFORMANCE METRICS")
    print("=" * 90)
    print(f"Total Evaluated Documents : {total_docs}")
    print(f"Genuine Documents         : {total_genuine} (True Negatives: {tn}, False Positives: {fp})")
    print(f"Tampered Documents        : {total_tampered} (True Positives: {tp}, False Negatives: {fn})")
    print("-" * 50)
    print(f"Overall Accuracy          : {accuracy:.1f}%")
    print(f"Recall (Detection Rate)   : {recall:.1f}%")
    print(f"Precision                 : {precision:.1f}%")
    print(f"Specificity (Clean Rate)  : {specificity:.1f}%")
    print(f"F1-Score                  : {f1:.1f}%")
    print("=" * 90)

    print("\nPER-RULE ACTIVATION COUNTS:")
    print("-" * 50)
    for rid, count in sorted(rule_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {rid:<16} : {count} hit(s)")
    print("-" * 50 + "\n")

    return 0


if __name__ == '__main__':
    sys.exit(run_evaluation())
