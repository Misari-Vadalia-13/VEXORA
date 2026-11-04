"""
VEXORA — Named Entity Recognition & Forensic Information Extraction Module
Extracts persons, organizations, dates, monetary values, identifiers,
tax codes, and emails with page traceability and coordinate tracking.
"""

import re

# Comprehensive regex patterns for forensic entity detection
PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'date': (
        r'\b(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|'
        r'\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|'
        r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        r'\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|'
        r'\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})\b'
    ),
    'monetary': (
        r'(?:[\$\€\£\₹]|USD|EUR|GBP|INR)\s*(?:\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\b|'
        r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP|INR|dollars|cents)\b'
    ),
    'identifier': (
        r'\b(?:INV|BILL|PO|SWIFT|BIC|IBAN|CAS|DOC|TXN|REF|ID|VAT|PAN|GST)[-:#]+[A-Z0-9_-]{2,32}\b|'
        r'\b(?:INV|BILL|PO|SWIFT|BIC|IBAN|CAS|DOC|TXN|REF|ID|VAT|PAN|GST)\s*#\s*[A-Z0-9_-]{2,32}\b|'
        r'\b(?:INV|BILL|PO|SWIFT|BIC|IBAN|CAS|DOC|TXN|REF|ID|VAT|PAN|GST)\d{3,24}\b'
    ),
    'person': (
        r'\b(?:Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.|Lead:|Investigator:|Director:|Employee:|Employer:|Party:|Consultant:|Signatory:|Name:|Tax Payer:|Taxpayer:|Beneficiary:)[^\S\r\n]+[A-Z][a-z]+(?:[^\S\r\n]+[A-Z][a-z]+){1,2}\b'
    ),
    'organization': (
        r'\b[A-Z][A-Za-z0-9&.\'-]+(?:[^\S\r\n]+[A-Z][A-Za-z0-9&.\'-]+)*[^\S\r\n]+'
        r'(?:Inc\.?|LLC|Ltd\.?|Corp\.?|Corporation|GmbH|Bank|Technologies|Energy|Logistics|Systems|Services|Audit|Group|Holdings|Industries)\b'
    )
}

def extract_entities_from_text(text, page_number=1, word_confidences=None, default_confidence=None):
    """
    Scans a block of text and extracts categorized named entities,
    preserving the page number reference and attaching word-level confidence
    when extracted from OCR (or 'n/a (digital text)' for native digital PDF).
    """
    if not text or not isinstance(text, str):
        return {
            'dates': [],
            'monetary_values': [],
            'organizations': [],
            'persons': [],
            'identifiers': [],
            'emails': []
        }

    results = {
        'dates': [],
        'monetary_values': [],
        'organizations': [],
        'persons': [],
        'identifiers': [],
        'emails': []
    }

    # Helper to deduplicate while preserving discovery order
    seen = {k: set() for k in results}

    def compute_entity_confidence(val):
        if word_confidences is None:
            return default_confidence

        clean_v = val.strip().lower()
        if isinstance(word_confidences, list):
            # 1. Direct match of entire entity string
            for entry in word_confidences:
                if clean_v == entry.get('word', '').lower():
                    c = entry.get('conf')
                    if c is not None and float(c) >= 0:
                        return round(float(c), 1)

            # 2. Token-level matching
            matched_confs = []
            words_in_val = [re.sub(r'^[^\w]+|[^\w]+$', '', w).lower() for w in val.split() if w.strip()]
            for wv in words_in_val:
                if not wv:
                    continue
                found = False
                for entry in word_confidences:
                    w = re.sub(r'^[^\w]+|[^\w]+$', '', entry.get('word', '')).lower()
                    if wv == w:
                        c = entry.get('conf')
                        if c is not None and float(c) >= 0:
                            matched_confs.append(float(c))
                            found = True
                            break
                if not found and len(wv) >= 3:
                    for entry in word_confidences:
                        w = entry.get('word', '').lower()
                        if wv in w:
                            c = entry.get('conf')
                            if c is not None and float(c) >= 0:
                                matched_confs.append(float(c))
                                break

            if matched_confs:
                return round(sum(matched_confs) / len(matched_confs), 1)

        elif isinstance(word_confidences, dict):
            if clean_v in word_confidences:
                return round(float(word_confidences[clean_v]), 1)
            matched_confs = []
            for w in val.split():
                clean_w = re.sub(r'^[^\w]+|[^\w]+$', '', w).lower()
                if clean_w in word_confidences:
                    c = word_confidences[clean_w]
                    if c is not None and float(c) >= 0:
                        matched_confs.append(float(c))
            if matched_confs:
                return round(sum(matched_confs) / len(matched_confs), 1)

        return default_confidence

    def add_match(category, val):
        clean_val = val.strip().strip(',.;:')
        if clean_val and clean_val.lower() not in seen[category]:
            seen[category].add(clean_val.lower())
            conf = compute_entity_confidence(clean_val)
            entry = {
                'value': clean_val,
                'page': page_number
            }
            if conf is not None:
                entry['confidence'] = conf
            results[category].append(entry)

    # 1. Dates
    for match in re.finditer(PATTERNS['date'], text, re.IGNORECASE):
        add_match('dates', match.group())

    # 2. Monetary Values
    for match in re.finditer(PATTERNS['monetary'], text, re.IGNORECASE):
        add_match('monetary_values', match.group())

    # 3. Identifiers
    for match in re.finditer(PATTERNS['identifier'], text, re.IGNORECASE):
        add_match('identifiers', match.group())

    # 4. Organizations
    for match in re.finditer(PATTERNS['organization'], text):
        add_match('organizations', match.group())

    # 5. Persons
    for match in re.finditer(PATTERNS['person'], text):
        add_match('persons', match.group())

    # 6. Emails
    for match in re.finditer(PATTERNS['email'], text, re.IGNORECASE):
        add_match('emails', match.group())

    return results

def merge_entities(entity_list):
    """Merges multiple page-level entity dictionaries into a unified document-level summary."""
    combined = {
        'dates': [],
        'monetary_values': [],
        'organizations': [],
        'persons': [],
        'identifiers': [],
        'emails': []
    }
    seen = {k: set() for k in combined}

    for item in entity_list:
        for cat in combined:
            for entry in item.get(cat, []):
                key = (entry['value'].lower(), entry.get('page', 1))
                if key not in seen[cat]:
                    seen[cat].add(key)
                    merged_entry = {
                        'value': entry['value'],
                        'page': entry.get('page', 1)
                    }
                    if 'confidence' in entry:
                        merged_entry['confidence'] = entry['confidence']
                    combined[cat].append(merged_entry)

    return combined
