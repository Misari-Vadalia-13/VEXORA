"""
VEXORA — Content-Based Document Classification Fallback Module (Phase F & Phase 3)
Combines deep semantic content inspection and filename heuristics to accurately
classify documents (Invoices, Bank Statements, Purchase Orders, Tax Returns,
Employment Contracts, Financial Audits, Identity Proofs/IDs).
"""

import re

CONTENT_CLASSIFICATION_RULES = {
    'Invoice': {
        'filename_clues': ['invoice', 'inv', 'bill', 'billing'],
        'patterns': [
            r'\btax\s+invoice\b',
            r'\binvoice\s*(?:#|no|num|number)\b',
            r'\bbill\s+to\b',
            r'\bamount\s+due\b',
            r'\btotal\s+amount\b',
            r'\bgrand\s+total\b',
            r'\bremittance\b',
            r'\bpayment\s+terms\b',
            r'\bsubtotal\b',
            r'\bdue\s+date\b'
        ],
        'base_confidence': 95.0
    },
    'Bank Statement': {
        'filename_clues': ['statement', 'bank', 'acct', 'financial_statement'],
        'patterns': [
            r'\bbank\s+statement\b',
            r'\baccount\s+statement\b',
            r'\bopening\s+balance\b',
            r'\bclosing\s+balance\b',
            r'\baccount\s+number\b',
            r'\bstatement\s+period\b',
            r'\bbalance\b',
            r'\bwithdrawals?\b',
            r'\bdeposits?\b',
            r'\bavailable\s+balance\b',
            r'\btransaction\s+history\b'
        ],
        'base_confidence': 95.0
    },
    'Purchase Order': {
        'filename_clues': ['purchase_order', 'po_', 'purchase'],
        'patterns': [
            r'\bpurchase\s+order\b',
            r'\bpo\s*(?:number|#|no)\b',
            r'\bvendor\b',
            r'\bdeliver\s+to\b',
            r'\bship\s+to\b',
            r'\bunit\s+price\b',
            r'\bline\s+items?\b',
            r'\border\s+date\b'
        ],
        'base_confidence': 94.0
    },
    'Tax Return': {
        'filename_clues': ['tax', 'w-2', 'w2', '1040', 'income_tax'],
        'patterns': [
            r'\bform\s+1040\b',
            r'\bw-2\b',
            r'\binternal\s+revenue\b',
            r'\bincome\s+tax\b',
            r'\btax\s+return\b',
            r'\btax\s+year\b',
            r'\badjusted\s+gross\s+income\b',
            r'\btaxable\s+income\b',
            r'\birs\b',
            r'\btax\s+payer\b'
        ],
        'base_confidence': 96.0
    },
    'Employment Contract': {
        'filename_clues': ['contract', 'agreement', 'employment', 'nda', 'mou'],
        'patterns': [
            r'\bemployment\s+(?:agreement|contract)\b',
            r'\bcontract\b',
            r'\bagreement\b',
            r'\bparties\b',
            r'\bemployer\b',
            r'\bemployee\b',
            r'\bcompensation\b',
            r'\bnon-disclosure\b',
            r'\bscope\s+of\s+work\b',
            r'\bprobationary\s+period\b'
        ],
        'base_confidence': 94.0
    },
    'Financial Audit': {
        'filename_clues': ['audit', 'annual_report', 'financial_report'],
        'patterns': [
            r'\bindependent\s+auditor\b',
            r'\bfinancial\s+statements\b',
            r'\bbalance\s+sheet\b',
            r'\bstatement\s+of\s+operations\b',
            r'\bstatement\s+of\s+cash\s+flows\b',
            r'\bnotes\s+to\s+financial\b',
            r'\baudit\s+opinion\b'
        ],
        'base_confidence': 94.0
    },
    'Identity Record': {
        'filename_clues': ['identity', 'passport', 'driver', 'license', 'id_card', 'id_proof'],
        'patterns': [
            r'\bpassport\b',
            r'\bdriver(?:\'s)?\s+license\b',
            r'\bnational\s+identity\b',
            r'\bidentification\s+card\b',
            r'\bdob\b',
            r'\bdate\s+of\s+birth\b',
            r'\bplace\s+of\s+birth\b',
            r'\bexpiration\s+date\b'
        ],
        'base_confidence': 95.0
    }
}

def classify_by_content(text_content, filename='', file_type='pdf'):
    """
    Combines semantic content keywords AND filename clues for forensic classification.
    Returns tuple: (category_name, confidence_score_float).
    """
    # Handle callers passing file_type as second positional argument
    if filename and filename.lower() in ('pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'):
        file_type = filename
        filename = ''

    clean_text = (text_content or '').lower()
    clean_filename = (filename or '').lower()

    if not clean_text and not clean_filename:
        if file_type.lower() in ('png', 'jpg', 'jpeg', 'tiff', 'bmp'):
            return ('Scanned Artifact', 65.0)
        return ('General Document', 60.0)

    best_category = 'General Document'
    best_score = 60.0
    best_matches = 0

    for category, config in CONTENT_CLASSIFICATION_RULES.items():
        matches = 0

        # Filename clues
        for clue in config.get('filename_clues', []):
            if clue in clean_filename:
                matches += 2  # Strong signal from filename

        # Content keyword patterns
        for pat in config['patterns']:
            if re.search(pat, clean_text, re.IGNORECASE):
                matches += 1

        if matches > 0:
            score = min(config['base_confidence'] + (matches - 1) * 1.5, 99.5)
            if matches > best_matches or (matches == best_matches and score > best_score):
                best_matches = matches
                best_score = score
                best_category = category

    if best_matches == 0:
        if file_type.lower() in ('png', 'jpg', 'jpeg', 'tiff', 'bmp'):
            return ('Scanned Artifact', 65.0)
        return ('General Document', 60.0)

    return (best_category, round(best_score, 1))
