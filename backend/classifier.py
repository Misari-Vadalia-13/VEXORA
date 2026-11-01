"""
VEXORA — Document Classification Module
Implements pattern-matching heuristics, filename analysis,
and metadata analysis to categorize ingested forensic documents.
"""

import re
from pathlib import Path

# Classification rules with associated keywords and weights
CLASSIFICATION_RULES = {
    'Invoice': {
        'patterns': [
            r'\binvoice\b', r'\binv\b', r'\bbill\b', r'\bbilling\b',
            r'\bvat\b', r'\btax\s+invoice\b', r'\bpurchase\s+order\b',
            r'\bpo\s*#\b', r'\bdue\s+date\b', r'\bremit\b'
        ],
        'base_confidence': 96.0
    },
    'Bank Statement': {
        'patterns': [
            r'\bswift\b', r'\bwire\b', r'\bstatement\b', r'\bbank\b',
            r'\baccount\s+statement\b', r'\biban\b', r'\bclearing\b',
            r'\btransaction\b', r'\bdebit\b', r'\bcredit\b', r'\bdeposit\b'
        ],
        'base_confidence': 94.0
    },
    'Contract': {
        'patterns': [
            r'\bcontract\b', r'\bagreement\b', r'\bnda\b', r'\bmemorandum\b',
            r'\bmou\b', r'\blicensing\b', r'\bterms\b', r'\baddendum\b',
            r'\bsettlement\b', r'\bconfidentiality\b', r'\bintellectual\s+property\b'
        ],
        'base_confidence': 97.5
    },
    'Identity Document': {
        'patterns': [
            r'\bpassport\b', r'\bidentity\b', r'\bid\s*card\b', r'\bdriver\b',
            r'\blicense\b', r'\bnational\s*id\b', r'\bidentification\b',
            r'\bvisa\b', r'\bbadge\b', r'\bcitizenship\b'
        ],
        'base_confidence': 95.0
    },
    'Receipt': {
        'patterns': [
            r'\breceipt\b', r'\bslip\b', r'\bvoucher\b', r'\bpos\b',
            r'\bpayment\s+confirmation\b', r'\bcashier\b', r'\bsale\s+receipt\b'
        ],
        'base_confidence': 93.0
    },
    'Customs Declaration': {
        'patterns': [
            r'\bcustoms\b', r'\bdeclaration\b', r'\bmanifest\b',
            r'\bbill\s+of\s+lading\b', r'\bfreight\b', r'\bexport\b',
            r'\bimport\b', r'\btariff\b', r'\bport\b', r'\bclearance\b'
        ],
        'base_confidence': 92.5
    },
    'Financial Report': {
        'patterns': [
            r'\baudit\b', r'\bquarterly\b', r'\bannual\s+report\b',
            r'\bbalance\s+sheet\b', r'\bprofit\s*(&|and)\s*loss\b',
            r'\bp&l\b', r'\b10-k\b', r'\bsec\s+filing\b'
        ],
        'base_confidence': 95.5
    }
}

def classify_document(filename, file_type='pdf', content_sample=''):
    """
    Classifies a document based on its filename, extension, and content text.
    Returns a tuple of (category_name, confidence_percentage).
    """
    normalized_name = Path(filename).stem.lower().replace('_', ' ').replace('-', ' ')
    normalized_content = content_sample.lower() if content_sample else ''
    combined_text = f"{normalized_name} {normalized_content}"

    best_category = 'Uncategorized'
    best_score = 0.0
    best_matches = 0

    for category, config in CLASSIFICATION_RULES.items():
        matches = 0
        for pattern in config['patterns']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                matches += 1

        if matches > 0:
            # Score formula: base confidence + slight boost per matching keyword, capped at 99.8%
            score = min(config['base_confidence'] + (matches - 1) * 1.5, 99.8)
            if score > best_score or (score == best_score and matches > best_matches):
                best_score = score
                best_category = category
                best_matches = matches

    if best_category == 'Uncategorized':
        # Default fallback based on file type
        if file_type.lower() in ('png', 'jpg', 'jpeg'):
            return ('Scanned Artifact', 65.0)
        return ('General Document', 60.0)

    return (best_category, round(best_score, 1))
