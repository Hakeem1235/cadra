# Approach — TCC Compliance Agent

## Problem Summary

Automate the Validus TCC (Transaction Compliance Check) desk — a mutual-fund RTA operation processing ~1,800 email requests/day (purchases, redemptions, SIPs, change-of-bank). Currently a maker spends ~11 minutes per request opening 5 system screens plus a rulebook, running 8 compliance checks, deciding the outcome, and drafting a reply; then a checker spends ~3 minutes approving. The system replaces this with a FastAPI HTTP service that returns a proposed decision + trace in seconds, leaving humans only where the SOP reserves the decision.

## Technical Approach

**Architecture:** 8-stage deterministic pipeline (S1–S8) orchestrated by `app/pipeline.py`:

1. **S1 Intake** (`app/s1_intake.py`): Decode base64 attachments — PDF via pdfplumber, DOCX via python-docx, images via vision LLM
2. **S2 Extract** (`app/s2_extract.py`): Regex pre-pass for folio/PAN/UTR/ARN/EUIN/amount, then LLM JSON extraction (with retry on invalid JSON); keyword classifier for request_type
3. **S3 Resolve** (`app/s3_resolve.py`): Folio normalise (10 digits → 8/2 split), exact lookup in folio_master, PAN cross-check, PENDING_TCC transaction match
4. **S4 Policy** (`app/policy/selector.py`): Deterministic version selection by `received_at ≥ effective_from`; addendum applied for TMF folios. Rules in `app/policy/rules.yaml`
5. **S5 Checks** (`app/checks/*.py`): 8 independent checks — each a pure function returning CheckResult(PASS/FAIL/NOT_APPLICABLE/UNABLE_TO_VERIFY) + evidence
6. **S6 Decide** (`app/s6_decide.py`): Precedence 9.2 (INVALID > REJECT > HOLD > PEND > MODIFIED > PROCEED) + Annexure A approver roles
7. **S7 Reply** (`app/s7_reply.py`): Template-based reply builder with banned-word guard for HOLD cases; LLM drafting optional
8. **S8 Trace** (`app/trace.py`): Collector records model calls, tokens, tools, documents, cost

**Data layer:** 5 CSV extracts loaded at startup into an in-memory `DataStore` — no database dependency. Build step (`scripts/prepare_data.py`) detects data issues and logs them.

**Key design choices:**
- LLM never decides the outcome — used only for extraction, OCR, and reply drafting
- No fuzzy matching on identifiers — folio not found = INVALID_REQUEST
- Every non-PROCEED outcome cites a clause + evidence
- Always returns a contract-valid response (never HTTP 500)

## AI Tool Usage

The system uses an LLM (Gemini via `app/llm.py`) for three narrow tasks:
1. **Email field extraction** — JSON-mode output from free-text email body, retry once on invalid JSON; regex results override LLM for critical fields (folio, PAN)
2. **Image transcription** — JPEG/PNG attachment text extraction via vision LLM
3. **Reply drafting** — LLM generates reply from outcome + reasons + clause text; template fallback on failure

All other logic is deterministic Python — checks, outcome precedence, approver selection, version selection.

## Trade-offs & Limitations

- **No persistence:** Data store is in-memory (CSV-at-startup); no database means no querying or audit history. Acceptable for API-first eval; a real deployment would use SQLite/Postgres.
- **No fuzzy matching:** A typo in folio number → INVALID_REQUEST. Intentionally strict per spec, but reduces automation rate. A real system might add a controlled human-in-loop "did you mean?" step.
- **Version selection is rule-based:** Adding a new SOP version requires a code change to `selector.py` and `rules.yaml`. A policy-update assistant was designed but not built.
- **LLM dependency for full automation:** Without LLM key, extraction is regex-only (fragile), images cannot be read, and replies are templates. The API still functions but with reduced coverage.
- **No auth:** API is public — no authentication layer. Acceptable for eval; production would need API key or OAuth
- **Full eval set incomplete:** Only 18 unit tests exist; the full 30+ eval cases for every reason code are not yet written