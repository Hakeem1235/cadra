from __future__ import annotations

from app.schemas import Outcome, CheckResult, CheckResultValue, ApproverRole


OUTCOME_ORDER = {
    Outcome.INVALID_REQUEST: 0,
    Outcome.REJECT: 1,
    Outcome.HOLD_AND_REFER: 2,
    Outcome.PEND: 3,
    Outcome.PROCEED_MODIFIED: 4,
    Outcome.PROCEED: 5,
}

_HOLD_REASONS = {"STOP_LOCK", "REFERRAL_TRIGGER", "HIGH_RISK_CONTACT_COB"}
_REJECT_REASONS = {"KYC_ON_HOLD", "KYC_REJECTED", "TPP_NO_EXCEPTION", "CASH_LIMIT_BREACH", "FOLIO_NOT_FOUND", "FOLIO_PAN_MISMATCH"}
_MODIFIED_REASONS = {"ARN_INVALID_DIRECT"}
_PEND_REASONS = {"COB_COOLING", "KYC_UNABLE_TO_VERIFY", "KYC_REGISTERED_NEW_AMC", "TPP_DOCS_MISSING", "BANK_PROOF_REQUIRED", "MINOR_ATTAINED_MAJORITY", "TPP_UNABLE_TO_VERIFY"}


def decide(checks: list[CheckResult], is_invalid: bool = False) -> tuple[Outcome, list[str], bool, str | None]:
    reason_codes = []
    for c in checks:
        reason_codes.extend(c.reason_codes)
    outcomes_available = set()
    if is_invalid:
        outcomes_available.add(Outcome.INVALID_REQUEST)
    for c in checks:
        if c.result == CheckResultValue.FAIL:
            codes = set(c.reason_codes)
            if codes & _HOLD_REASONS:
                outcomes_available.add(Outcome.HOLD_AND_REFER)
            elif codes & _REJECT_REASONS:
                outcomes_available.add(Outcome.REJECT)
            elif codes & _MODIFIED_REASONS:
                outcomes_available.add(Outcome.PROCEED_MODIFIED)
            elif codes & _PEND_REASONS:
                outcomes_available.add(Outcome.PEND)
            else:
                outcomes_available.add(Outcome.REJECT)
        if c.result == CheckResultValue.UNABLE_TO_VERIFY:
            outcomes_available.add(Outcome.PEND)
    if not outcomes_available:
        outcomes_available.add(Outcome.PROCEED)
    selected = min(outcomes_available, key=lambda o: OUTCOME_ORDER.get(o, 99))
    if selected in (Outcome.PROCEED, Outcome.PEND, Outcome.INVALID_REQUEST):
        approver = (None, False)
    elif selected in (Outcome.PROCEED_MODIFIED, Outcome.REJECT):
        approver = (ApproverRole.CHECKER, True)
    elif selected == Outcome.HOLD_AND_REFER:
        approver = (ApproverRole.OPS_MANAGER, True)
    else:
        approver = (None, False)
    return selected, list(dict.fromkeys(reason_codes)), approver[1], approver[0].value if approver[0] else None