# VEXORA — AI Reasoning Architecture & Anti-Hallucination Guardrails

**Core Philosophy:** Deterministic Rules Detect Anomaly; AI Explains & Cross-Correlates  
**Default State:** `ENABLE_LLM=False` (100% Offline-Capable & Deterministic)  
**Implementation Modules:** `backend/llm.py`, `backend/app.py`, `frontend/js/app.js`

---

## 1. Architectural Philosophy & Zero-Hallucination Boundary

In forensic document intelligence, **LLMs must never act as ungrounded arbiters of truth**. Large language models are prone to hallucinating facts, misreading numeric amounts, or falsely asserting fraud.

VEXORA resolves this by strictly decoupling detection from explanation:

```
[ Ingested Document ]
       │
       ▼
[ Deterministic Forensic Engine ] ──(SHA-256, PyMuPDF, OpenCV ELA, Cross-Document Rules)
       │
       ▼
[ Verified Forensic Findings ]
       │
       ▼  (Optional / Enabled only when VEXORA_LLM_API_KEY configured)
[ AI Reasoning & Explainability Subsystem ]
       │
       ├── 1. PII Redaction Filter (Masks IBAN, Cards, Aadhaar, SSN)
       ├── 2. Direct HTTPS Dispatcher (Gemini, OpenAI, Claude)
       ├── 3. Anti-Hallucination Quote Verifier (verify_source_quote)
       └── 4. Mandatory Human-Review Disclaimer
```

1. **Rule Engine Detects:** All anomalies (font mismatches, metadata shifts, chronological inversions, payment discrepancies) are detected by deterministic code and OpenCV/PyMuPDF algorithms.
2. **AI Explains:** The LLM's only role is to synthesize plain-language summaries for non-technical investigators, suggest plausible innocent explanations (e.g. print driver glitch, software upgrade), and recommend concrete next verification steps.
3. **Evidence Grounding:** An AI observation is rejected if its cited source quote does not verbatim exist in the document text.

---

## 2. Multi-Provider Direct HTTPS Dispatcher

VEXORA connects directly to cloud LLM APIs using lightweight HTTPS REST requests (`requests.post`), eliminating heavy third-party SDK dependencies:

| Provider | Default Model | Configuration Key | Endpoint URL |
| :--- | :--- | :--- | :--- |
| **Google Gemini** | `gemini-2.5-flash` | `GEMINI_API_KEY` / `VEXORA_LLM_API_KEY` | `https://generativelanguage.googleapis.com/v1beta/models/...` |
| **OpenAI** | `gpt-4o-mini` | `OPENAI_API_KEY` / `VEXORA_LLM_API_KEY` | `https://api.openai.com/v1/chat/completions` |
| **Anthropic Claude** | `claude-3-5-sonnet-20241022` | `ANTHROPIC_API_KEY` / `VEXORA_LLM_API_KEY` | `https://api.anthropic.com/v1/messages` |
| **Local / Offline** | Custom / Ollama | `VEXORA_LLM_PROVIDER=local` | Local endpoint fallback |

---

## 3. Anti-Hallucination Grounding Engine

### 3.1 Verbatim Source Quote Verification (`verify_source_quote`)
When contextual cross-checking identifies a multi-document discrepancy, the model must output a `source_quote` representing the exact text snippet in the document supporting its finding.

`verify_source_quote(source_quote, original_text)`:
1. Normalizes whitespace and case across both strings.
2. Performs direct substring search.
3. Applies a fallback punctuation-stripped search to account for minor OCR glyph boundaries.
4. If the quote is not found in the original document $\rightarrow$ **The finding is permanently dropped**. Phantom AI hallucinations cannot enter the case dossier.

### 3.2 Finding Grounding Verification
`POST /api/findings/<id>/explain`:
- Verifies that `finding_id` exists in the case database and is accessible under current RBAC.
- Passes the actual detected rule ID, severity, and nearby verbatim text block to the explanation generator.
- The model prompt strictly forbids using accusatory terms ("criminal", "fraudster", "forgery") and requires stating at least one innocent alternative hypothesis.

---

## 4. Privacy & PII Redaction Layer

Before any document excerpt is transmitted over HTTPS to an external model, `redact_text_for_llm(text)` applies regex-based privacy masking:

- **IBANs:** Replaced with `[REDACTED_IBAN]`
- **Credit / Debit Cards:** Replaced with `[REDACTED_CARD]`
- **Indian Aadhaar Numbers:** Replaced with `[REDACTED_AADHAAR]`
- **US Social Security Numbers:** Replaced with `[REDACTED_SSN]`
- **Email Addresses:** Replaced with `[REDACTED_EMAIL]`
- **Phone Numbers:** Replaced with `[REDACTED_PHONE]`

Tested and verified in `tests/test_explainability_privacy.py` (`test_01_extended_pii_redaction`).

---

## 5. Resilience to API Failures & Timeouts

The AI subsystem operates with defensive error isolation:
- **Missing API Key:** Returns `None` immediately; records user-friendly status in `/api/system/ai-status` without crashing.
- **HTTP 401 Unauthorized:** Catches invalid API keys, sanitizes error message, and prevents retries.
- **HTTP 429 Rate Limiting:** Catches quota exhaustion gracefully; logs notice and falls back to deterministic summary.
- **Timeouts:** Enforces 30-second strict request timeout. Transient network drops attempt 1 exponential backoff retry before failing cleanly.
- **Malformed JSON:** Employs `_parse_json_block()` capable of stripping markdown fences (` ```json `), fixing trailing commas in lists and dicts, and discarding conversational preambles.

---

## 6. Transparent Human-in-the-Loop Disclaimers

Every AI-derived finding, explanation, and extraction is stamped with a mandatory disclaimer:
> *"AI-assessed, requires human review. AI-generated rationale. Must be verified against primary evidence before investigative escalation."*

In the frontend UI:
- AI-generated explanations are visually distinguished with purple/gold `[AI Assessed]` badges.
- Disclaimers are displayed prominently alongside the innocent alternative hypothesis and recommended verification action.

