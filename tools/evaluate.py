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
import backend.database as db_module
from backend.database import init_db
from backend.models import create_case, create_document, save_document_extraction
from backend.comparator import compare_case_documents
from backend.correlator import build_case_relationship_graph

DATASET_DIR = PROJECT_ROOT / 'demo_dataset'
LABELS_PATH = DATASET_DIR / 'labels.csv'
CASES_PATH = DATASET_DIR / 'cases.csv'


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

            # 5. Image Forensics (Standalone Images and PDF Embedded Images)
            if ext in ('png', 'jpg', 'jpeg', 'tiff', 'bmp', 'pdf'):
                img_findings = run_image_forensics(str(fpath), doc_category=cat)
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


def run_case_evaluation():
    """
    Evaluates cross-document correlation and comparison rules against cases.csv.
    Tests duplicate reference collisions, financial total mismatches, and genuine paired records.
    """
    if not CASES_PATH.exists():
        print(f"\n[INFO] Case evaluation file not found at {CASES_PATH}. Skipping case-level evaluation.")
        return 0

    print("\n" + "=" * 90)
    print(" SECTION 2: CROSS-DOCUMENT CASE-LEVEL EVALUATION (Comparator & Correlator)")
    print("=" * 90)

    # Save previous active database to restore afterwards
    prev_db = getattr(db_module, '_last_active_db', None)

    # Initialize ephemeral database for case evaluation
    eval_db_path = str((PROJECT_ROOT / 'backend' / 'eval_benchmark.db').resolve())
    if os.path.exists(eval_db_path):
        try:
            os.remove(eval_db_path)
        except Exception:
            pass

    init_db(eval_db_path)
    Config.ENABLE_CORRELATOR = True

    cases = []
    with open(CASES_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(row)

    print(f"Target Scenarios: {CASES_PATH}")
    print(f"Total Test Cases: {len(cases)}\n")

    col_fmt = "{:<28} | {:<10} | {:<8} | {:<28} | {:<8}"
    print(col_fmt.format("Case ID", "Type", "Ground", "Detected Discrepancies", "Verdict"))
    print("-" * 90)

    c_tp = 0
    c_fn = 0
    c_tn = 0
    c_fp = 0

    for c in cases:
        cid = c['case_id']
        is_tampered = int(c.get('is_tampered', 0))
        filenames = [fn.strip() for fn in c.get('filenames', '').split(';') if fn.strip()]

        create_case({
            'title': c.get('title', cid),
            'type': 'Cross-Document Benchmark',
            'priority': 'High',
            'status': 'Active',
            'investigator': 'Benchmark Runner',
            'description': c.get('tampering_type', 'Benchmark Case')
        }, custom_id=cid)

        for idx, fn in enumerate(filenames):
            fpath = DATASET_DIR / fn
            if not fpath.exists():
                continue
            ext = fpath.suffix.lower().lstrip('.')
            doc_id = f"DOC-{cid}-{idx+1:02d}"
            ext_data = extract_document_content(str(fpath))
            create_document({
                'id': doc_id,
                'case_id': cid,
                'filename': fn,
                'file_type': ext,
                'file_size': fpath.stat().st_size,
                'file_path': str(fpath.resolve()),
                'category': 'Invoice',
                'status': 'Analyzed'
            })
            save_document_extraction(doc_id, ext_data)

        cmp_res = compare_case_documents(cid)
        graph_res = build_case_relationship_graph(cid)

        discrepancies = cmp_res.get('discrepancies', [])
        has_conflict = len(discrepancies) > 0

        # Extract unique discrepancy attributes
        disc_attrs = list({d.get('attribute', 'Discrepancy') for d in discrepancies})
        disc_str = ", ".join(disc_attrs) if disc_attrs else "None (Matches)"
        if len(disc_str) > 28:
            disc_str = disc_str[:25] + "..."

        verdict = ""
        if is_tampered == 1:
            if has_conflict:
                c_tp += 1
                verdict = "TP (HIT)"
            else:
                c_fn += 1
                verdict = "FN (MISS)"
        else:
            if has_conflict:
                c_fp += 1
                verdict = "FP (ALARM)"
            else:
                c_tn += 1
                verdict = "TN (CLEAN)"

        type_str = "Tampered" if is_tampered == 1 else "Genuine"
        ground_str = "Anomaly" if is_tampered == 1 else "Genuine"
        print(col_fmt.format(cid[:28], type_str, ground_str, disc_str, verdict))

    # Case Summary Metrics
    total_cases = len(cases)
    total_tampered = c_tp + c_fn
    total_genuine = c_tn + c_fp

    c_acc = ((c_tp + c_tn) / total_cases * 100) if total_cases > 0 else 0.0
    c_rec = (c_tp / total_tampered * 100) if total_tampered > 0 else 0.0
    c_prec = (c_tp / (c_tp + c_fp) * 100) if (c_tp + c_fp) > 0 else 0.0
    c_spec = (c_tn / total_genuine * 100) if total_genuine > 0 else 0.0
    c_f1 = (2 * c_prec * c_rec / (c_prec + c_rec)) if (c_prec + c_rec) > 0 else 0.0

    print("\n" + "=" * 90)
    print(" SUMMARY CASE-LEVEL FORENSIC PERFORMANCE METRICS")
    print("=" * 90)
    print(f"Total Evaluated Cases     : {total_cases}")
    print(f"Genuine Cases             : {total_genuine} (True Negatives: {c_tn}, False Positives: {c_fp})")
    print(f"Tampered Cases            : {total_tampered} (True Positives: {c_tp}, False Negatives: {c_fn})")
    print("-" * 50)
    print(f"Case-Level Accuracy       : {c_acc:.1f}%")
    print(f"Case Recall (Detection)   : {c_rec:.1f}%")
    print(f"Case Precision            : {c_prec:.1f}%")
    print(f"Case Specificity (Clean)  : {c_spec:.1f}%")
    print(f"Case F1-Score             : {c_f1:.1f}%")
    print("=" * 90 + "\n")

    # Clean up ephemeral database and restore prior active database
    if os.path.exists(eval_db_path):
        try:
            os.remove(eval_db_path)
        except Exception:
            pass
    db_module._last_active_db = prev_db

    return 0


def run_all_evaluations():
    doc_res = run_evaluation()
    case_res = run_case_evaluation()
    return doc_res or case_res


if __name__ == '__main__':
    sys.exit(run_all_evaluations())
