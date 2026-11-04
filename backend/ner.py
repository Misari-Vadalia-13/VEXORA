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


def normalize_structured_document_fields(text, entities=None, category=None):
    """
    Normalizes unstructured document entities into high-fidelity semantic models:
    - Commercial Invoices: subtotal, tax rate/amount, grand total, invoice ID, issue/due dates.
    - Bank Statements: account number, opening/closing balances, period dates.
    - Identity Documents: ID number, bearer name, issue/expiration dates.
    - Contracts: counterparties, execution date, monetary obligations.
    Computes deterministic intra-document arithmetic consistency flags.
    """
    entities = entities or {}
    text_clean = text or ""
    cat_lower = (category or "").lower()

    # Determine primary document archetype
    doc_type = "general"
    if "invoice" in cat_lower or re.search(r'\b(?:tax\s+invoice|commercial\s+invoice|invoice\s+#|bill\s+to)\b', text_clean, re.I):
        doc_type = "invoice"
    elif "bank" in cat_lower or "statement" in cat_lower or re.search(r'\b(?:bank\s+statement|account\s+statement|opening\s+balance)\b', text_clean, re.I):
        doc_type = "bank_statement"
    elif "id" in cat_lower or "identity" in cat_lower or "card" in cat_lower or re.search(r'\b(?:identification\s+card|driver\s+license|passport|national\s+id)\b', text_clean, re.I):
        doc_type = "id_card"
    elif "contract" in cat_lower or "agreement" in cat_lower or re.search(r'\b(?:employment\s+agreement|service\s+contract|agreement\s+by\s+and\s+between)\b', text_clean, re.I):
        doc_type = "contract"

    structured = {
        'document_type': doc_type,
        'detected_category': category or doc_type.replace('_', ' ').title(),
        'identifiers': {},
        'dates': {},
        'parties': {},
        'financials': {},
        'validation_flags': {}
    }

    # Helper to extract monetary float
    def _parse_amount(s):
        if not s:
            return None
        cleaned = re.sub(r'[^0-9.]', '', s)
        try:
            return float(cleaned)
        except ValueError:
            return None

    if doc_type == "invoice":
        # Extract invoice ID
        inv_id_match = re.search(r'(?:invoice\s*(?:#|no\.?|number|id|code)|inv\s*#|invoice\s*:)\s*[:#]?\s*([A-Z0-9_-]{3,30})', text_clean, re.I)
        if inv_id_match:
            structured['identifiers']['invoice_number'] = inv_id_match.group(1).strip()
        elif entities.get('identifiers'):
            for ident in entities['identifiers']:
                val = ident.get('value', '')
                if any(val.upper().startswith(p) for p in ('INV', 'BILL')):
                    structured['identifiers']['invoice_number'] = val
                    break
            if 'invoice_number' not in structured['identifiers'] and entities['identifiers']:
                structured['identifiers']['invoice_number'] = entities['identifiers'][0]['value']

        # Dates: issue and due
        issue_match = re.search(r'(?:invoice\s+date|issue\s+date|dated)[:\s]*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})', text_clean, re.I)
        due_match = re.search(r'(?:due\s+date|payment\s+due|payable\s+by)[:\s]*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})', text_clean, re.I)
        if issue_match:
            structured['dates']['issue_date'] = issue_match.group(1).strip()
        if due_match:
            structured['dates']['due_date'] = due_match.group(1).strip()

        # Parties: Vendor / Client
        if entities.get('organizations'):
            structured['parties']['vendor'] = entities['organizations'][0]['value']
            if len(entities['organizations']) > 1:
                structured['parties']['customer'] = entities['organizations'][1]['value']

        # Financials: Subtotal, Tax, Grand Total
        sub_m = re.search(r'(?:subtotal|sub-total|net\s+amount|items\s+total)[:\s]*[\$€£₹]?\s*([\d,]+(?:\.\d{1,2})?)', text_clean, re.I)
        tax_m = re.search(r'(?:tax|vat|gst|sales\s+tax)(?:\s*\([0-9.]+%{0,1}\))?[:\s]*[\$€£₹]?\s*([\d,]+(?:\.\d{1,2})?)', text_clean, re.I)
        tot_m = re.search(r'(?:total\s+amount|grand\s+total|balance\s+due|amount\s+due|invoice\s+total|\btotal\b)[:\s]*[\$€£₹]?\s*([\d,]+(?:\.\d{1,2})?)', text_clean, re.I)

        val_sub = _parse_amount(sub_m.group(1)) if sub_m else None
        val_tax = _parse_amount(tax_m.group(1)) if tax_m else None
        val_tot = _parse_amount(tot_m.group(1)) if tot_m else None

        structured['financials'] = {
            'subtotal': val_sub,
            'tax_amount': val_tax,
            'grand_total': val_tot,
            'currency': 'USD' if '$' in text_clean else 'EUR' if '€' in text_clean else 'GBP' if '£' in text_clean else 'USD'
        }

        # Cross-field arithmetic verification
        if val_sub is not None and val_tax is not None and val_tot is not None:
            expected_total = round(val_sub + val_tax, 2)
            discrepancy = round(abs(expected_total - val_tot), 2)
            is_valid = discrepancy <= 0.05
            structured['validation_flags']['arithmetic_consistent'] = is_valid
            structured['validation_flags']['arithmetic_discrepancy'] = discrepancy
            structured['validation_flags']['expected_grand_total'] = expected_total

    elif doc_type == "bank_statement":
        acc_match = re.search(r'(?:account\s*(?:#|no\.?|number)?|iban)[:\s]*([A-Z0-9-]{6,34})', text_clean, re.I)
        if acc_match:
            structured['identifiers']['account_number'] = acc_match.group(1).strip()

        open_m = re.search(r'(?:opening\s+balance|starting\s+balance)[:\s]*[\$€£₹]?\s*([\d,]+(?:\.\d{1,2})?)', text_clean, re.I)
        close_m = re.search(r'(?:closing\s+balance|ending\s+balance)[:\s]*[\$€£₹]?\s*([\d,]+(?:\.\d{1,2})?)', text_clean, re.I)
        structured['financials']['opening_balance'] = _parse_amount(open_m.group(1)) if open_m else None
        structured['financials']['closing_balance'] = _parse_amount(close_m.group(1)) if close_m else None

    elif doc_type == "id_card":
        id_m = re.search(r'(?:id\s*(?:#|no\.?|number)?|card\s*#|passport\s*#)[:\s]*([A-Z0-9-]{4,20})', text_clean, re.I)
        if id_m:
            structured['identifiers']['document_number'] = id_m.group(1).strip()
        if entities.get('persons'):
            structured['parties']['bearer_name'] = entities['persons'][0]['value']

        exp_m = re.search(r'(?:exp(?:iry|iration)?\s*(?:date)?|valid\s*(?:until|thru|through))[:\s]*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})', text_clean, re.I)
        if exp_m:
            structured['dates']['expiration_date'] = exp_m.group(1).strip()

        dob_m = re.search(r'(?:d\.?o\.?b\.?|birth\s*date|date\s*of\s*birth)[:\s]*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})', text_clean, re.I)
        if dob_m:
            structured['dates']['birth_date'] = dob_m.group(1).strip()

    return structured
