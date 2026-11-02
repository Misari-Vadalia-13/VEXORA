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
        r'[-/\s]+\d{1,2}(?:st|nd|rd|th)?,?[-/\s]+\d{2,4}|'
        r'\d{1,2}(?:st|nd|rd|th)?[-/\s]+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[-/\s]+\d{2,4})\b'
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
        r'(?:Inc\.?|LLC|Ltd\.?|Corp\.?|Corporation|GmbH|Bank|Technologies|Energy|Logistics|Systems|Services|Audit|Group|Holdings|Utility|Company|Enterprise|Authority)\b'
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
    for match in re.finditer(PATTERNS['organization'], text, re.IGNORECASE):
        add_match('organizations', match.group())

    # 5. Persons
    for match in re.finditer(PATTERNS['person'], text):
        clean_person = re.sub(r'^(?:Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.|Lead:|Investigator:|Director:|Applicant\s*Name:|Name:|Employee\s*Name:)\s*', '', match.group(), flags=re.I).strip()
        if clean_person:
            add_match('persons', clean_person)

    # 6. Emails
    for match in re.finditer(PATTERNS['email'], text, re.IGNORECASE):
        add_match('emails', match.group())

    # 7. Extract structured key-value form fields
    fields = extract_form_fields(text)
    if 'Applicant Name' in fields:
        add_match('persons', fields['Applicant Name'])
    elif 'Name' in fields:
        add_match('persons', fields['Name'])

    return results

def extract_form_fields(text):
    """
    Extracts structured key-value attributes from documents such as application forms,
    invoices, identity cards, and verification certificates.
    Handles both single-line ('Label: Value') and multi-line ('Label\nValue') structures.
    """
    fields = {}
    if not text or not isinstance(text, str):
        return fields

    # 1. First check explicit 'Key: Value' or 'Key = Value'
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r'^([A-Za-z0-9\s/().#_-]{2,35})\s*[:=]\s*(.+)$', line)
        if m:
            k = m.group(1).strip()
            v = m.group(2).strip()
            if 0 < len(v) < 150:
                fields[k] = v

    # 2. Check consecutive lines where line i is a label and line i+1 is its corresponding value
    raw_lines = [l.strip() for l in text.splitlines() if l.strip()]
    labels_kw = [
        'name', 'applicant', 'candidate', 'employee', 'signatory',
        'birth', 'dob', 'age',
        'address', 'residence', 'location',
        'income', 'salary', 'declared', 'earnings', 'amount', 'fee', 'total', 'price',
        'employment', 'occupation', 'designation', 'job', 'role',
        'application id', 'id', 'reference', 'ref', 'pan', 'passport', 'ssn', 'tax id', 'account', 'invoice',
        'date', 'application date', 'issue date', 'period'
    ]

    i = 0
    while i < len(raw_lines) - 1:
        line_cur = raw_lines[i]
        line_next = raw_lines[i + 1]

        # Multi-line label cannot already be a complete 'Key: Value' line
        if ':' in line_cur:
            parts = line_cur.split(':', 1)
            if len(parts) > 1 and len(parts[1].strip()) > 0:
                i += 1
                continue

        is_label = False
        if len(line_cur) < 40 and not any(line_cur.lower().startswith(x) for x in ['synthetic', 'page', 'vexora', 'customer application form']):
            for kw in labels_kw:
                if kw in line_cur.lower():
                    is_label = True
                    break

        if is_label and line_next:
            # Verify line_next is not another label
            next_is_label = False
            for kw in ['applicant name', 'date of birth', 'declared monthly income', 'application date', 'application id', 'employment']:
                if kw in line_next.lower():
                    next_is_label = True
                    break
            if not next_is_label:
                clean_key = line_cur.strip(' :#-')
                if clean_key not in fields:
                    fields[clean_key] = line_next
                i += 2
                continue
        i += 1

    return fields

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

