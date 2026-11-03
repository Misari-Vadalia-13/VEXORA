"""
VEXORA — LLM Reasoning & Explainability Layer (Phase C)
Provides contextual intelligence and AI explainability via HTTPS API calls (Gemini / OpenAI / Claude):
1. extract_fields_llm: Structured field extraction with source quotes & anti-hallucination verification.
2. explain_finding: 2-4 sentence plain-language explanation of findings, innocent hypotheses, and next verification steps.
3. contextual_crosscheck: Cross-document logical & mathematical consistency checks (LLM-001+).

Non-negotiable constraints:
- Pure HTTPS with `requests` (no heavyweight SDK).
- Graceful degradation: returns None on any error/timeout/missing key.
- Strict anti-hallucination: every extracted field/claim must have a verbatim source quote verified in text.
- Privacy redaction: masks PII (emails, phones, long digit strings) before dispatch when configured.
- Audit logging: records every invocation in audit trail without logging secret keys.
"""

import os
import re
import json
import logging
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

from backend.config import Config
from backend.evidence_class import get_evidence_class

logger = logging.getLogger(__name__)

# Mandatory AI Disclaimer
AI_DISCLAIMER = "AI-assessed, requires human review"

# Configurable Default Models per Provider
DEFAULT_MODELS = {
    'gemini': 'gemini-1.5-flash',
    'openai': 'gpt-4o-mini',
    'claude': 'claude-3-haiku-20240307',
    'anthropic': 'claude-3-haiku-20240307'
}

_last_llm_error = None


def get_last_llm_error():
    """Returns the most recent LLM invocation error message, if any."""
    global _last_llm_error
    return _last_llm_error


def set_last_llm_error(error_message):
    """Sets the most recent LLM invocation error message."""
    global _last_llm_error
    _last_llm_error = error_message


def get_model_name(provider=None):
    """
    Returns the configured model name for the given provider.
    Priority:
    1. Config.VEXORA_LLM_MODEL or os.environ.get('VEXORA_LLM_MODEL') if specified.
    2. Default model from DEFAULT_MODELS dictionary based on provider.
    """
    prov = (provider or getattr(Config, 'VEXORA_LLM_PROVIDER', 'gemini') or 'gemini').lower().strip()
    configured = getattr(Config, 'VEXORA_LLM_MODEL', '') or os.environ.get('VEXORA_LLM_MODEL', '')
    if configured and configured.strip():
        return configured.strip()
    return DEFAULT_MODELS.get(prov, 'gemini-1.5-flash')


# =====================================================================
# 1. Privacy Masking & Anti-Hallucination Verification
# =====================================================================

def redact_text_for_llm(text):
    """
    Masks sensitive personal identifying information (PII) before dispatching to external LLMs:
    - Email addresses -> [REDACTED_EMAIL]
    - Phone numbers -> [REDACTED_PHONE]
    - Long digit strings (account/ID numbers >= 10 digits) -> [REDACTED_DIGITS]
    Preserves document structure and contextual terms.
    """
    if not text or not isinstance(text, str):
        return ""

    redact_flag = getattr(Config, 'VEXORA_LLM_REDACT', True)
    if not redact_flag:
        return text

    # Mask email addresses
    redacted = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[REDACTED_EMAIL]',
        text
    )

    # Mask long digit strings (bank accounts, IBANs, national IDs, SSNs >= 10 digits)
    redacted = re.sub(
        r'\b\d{10,24}\b',
        '[REDACTED_DIGITS]',
        redacted
    )

    # Mask standard telephone number formats
    redacted = re.sub(
        r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        '[REDACTED_PHONE]',
        redacted
    )

    return redacted


def verify_source_quote(source_quote, original_text):
    """
    Strict anti-hallucination verification.
    Confirms that the model's claimed source quote actually exists within the original
    extracted text as a case-insensitive substring. Normalizes whitespace and common punctuation.
    Returns True if grounded, False if hallucinated/unfound.
    """
    if not source_quote or not isinstance(source_quote, str):
        return False
    if not original_text or not isinstance(original_text, str):
        return False

    clean_quote = " ".join(source_quote.strip().split()).lower()
    clean_text = " ".join(original_text.strip().split()).lower()

    if len(clean_quote) < 2:
        return False

    # Direct substring search
    if clean_quote in clean_text:
        return True

    # Punctuation-stripped fallback search for OCR variations
    punc_table = str.maketrans('', '', '.,;:\'"-_/\\$#()[]{}')
    stripped_quote = clean_quote.translate(punc_table)
    stripped_text = clean_text.translate(punc_table)

    return len(stripped_quote) >= 2 and stripped_quote in stripped_text


# =====================================================================
# 2. Universal HTTPS LLM Dispatcher
# =====================================================================

def call_llm(prompt, system_instruction=None, json_mode=True, timeout=15):
    """
    Dispatches a prompt to configured LLM provider via plain HTTPS (no SDK required).
    Supports Gemini (default), OpenAI, and Claude.
    Returns parsed JSON dictionary if json_mode=True, or raw response text if json_mode=False.
    Returns None on any network timeout, missing key, invalid JSON, or HTTP error.
    """
    if requests is None:
        logger.warning("[LLM] 'requests' library is not available.")
        return None

    # Verify feature flag and API key
    enabled = getattr(Config, 'ENABLE_LLM', False)
    if not enabled:
        return None

    api_key = getattr(Config, 'VEXORA_LLM_API_KEY', '') or os.environ.get('VEXORA_LLM_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        logger.info("[LLM] VEXORA_LLM_API_KEY is not configured.")
        return None

    provider = getattr(Config, 'VEXORA_LLM_PROVIDER', 'gemini').lower().strip()

    try:
        if provider == 'gemini':
            return _call_gemini(prompt, api_key, system_instruction, json_mode, timeout)
        elif provider == 'openai':
            return _call_openai(prompt, api_key, system_instruction, json_mode, timeout)
        elif provider == 'claude' or provider == 'anthropic':
            return _call_claude(prompt, api_key, system_instruction, json_mode, timeout)
        else:
            logger.warning(f"[LLM] Unsupported provider '{provider}'. Defaulting to Gemini.")
            return _call_gemini(prompt, api_key, system_instruction, json_mode, timeout)
    except Exception as e:
        logger.warning(f"[LLM Error] Execution failed: {e}")
        return None


def _call_gemini(prompt, api_key, system_instruction, json_mode, timeout):
    """Executes HTTPS request against Google Gemini REST API."""
    model = get_model_name('gemini')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    generation_config = {
        "temperature": 0.1,
        "maxOutputTokens": 2048
    }
    if json_mode:
        generation_config["responseMimeType"] = "application/json"

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": generation_config
    }

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code != 200:
        err_text = resp.text[:400]
        clean_err = err_text.replace(api_key, "[REDACTED_KEY]") if api_key else err_text
        if resp.status_code == 404 or "not found" in err_text.lower() or "not supported" in err_text.lower():
            msg = f"Model '{model}' not found or unsupported by Gemini. Please set VEXORA_LLM_MODEL in environment or .env."
            set_last_llm_error(msg)
            logger.warning(f"[Gemini API Error] {msg} (HTTP {resp.status_code})")
        else:
            set_last_llm_error(f"Gemini API HTTP {resp.status_code}: {clean_err}")
            logger.warning(f"[Gemini API Error] HTTP {resp.status_code}: {clean_err}")
        return None

    set_last_llm_error(None)
    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return None

    part = candidates[0].get("content", {}).get("parts", [{}])[0]
    text_content = part.get("text", "").strip()

    if not json_mode:
        return text_content

    # Parse and extract JSON object
    return _parse_json_block(text_content)


def _call_openai(prompt, api_key, system_instruction, json_mode, timeout):
    """Executes HTTPS request against OpenAI Chat Completions API."""
    model = get_model_name('openai')
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 2048
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code != 200:
        err_text = resp.text[:400]
        clean_err = err_text.replace(api_key, "[REDACTED_KEY]") if api_key else err_text
        if resp.status_code == 404 or "not found" in err_text.lower() or "model_not_found" in err_text.lower():
            msg = f"Model '{model}' not found or unsupported by OpenAI. Please set VEXORA_LLM_MODEL in environment or .env."
            set_last_llm_error(msg)
            logger.warning(f"[OpenAI API Error] {msg} (HTTP {resp.status_code})")
        else:
            set_last_llm_error(f"OpenAI API HTTP {resp.status_code}: {clean_err}")
            logger.warning(f"[OpenAI API Error] HTTP {resp.status_code}: {clean_err}")
        return None

    set_last_llm_error(None)
    data = resp.json()
    choices = data.get("choices", [])
    if not choices:
        return None

    content = choices[0].get("message", {}).get("content", "").strip()
    if not json_mode:
        return content

    return _parse_json_block(content)


def _call_claude(prompt, api_key, system_instruction, json_mode, timeout):
    """Executes HTTPS request against Anthropic Claude Messages API."""
    model = get_model_name('claude')
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}]
    }
    if system_instruction:
        payload["system"] = system_instruction

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code != 200:
        err_text = resp.text[:400]
        clean_err = err_text.replace(api_key, "[REDACTED_KEY]") if api_key else err_text
        if resp.status_code == 404 or "not_found" in err_text.lower() or "not found" in err_text.lower():
            msg = f"Model '{model}' not found or unsupported by Anthropic Claude. Please set VEXORA_LLM_MODEL in environment or .env."
            set_last_llm_error(msg)
            logger.warning(f"[Claude API Error] {msg} (HTTP {resp.status_code})")
        else:
            set_last_llm_error(f"Claude API HTTP {resp.status_code}: {clean_err}")
            logger.warning(f"[Claude API Error] HTTP {resp.status_code}: {clean_err}")
        return None

    set_last_llm_error(None)
    data = resp.json()
    content_list = data.get("content", [])
    if not content_list:
        return None

    text_content = content_list[0].get("text", "").strip()
    if not json_mode:
        return text_content

    return _parse_json_block(text_content)


def _parse_json_block(text):
    """Safely extracts and parses JSON even if wrapped in markdown codeblocks."""
    if not text:
        return None
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Search for first JSON object or array
        match = re.search(r'(\{.*\}|\[.*\])', clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        return None


# =====================================================================
# 3. Core Feature 1: Structured Extraction with Anti-Hallucination
# =====================================================================

def extract_fields_llm(text, doc_type="Document", document_id=None, user="System"):
    """
    Extracts key structured fields from document text using LLM:
    fields (vendor, invoice number, dates, subtotal, tax, total, line items, parties),
    each with value, confidence, and source_quote, strictly verified by substring check.
    Any ungrounded field is discarded. Grounded insights are saved to ai_insights table.
    """
    if not text or not text.strip():
        return None

    # Redact PII before sending externally
    clean_text = text[:12000]  # Cap prompt context to avoid window limits
    redacted_prompt_text = redact_text_for_llm(clean_text)

    system_prompt = (
        "You are an expert document forensics intelligence engine. "
        "Extract key structured fields from the document text: "
        "vendor, invoice number, dates, subtotal, tax, total, line items, and parties. "
        "CRITICAL REQUIREMENT: For EVERY extracted field or value, you MUST include a 'source_quote' "
        "copied verbatim from the document text. If a field does not exist, do not guess. "
        "Return a valid JSON object with the following schema:\n"
        "{\n"
        '  "vendor": {"value": str, "confidence": float, "source_quote": str},\n'
        '  "invoice_number": {"value": str, "confidence": float, "source_quote": str},\n'
        '  "subtotal": {"value": str, "confidence": float, "source_quote": str},\n'
        '  "tax": {"value": str, "confidence": float, "source_quote": str},\n'
        '  "total": {"value": str, "confidence": float, "source_quote": str},\n'
        '  "totals": {"subtotal": float, "tax": float, "total_amount": float, "currency": str, "confidence": float, "source_quote": str},\n'
        '  "dates": [{"field": str, "value": str, "confidence": float, "source_quote": str}],\n'
        '  "line_items": [{"description": str, "quantity": float, "unit_price": float, "total": float, "confidence": float, "source_quote": str}],\n'
        '  "parties": [{"role": str, "name": str, "confidence": float, "source_quote": str}]\n'
        "}"
    )

    prompt = f"Document Type: {doc_type}\n\nDocument Text:\n{redacted_prompt_text}"

    raw_result = call_llm(prompt, system_instruction=system_prompt, json_mode=True)
    if not raw_result or not isinstance(raw_result, dict):
        return None

    # Anti-Hallucination Verification Pass
    verified_data = {}
    dropped_fields = []

    # 1. Single scalar dictionary fields
    scalar_fields = ["vendor", "invoice_number", "subtotal", "tax", "total", "totals"]
    for field_name in scalar_fields:
        f_val = raw_result.get(field_name)
        if isinstance(f_val, dict):
            quote = f_val.get("source_quote") or ""
            if verify_source_quote(quote, text):
                verified_data[field_name] = f_val
            else:
                claimed = f_val.get("value") or f_val.get("total_amount") or f_val.get("subtotal") or str(f_val)
                dropped_fields.append({
                    "field": field_name,
                    "claimed_value": claimed,
                    "reason": "Source quote could not be verified in original document text."
                })

    # If totals was verified and subtotal/tax/total are missing at top level, populate from totals
    if "totals" in verified_data:
        tot = verified_data["totals"]
        tot_quote = tot.get("source_quote", "")
        tot_conf = tot.get("confidence", 0.9)
        if "subtotal" not in verified_data and "subtotal" in tot and tot["subtotal"] is not None:
            verified_data["subtotal"] = {
                "value": str(tot["subtotal"]),
                "confidence": tot_conf,
                "source_quote": tot_quote
            }
        if "tax" not in verified_data and "tax" in tot and tot["tax"] is not None:
            verified_data["tax"] = {
                "value": str(tot["tax"]),
                "confidence": tot_conf,
                "source_quote": tot_quote
            }
        if "total" not in verified_data:
            val = tot.get("total_amount") if tot.get("total_amount") is not None else tot.get("total")
            if val is not None:
                verified_data["total"] = {
                    "value": str(val),
                    "confidence": tot_conf,
                    "source_quote": tot_quote
                }

    # 2. List fields (dates, line_items, parties)
    for list_field in ["dates", "line_items", "parties"]:
        items = raw_result.get(list_field)
        if isinstance(items, list):
            verified_list = []
            for item in items:
                if isinstance(item, dict):
                    quote = item.get("source_quote") or ""
                    if verify_source_quote(quote, text):
                        # Ensure confidence is present
                        if "confidence" not in item:
                            item["confidence"] = 0.9
                        verified_list.append(item)
                    else:
                        dropped_fields.append({
                            "field": list_field,
                            "claimed_value": item.get("value") or item.get("description") or item.get("name"),
                            "reason": "Source quote not grounded in document text."
                        })
            if verified_list:
                verified_data[list_field] = verified_list

    provider = getattr(Config, 'VEXORA_LLM_PROVIDER', 'gemini')

    # Persist to database if document_id is provided
    if document_id:
        try:
            from backend.models import log_audit
            from backend.database import execute_db
            insight_id = f"INS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{document_id[:8]}"
            execute_db(
                """
                INSERT OR REPLACE INTO ai_insights (id, document_id, insight_type, data, model_provider, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    insight_id,
                    document_id,
                    'field_extraction',
                    json.dumps(verified_data),
                    provider,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )
            log_audit(
                "AI_FIELD_EXTRACTION",
                "document",
                document_id,
                f"LLM extracted {len(verified_data)} grounded field categories ({len(dropped_fields)} ungrounded dropped).",
                user
            )
        except Exception as e:
            logger.warning(f"[LLM Storage Error] Failed to persist AI insights: {e}")

    return {
        "success": True,
        "fields": verified_data,
        "dropped_fields": dropped_fields,
        "provider": provider,
        "disclaimer": AI_DISCLAIMER
    }


# =====================================================================
# 4. Core Feature 2: Finding Explanation with Innocent Hypotheses
# =====================================================================

def explain_finding(finding, nearby_text="", document_id=None, user="System"):
    """
    Generates a 2-4 sentence plain-language explanation of why a finding needs review,
    which innocent alternative hypotheses exist, and what concrete steps to verify next.
    Must refer strictly to supplied text and evidence.
    Never asserts confirmed fraud.
    """
    if not finding or not isinstance(finding, dict):
        return None

    rule_id = finding.get('rule_id', 'UNKNOWN')
    title = finding.get('title', 'Forensic Observation')
    desc = finding.get('description', '')
    evidence = finding.get('evidence', '')

    context_sample = nearby_text[:3000] if nearby_text else ""
    redacted_context = redact_text_for_llm(context_sample)

    system_prompt = (
        "You are an objective, senior forensic document intelligence assistant. "
        "Explain an automated technical document observation in 2 to 4 concise sentences. "
        "Strictly adhere to the following rules:\n"
        "1. Clearly explain why this anomaly pattern warrants human scrutiny.\n"
        "2. State at least one plausible innocent explanation (such as software upgrade, print driver formatting, scanner glitch, or legitimate amendment).\n"
        "3. Provide one concrete verification action the reviewer should take next.\n"
        "4. NEVER say 'confirmed fraud', 'forgery', or 'criminal'. Maintain strictly neutral, objective language.\n"
        "Return a valid JSON object with the schema:\n"
        "{\n"
        '  "explanation": "2-4 sentences explaining why this requires review...",\n'
        '  "innocent_hypotheses": ["Plausible non-fraud explanation 1", "..."],\n'
        '  "next_verification_step": "Exact physical/digital check to perform..."\n'
        "}"
    )

    user_prompt = (
        f"Rule ID: {rule_id}\n"
        f"Observation Title: {title}\n"
        f"Technical Description: {desc}\n"
        f"Measured Evidence: {evidence}\n"
        f"Surrounding Document Text:\n{redacted_context}"
    )

    res = call_llm(user_prompt, system_instruction=system_prompt, json_mode=True)
    if not res or not isinstance(res, dict):
        return None

    # Audit logging
    try:
        from backend.models import log_audit
        log_audit(
            "AI_FINDING_EXPLAINED",
            "finding",
            finding.get('id', rule_id),
            f"Generated AI contextual explanation for rule [{rule_id}].",
            user
        )
    except Exception:
        pass

    return {
        "finding_id": finding.get('id'),
        "rule_id": rule_id,
        "explanation": res.get("explanation", "").strip(),
        "innocent_hypotheses": res.get("innocent_hypotheses", []),
        "next_verification_step": res.get("next_verification_step", "").strip(),
        "disclaimer": AI_DISCLAIMER
    }


# =====================================================================
# 5. Core Feature 3: Contextual Cross-Check Across Case Documents
# =====================================================================

def contextual_crosscheck(case_documents, case_id=None, user="System"):
    """
    Performs multi-document reasoning to identify contextual, logical, and arithmetic
    inconsistencies (totals vs line items, contradictory parties, impossible dates).
    Enforces quote verification to eliminate hallucinations.
    Returns findings with rule IDs LLM-001 onwards, clearly labeled 'AI-assessed, requires human review'.
    Never replaces rule-based findings (purely additive).
    """
    if not case_documents or not isinstance(case_documents, list):
        return []

    # Compile document excerpts
    doc_payloads = []
    full_text_map = {}

    for doc in case_documents:
        d_id = doc.get('id', 'Unknown')
        text = doc.get('extracted_text') or ""
        full_text_map[d_id] = text
        redacted_sample = redact_text_for_llm(text[:4000])
        doc_payloads.append({
            "document_id": d_id,
            "filename": doc.get('filename', ''),
            "category": doc.get('category', 'Document'),
            "text_sample": redacted_sample
        })

    system_prompt = (
        "You are an advanced AI contextual audit engine. "
        "Analyze the set of investigation documents specifically for four categories of discrepancies:\n"
        "1. Totals that do not equal the sum of line items (subtotal + tax != grand total, line items sum != subtotal)\n"
        "2. Mismatched parties across documents (differing vendor names, customer names, or bank account identities across related records)\n"
        "3. Impossible timelines (chronological sequence violations such as shipping before order, invoice paid before issue, or future dates)\n"
        "4. Amounts that differ across documents for the same transaction, order, or invoice reference\n\n"
        "CRITICAL REQUIREMENT: For EVERY inconsistency identified, you MUST provide an exact 'source_quote' "
        "copied directly from the text of the involved document. If you cannot quote it verbatim, do not report it.\n"
        "Return a valid JSON object:\n"
        "{\n"
        '  "inconsistencies": [\n'
        '    {\n'
        '      "title": "Short descriptive title of discrepancy",\n'
        '      "document_id": "Document ID where quote appears",\n'
        '      "severity": "Medium" | "High",\n'
        '      "description": "2-3 sentences explaining the logical conflict...",\n'
        '      "source_quote": "Exact verbatim quote from text",\n'
        '      "recommendation": "What the reviewer should check..."\n'
        '    }\n'
        '  ]\n'
        "}"
    )

    prompt = f"Case Documents:\n{json.dumps(doc_payloads, indent=2)}"

    res = call_llm(prompt, system_instruction=system_prompt, json_mode=True, timeout=20)
    if not res or not isinstance(res, dict):
        return []

    raw_inconsistencies = res.get("inconsistencies", [])
    if not isinstance(raw_inconsistencies, list):
        return []

    verified_findings = []
    llm_idx = 1

    for item in raw_inconsistencies:
        if not isinstance(item, dict):
            continue

        doc_id = item.get("document_id")
        quote = item.get("source_quote") or ""
        target_text = full_text_map.get(doc_id, "")

        # Strict anti-hallucination verification
        if not verify_source_quote(quote, target_text):
            logger.info(f"[LLM CrossCheck] Discarded ungrounded finding '{item.get('title')}'")
            continue

        rule_id = f"LLM-{llm_idx:03d}"
        llm_idx += 1

        finding_dict = {
            'rule_id': rule_id,
            'title': f"[AI] {item.get('title', 'Contextual Discrepancy Detected')}",
            'severity': item.get('severity', 'Medium'),
            'category': 'Contextual Intelligence',
            'status': 'Observation',
            'evidence_class': 'Inconsistency',
            'confidence': 0.86,
            'document_id': doc_id,
            'case_id': case_id,
            'page_number': 1,
            'coordinates': None,
            'description': (
                f"{item.get('description', '')} "
                f"[{AI_DISCLAIMER}]."
            ),
            'evidence': f"Grounded quote: \"{quote}\"",
            'recommendation': item.get('recommendation', 'Cross-examine source transaction documents.')
        }

        verified_findings.append(finding_dict)

    # Persist findings to database if case_id is provided
    if case_id and verified_findings:
        try:
            from backend.models import create_finding, log_audit
            from backend.database import query_db
            for f in verified_findings:
                payload = dict(f)
                d_id = payload.get('document_id')
                if d_id:
                    exists = query_db("SELECT id FROM documents WHERE id = ?", (d_id,), one=True)
                    if not exists:
                        payload['document_id'] = None
                create_finding(payload, user=user)
            log_audit(
                "AI_CROSSCHECK_COMPLETED",
                "case",
                case_id,
                f"Generated {len(verified_findings)} grounded contextual cross-check findings.",
                user
            )
        except Exception as e:
            logger.warning(f"[LLM Storage Error] Failed to persist crosscheck findings: {e}")

    return verified_findings


# =====================================================================
# 6. System Status Reporter
# =====================================================================

def get_ai_status():
    """
    Returns current LLM subsystem telemetry without leaking secrets.
    """
    enabled = getattr(Config, 'ENABLE_LLM', False)
    provider = getattr(Config, 'VEXORA_LLM_PROVIDER', 'gemini')
    api_key = getattr(Config, 'VEXORA_LLM_API_KEY', '') or os.environ.get('VEXORA_LLM_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '') or os.environ.get('OPENAI_API_KEY', '')
    has_key = bool(api_key and len(api_key.strip()) > 5)
    redact = getattr(Config, 'VEXORA_LLM_REDACT', True)
    model_name = get_model_name(provider)

    return {
        "enabled": bool(enabled and has_key),
        "feature_flag_enabled": bool(enabled),
        "has_api_key": has_key,
        "provider": provider,
        "model": model_name,
        "privacy_redaction_enabled": bool(redact),
        "disclaimer": AI_DISCLAIMER
    }


def test_ai_connection(prompt="PING"):
    """
    Sends a minimal harmless prompt to test live LLM connectivity.
    Returns dictionary with:
    - ok: bool
    - provider: str
    - model: str
    - latency_ms: float
    - error: str (only on failure; never leaks api keys)
    - disclaimer: str
    """
    import time
    provider = getattr(Config, 'VEXORA_LLM_PROVIDER', 'gemini').lower().strip()
    model = get_model_name(provider)

    enabled = getattr(Config, 'ENABLE_LLM', False)
    if not enabled:
        return {
            'ok': False,
            'provider': provider,
            'model': model,
            'latency_ms': 0.0,
            'error': 'AI reasoning is disabled. Set ENABLE_LLM=true in environment or .env.',
            'disclaimer': AI_DISCLAIMER
        }

    api_key = (
        getattr(Config, 'VEXORA_LLM_API_KEY', '')
        or os.environ.get('VEXORA_LLM_API_KEY', '')
        or os.environ.get('GEMINI_API_KEY', '')
        or os.environ.get('OPENAI_API_KEY', '')
    )
    if not api_key or len(api_key.strip()) < 5:
        return {
            'ok': False,
            'provider': provider,
            'model': model,
            'latency_ms': 0.0,
            'error': f'API key not configured for provider "{provider}". Set VEXORA_LLM_API_KEY in environment or .env.',
            'disclaimer': AI_DISCLAIMER
        }

    if requests is None:
        return {
            'ok': False,
            'provider': provider,
            'model': model,
            'latency_ms': 0.0,
            'error': "'requests' library is not available.",
            'disclaimer': AI_DISCLAIMER
        }

    start_time = time.time()
    try:
        set_last_llm_error(None)
        res = call_llm(prompt, json_mode=False, timeout=12)
        latency = round((time.time() - start_time) * 1000, 1)

        if res is not None:
            return {
                'ok': True,
                'provider': provider,
                'model': model,
                'latency_ms': latency,
                'response_sample': str(res)[:60].strip(),
                'disclaimer': AI_DISCLAIMER
            }
        else:
            err = get_last_llm_error() or f"Connection failed to {provider} ({model}). Check network, key, or model name."
            if api_key:
                err = err.replace(api_key, "[REDACTED_KEY]")
            return {
                'ok': False,
                'provider': provider,
                'model': model,
                'latency_ms': latency,
                'error': err,
                'disclaimer': AI_DISCLAIMER
            }
    except Exception as e:
        latency = round((time.time() - start_time) * 1000, 1)
        err_msg = str(e)
        if api_key:
            err_msg = err_msg.replace(api_key, "[REDACTED_KEY]")
        return {
            'ok': False,
            'provider': provider,
            'model': model,
            'latency_ms': latency,
            'error': err_msg,
            'disclaimer': AI_DISCLAIMER
        }
