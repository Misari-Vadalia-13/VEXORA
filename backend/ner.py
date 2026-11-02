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
        r'\b(?:INV|BILL|PO|SWIFT|BIC|IBAN|CAS|DOC|TXN|REF|ID|VAT|PAN|GST)[-:\s#]+[A-Z0-9_-]{2,32}\b|'
        r'\b(?:INV|BILL|PO|SWIFT|BIC|IBAN|CAS|DOC|TXN|REF|ID|VAT|PAN|GST)\d{3,24}\b'
    ),
    'person': (
        r'\b(?:Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.|Lead:|Investigator:|Director:)[^\S\r\n]+[A-Z][a-z]+(?:[^\S\r\n]+[A-Z][a-z]+){1,2}\b'
    ),
    'organization': (
        r'\b[A-Z][A-Za-z0-9&.\'-]+(?:\s+[A-Z][A-Za-z0-9&.\'-]+)*\s+'
        r'(?:Inc\.?|LLC|Ltd\.?|Corp\.?|Corporation|GmbH|Bank|Technologies|Energy|Logistics|Systems|Services|Audit|Group|Holdings)\b'
    )
}

def extract_entities_from_text(text, page_number=1):
    """
    Scans a block of text and extracts categorized named entities,
    preserving the page number reference for each entity.
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

    def add_match(category, val):
        clean_val = val.strip().strip(',.;:')
        if clean_val and clean_val.lower() not in seen[category]:
            seen[category].add(clean_val.lower())
            results[category].append({
                'value': clean_val,
                'page': page_number
            })

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
                    combined[cat].append(entry)

    return combined
