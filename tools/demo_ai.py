#!/usr/bin/env python3
"""
VEXORA — AI Forensic Intelligence CLI Demonstration (Phase I)
Demonstrates live / configured LLM capabilities:
1. Structured field extraction with source-quote anti-hallucination verification.
2. Forensic finding explanation with innocent alternative hypotheses.
3. Multi-document contextual and mathematical cross-checks.

If no API key is configured or AI is disabled, exits cleanly with code 0.
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import Config


def main():
    parser = argparse.ArgumentParser(description="VEXORA AI Forensic Subsystem CLI Demonstration")
    parser.add_argument(
        "--doc",
        type=str,
        default="demo_dataset/tampered_01_font_shift.pdf",
        help="Path to sample document for AI analysis (default: demo_dataset/tampered_01_font_shift.pdf)"
    )
    args = parser.parse_args()

    api_key = (
        getattr(Config, 'VEXORA_LLM_API_KEY', '')
        or os.environ.get('VEXORA_LLM_API_KEY', '')
        or os.environ.get('GEMINI_API_KEY', '')
        or os.environ.get('OPENAI_API_KEY', '')
    )
    enabled = getattr(Config, 'ENABLE_LLM', False)

    # Clean exit per requirement I5
    if not enabled or not api_key or len(api_key.strip()) < 5:
        print("AI not configured, skipped")
        sys.exit(0)

    try:
        from backend.llm import (
            get_ai_status,
            extract_fields_llm,
            explain_finding,
            contextual_crosscheck
        )
        from backend.extractor import extract_document_content

        status = get_ai_status()
        print("=" * 60)
        print(" VEXORA AI FORENSIC REASONING SUBSYSTEM")
        print("=" * 60)
        print(f"Provider : {status.get('provider')}")
        print(f"Model    : {status.get('model')}")
        print(f"Target   : {args.doc}")
        print("=" * 60)

        doc_path = PROJECT_ROOT / args.doc
        if not doc_path.exists():
            print(f"Error: Target document '{args.doc}' not found.")
            sys.exit(0)

        # 1. Extract raw document text
        ext = extract_document_content(str(doc_path))
        doc_text = ext.get('text', '')
        if not doc_text:
            print("No extractable text found in target document.")
            sys.exit(0)

        # 2. Structured Field Extraction
        print("\n--- 1. STRUCTURED FIELD EXTRACTION ---")
        extracted = extract_fields_llm(doc_text, doc_type="Invoice")
        if extracted and extracted.get('fields'):
            fields = extracted['fields']
            for k, v in fields.items():
                if isinstance(v, dict):
                    print(f"  • {k:15}: {v.get('value') or v.get('total_amount')} (quote: '{v.get('source_quote')}')")
                elif isinstance(v, list):
                    print(f"  • {k:15}: {len(v)} item(s)")
            if extracted.get('dropped_fields'):
                print(f"  * Anti-hallucination dropped {len(extracted['dropped_fields'])} ungrounded field(s).")
        else:
            print("  No fields extracted or provider returned empty.")

        # 3. Finding Explanation
        print("\n--- 2. FORENSIC FINDING EXPLANATION ---")
        sample_finding = {
            'id': 'FND-DEMO-001',
            'rule_id': 'RULE-VIS-001',
            'title': 'Discrepant Font Family Detected',
            'description': 'Invoice amount rendered in different font and resolution from document body.',
            'evidence': 'Font Helvetica-Bold vs Times-Roman; Baseline shift +1.2pt',
            'severity': 'High'
        }
        explanation = explain_finding(sample_finding, nearby_text=doc_text[:2000])
        if explanation:
            print(f"  Explanation       : {explanation.get('explanation')}")
            print(f"  Innocent Hypotheses: {'; '.join(explanation.get('innocent_hypotheses', []))}")
            print(f"  Next Action Check : {explanation.get('next_verification_step')}")
        else:
            print("  Explanation unavailable.")

        # 4. Contextual Cross-Check
        print("\n--- 3. CONTEXTUAL & MATHEMATICAL CROSS-CHECK ---")
        docs = [{
            'id': 'DOC-DEMO-01',
            'filename': doc_path.name,
            'category': 'Invoice',
            'extracted_text': doc_text
        }]
        cross_findings = contextual_crosscheck(docs)
        if cross_findings:
            print(f"  Identified {len(cross_findings)} grounded contextual observation(s):")
            for cf in cross_findings:
                print(f"  • [{cf.get('rule_id')}] {cf.get('title')}: {cf.get('description')}")
        else:
            print("  No contextual discrepancies detected across evaluated records.")

        print("\n" + "=" * 60)
        print(" AI Demonstration Completed Successfully.")
        print("=" * 60)
        sys.exit(0)

    except Exception as e:
        print(f"AI demo encountered error: {e}")
        sys.exit(0)


if __name__ == "__main__":
    main()
