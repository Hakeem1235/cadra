from __future__ import annotations

from app.schemas import Outcome, DraftReply
from app.trace import TraceCollector


BANNED_WORDS = ["referral", "suspicious", "compliance", "fiu", "report", "referred", "investigation"]


def draft(outcome: Outcome, reason_codes: list[str], checks: list, resolved_info, extracted, request: "RequestIn", trace: TraceCollector | None = None) -> DraftReply:
    to_addr = request.from_
    subject = f"Re: {request.subject}"
    # Build body
    body = _template_body(outcome, reason_codes, checks, resolved_info, extracted)
    # Guard: for HOLD/referred cases, check banned words
    if outcome == Outcome.HOLD_AND_REFER:
        for bw in BANNED_WORDS:
            if bw in body.lower():
                body = _safe_hold_body()
    return DraftReply(to=to_addr, subject=subject, body=body)


def _template_body(outcome: Outcome, reason_codes: list[str], checks, resolved_info, extracted) -> str:
    folio = resolved_info.folio_no or "your folio"
    lines = [f"Dear Investor,"]
    lines.append(f"")
    if outcome == Outcome.PROCEED:
        lines.append(f"Your request regarding folio {folio} has been processed successfully.")
    elif outcome == Outcome.REJECT:
        lines.append(f"We regret to inform you that your request regarding folio {folio} could not be accepted for the following reason(s):")
        for rc in reason_codes:
            lines.append(f"- {rc}")
        lines.append(f"The amount will be refunded to the remitting account.")
    elif outcome == Outcome.PEND:
        lines.append(f"Your request regarding folio {folio} is currently pending. We require the following:")
        for rc in reason_codes:
            lines.append(f"- {rc}")
        lines.append(f"Please send the required documents to proceed.")
    elif outcome == Outcome.PROCEED_MODIFIED:
        lines.append(f"Your request regarding folio {folio} has been processed with modifications.")
        for rc in reason_codes:
            lines.append(f"- {rc}")
    elif outcome == Outcome.HOLD_AND_REFER:
        lines.append(f"Your request regarding folio {folio} is under processing. We will provide an update shortly.")
    elif outcome == Outcome.INVALID_REQUEST:
        lines.append(f"We are unable to process your request regarding folio {folio}. Please check the folio details and try again.")
    lines.append(f"")
    lines.append(f"Regards,")
    lines.append(f"TCC Desk - Validus")
    return "\n".join(lines)


def _safe_hold_body() -> str:
    return "Dear Investor,\n\nYour request is under processing. We will provide an update shortly.\n\nRegards,\nTCC Desk - Validus"