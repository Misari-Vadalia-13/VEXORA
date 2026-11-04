"""
VEXORA — OCR Reliability & Quantitative Accuracy Evaluator
Computes Character Error Rate (CER) and Word Error Rate (WER) using Levenshtein distance.
Provides command-line evaluation and programmatic reporting for OCR ground truth verification.
"""

import sys
import argparse
from pathlib import Path


def levenshtein_distance(seq1, seq2):
    """
    Computes exact Levenshtein edit distance (insertions, deletions, substitutions)
    between two sequences (list of characters or list of words).
    """
    m, n = len(seq1), len(seq2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if seq1[i - 1] == seq2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],      # Deletion
                    dp[i][j - 1],      # Insertion
                    dp[i - 1][j - 1]   # Substitution
                )

    return dp[m][n]


def compute_cer(reference_text, hypothesis_text):
    """
    Computes Character Error Rate:
    CER = Levenshtein(chars(ref), chars(hyp)) / len(chars(ref))
    Returns CER float (e.g. 0.05 = 5% error) and character accuracy (1.0 - CER).
    """
    ref_chars = list(reference_text)
    hyp_chars = list(hypothesis_text)
    if not ref_chars:
        return (0.0, 1.0) if not hyp_chars else (1.0, 0.0)

    dist = levenshtein_distance(ref_chars, hyp_chars)
    cer = dist / len(ref_chars)
    accuracy = max(0.0, 1.0 - cer)
    return round(cer, 4), round(accuracy, 4)


def compute_wer(reference_text, hypothesis_text):
    """
    Computes Word Error Rate:
    WER = Levenshtein(words(ref), words(hyp)) / len(words(ref))
    Returns WER float (e.g. 0.08 = 8% error) and word accuracy (1.0 - WER).
    """
    ref_words = reference_text.split()
    hyp_words = hypothesis_text.split()
    if not ref_words:
        return (0.0, 1.0) if not hyp_words else (1.0, 0.0)

    dist = levenshtein_distance(ref_words, hyp_words)
    wer = dist / len(ref_words)
    accuracy = max(0.0, 1.0 - wer)
    return round(wer, 4), round(accuracy, 4)


def evaluate_ocr_strings(reference, hypothesis, label="Document"):
    """Evaluates a pair of reference and hypothesis strings and returns a structured dictionary."""
    cer, char_acc = compute_cer(reference, hypothesis)
    wer, word_acc = compute_wer(reference, hypothesis)

    return {
        'label': label,
        'reference_chars': len(reference),
        'hypothesis_chars': len(hypothesis),
        'reference_words': len(reference.split()),
        'hypothesis_words': len(hypothesis.split()),
        'cer': cer,
        'char_accuracy': char_acc,
        'wer': wer,
        'word_accuracy': word_acc
    }


def main():
    parser = argparse.ArgumentParser(description="VEXORA OCR CER/WER Evaluator")
    parser.add_argument("--ref", type=str, help="Path to reference ground truth text file")
    parser.add_argument("--hyp", type=str, help="Path to hypothesis OCR extracted text file")
    parser.add_argument("--ref-text", type=str, help="Direct reference string")
    parser.add_argument("--hyp-text", type=str, help="Direct hypothesis string")

    args = parser.parse_args()

    ref_str = ""
    hyp_str = ""

    if args.ref:
        ref_str = Path(args.ref).read_text(encoding='utf-8')
    elif args.ref_text:
        ref_str = args.ref_text

    if args.hyp:
        hyp_str = Path(args.hyp).read_text(encoding='utf-8')
    elif args.hyp_text:
        hyp_str = args.hyp_text

    if not ref_str and not hyp_str:
        print("Usage: python evaluate_ocr.py --ref <ref.txt> --hyp <hyp.txt> or --ref-text '...' --hyp-text '...'")
        sys.exit(1)

    result = evaluate_ocr_strings(ref_str, hyp_str)
    print("\n" + "=" * 60)
    print(" VEXORA OCR QUANTITATIVE ERROR RATE EVALUATION")
    print("=" * 60)
    print(f" Reference Characters : {result['reference_chars']}")
    print(f" Hypothesis Characters: {result['hypothesis_chars']}")
    print(f" Reference Words      : {result['reference_words']}")
    print(f" Hypothesis Words     : {result['hypothesis_words']}")
    print("-" * 60)
    print(f" Character Error Rate (CER) : {result['cer'] * 100:.2f}% (Accuracy: {result['char_accuracy'] * 100:.2f}%)")
    print(f" Word Error Rate (WER)      : {result['wer'] * 100:.2f}% (Accuracy: {result['word_accuracy'] * 100:.2f}%)")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()

