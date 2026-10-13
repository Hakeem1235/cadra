from __future__ import annotations

import re
import json
from app.schemas import ExtractedRequest, RequestType
from app.trace import TraceCollector


FOLIO_PAT = re.compile(r"(?:folio|folio\s*no|folio no\.)[\s#:.\-/]+(\d{8,10}(?:\s*[/\-]\s*\d{2})?)", re.I)
FOLIO_PAT_RAW = re.compile(r"(?<!\d)(\d{10})(?!\d)")
FOLIO_PAT_DASH = re.compile(r"(\d{8})[ \-\/](\d{2})")
PAN_PAT = re.compile(r"[A-Z]{5}\d{4}[A-Z](?!\d)", re.I)
UTR_PAT = re.compile(r"UTR[:\s]*([A-Z0-9]+)", re.I)
AMOUNT_PAT = re.compile(r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)", re.I)
ARN_PAT = re.compile(r"ARN\s*:?\s*([A-Z0-9]{6,})", re.I)
EUIN_PAT = re.compile(r"EUIN\s*:?\s*([A-Z0-9]{6,})", re.I)


def regex_prepass(text: str) -> dict:
    folio = _match_first(FOLIO_PAT, text)
    if not folio:
        raw = _match_first(FOLIO_PAT_RAW, text)
        if raw:
            folio = raw
    if not folio:
        dash = FOLIO_PAT_DASH.search(text)
        if dash:
            folio = f"{dash.group(1)}{dash.group(2)}"
        else:
            # try "40131574-17" split
            m = re.search(r'(\d{8})[\/\-](\d{2})', text)
            if m:
                folio = m.group(1) + m.group(2)
    return {
        "folio_raw": folio,
        "pan": _match_first(PAN_PAT, text),
        "utr": _match_first(UTR_PAT, text),
        "amount_inr": _match_amount(text),
        "arn": _match_first(ARN_PAT, text),
        "euin": _match_first(EUIN_PAT, text),
    }


def _match_first(pat: re.Pattern, text: str) -> str | None:
    m = pat.search(text)
    return m.group(1).strip() if m else None


def _match_amount(text: str) -> float | None:
    m = AMOUNT_PAT.search(text)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


def classify_request_type(subject: str, body: str, text: str = "") -> str:
    combined = f"{subject} {body} {text}".lower()
    if any(w in combined for w in ["change of bank", "change bank", "new bank", "update bank"]):
        return "CHANGE_OF_BANK"
    if any(w in combined for w in ["redemption", "redeem", "withdraw"]):
        return "REDEMPTION"
    if any(w in combined for w in ["sip registration", "new sip", "start sip"]):
        return "SIP_REGISTRATION"
    if any(w in combined for w in ["sip instalment", "sip installment", "monthly sip"]):
        return "SIP_INSTALMENT"
    if any(w in combined for w in ["new folio", "new investment", "first purchase", "new purchase"]):
        return "NEW_FOLIO_PURCHASE"
    if any(w in combined for w in ["additional purchase", "additional", "top up", "further purchase"]):
        return "ADDITIONAL_PURCHASE"
    return "OTHER"


def extract(subject: str, body: str, attachment_texts: list[str], trace: TraceCollector | None = None) -> ExtractedRequest:
    all_text = f"Subject: {subject}\nBody: {body}\n" + "\n".join(attachment_texts)
    regex_data = regex_prepass(all_text)
    request_type_hint = classify_request_type(subject, body, "\n".join(attachment_texts))
    # Try LLM extraction
    try:
        from app.llm import get_llm_client
        llm = get_llm_client()
        prompt = f"""Extract structured data from this email request as JSON.
Subject: {subject}
Body: {body}

Return JSON with these fields (null if not present):
request_type_hint, folio_raw, pan, investor_name, minor_name, scheme_name, plan (REGULAR/DIRECT/null), option, amount_inr, payment_mode, remitter_name, remitter_account_last4, payer_relation_to_investor, utr, arn, euin, txn_date, new_bank_account_last4, new_bank_ifsc, is_cash (bool), execution_only_declaration (bool), sender_role (investor/distributor/employer/relative/other)"""
        llm_out = llm.generate(prompt, trace, json_mode=True)
        llm_data = json.loads(llm_out)
        # Merge: prefer regex for folio/PAN (more precise), LLM for everything else
        folio_raw = regex_data.get("folio_raw") or llm_data.get("folio_raw")
        pan = regex_data.get("pan") or llm_data.get("pan")
        return ExtractedRequest(
            request_type_hint=request_type_hint,
            folio_raw=folio_raw,
            pan=pan,
            investor_name=llm_data.get("investor_name"),
            remitter_name=llm_data.get("remitter_name"),
            remitter_account_last4=llm_data.get("remitter_account_last4"),
            payer_relation_to_investor=llm_data.get("payer_relation_to_investor"),
            utr=regex_data.get("utr") or llm_data.get("utr"),
            arn=regex_data.get("arn") or llm_data.get("arn"),
            euin=regex_data.get("euin") or llm_data.get("euin"),
            amount_inr=regex_data.get("amount_inr") or llm_data.get("amount_inr"),
            is_cash=llm_data.get("is_cash", False),
            execution_only_declaration=llm_data.get("execution_only_declaration", False),
            sender_role=llm_data.get("sender_role"),
        )
    except Exception:
        return ExtractedRequest(
            request_type_hint=request_type_hint,
            folio_raw=regex_data.get("folio_raw"),
            pan=regex_data.get("pan"),
            utr=regex_data.get("utr"),
            arn=regex_data.get("arn"),
            euin=regex_data.get("euin"),
            amount_inr=regex_data.get("amount_inr"),
        )