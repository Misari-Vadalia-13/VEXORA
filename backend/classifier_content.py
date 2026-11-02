"""
VEXORA — Content-Based Document Classification Fallback Module (Phase F)
Provides deep semantic content inspection used strictly as a secondary fallback
when filename-based heuristics return 'General Document'.
Existing classifications from filename rules remain 100% untouched.
"""

import re

CONTENT_CLASSIFICATION_RULES = {
    'Invoice': {
        'patterns': [
            r'\btax\s+invoice\b',
            r'\binvoice\s+(?:no|num|number|#)\b',
            r'\bbill\s+to\b',
            r'\bamount\s+due\b',
            r'\btotal\s+amount\b',
            r'\bgrand\s+total\b',
            r'\bremittance\b',
            r'\bpayment\s+terms\b',
            r'\bsubtotal\b',
            r'\bdue\s+date\b'
        ],
        'base_confidence': 93.5
    },
    'Bank Statement': {
        'patterns': [
            r'\bbank\s+statement\b',
            r'\baccount\s+statement\b',
            r'\bopening\s+balance\b',
            r'\bclosing\s+balance\b',
            r'\baccount\s+number\b',
            r'\bstatement\s+period\b',
            r'\bwithdrawals?\b',
            r'\bdeposits?\b',
            r'\bavailable\s+balance\b',
            r'\btransaction\s+history\b'
        ],
        'base_confidence': 94.5
    },
    'Purchase Order': {
        'patterns': [
            r'\bpurchase\s+order\b',
            r'\bpo\s+(?:number|#|no)\b',
            r'\bvendor\b',
            r'\bdeliver\s+to\b',
            r'\bship\s+to\b',
            r'\bunit\s+price\b',
            r'\bline\s+items?\b',
            r'\border\s+date\b'
        ],
        'base_confidence': 92.5
    },
    'Tax Return': {
        'patterns': [
            r'\bform\s+1040\b',
            r'\bw-2\b',
            r'\binternal\s+revenue\b',
            r'\btax\s+year\b',
            r'\badjusted\s+gross\s+income\b',
            r'\btaxable\s+income\b',
            r'\birs\b',
            r'\btax\s+payer\b'
        ],
        'base_confidence': 95.0
    },
    'Employment Contract': {
        'patterns': [
            r'\bemployment\s+(?:agreement|contract)\b',
            r'\bemployer\b',
            r'\bemployee\b',
            r'\bcompensation\b',
            r'\bnon-disclosure\b',
            r'\bscope\s+of\s+work\b',
            r'\bprobationary\s+period\b'
        ],
        'base_confidence': 91.5
    },
    'Financial Audit': {
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
        'patterns': [
            r'\bpassport\b',
            r'\bdriver(?:\'s)?\s+license\b',
            r'\bnational\s+identity\b',
            r'\bidentification\s+card\b',
            r'\bdate\s+of\s+birth\b',
            r'\bplace\s+of\s+birth\b',
            r'\bexpiration\s+date\b'
        ],
        'base_confidence': 93.0
    }
}

def classify_by_content(text_content, file_type='pdf'):
    """
    Performs fallback semantic classification based exclusively on document text content.
    Used ONLY when filename-based classification returns 'General Document'.
    Returns tuple: (category_name, confidence_score)
    """
    if not text_content or not isinstance(text_content, str):
        if file_type.lower() in ('png', 'jpg', 'jpeg', 'tiff', 'bmp'):
            return ('Scanned Artifact', 65.0)
        return ('General Document', 60.0)

    clean_text = text_content.lower()

    best_category = 'General Document'
    best_score = 60.0
    best_matches = 0

    for category, config in CONTENT_CLASSIFICATION_RULES.items():
        matches = 0
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
