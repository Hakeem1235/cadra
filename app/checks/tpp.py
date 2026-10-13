from __future__ import annotations

from app.schemas import CheckResultValue, CheckResult, EvidenceItem, AmcCode
from app.tools import folio as folio_tool, bank as bank_tool


def run(request_type: str, remitter_name: str | None, remitter_account_last4: str | None,
        payer_relation: str | None, folio_record, folio_no: str, bank_mandates: dict,
        is_minor: bool) -> CheckResult:
    if request_type in ("REDEMPTION", "CHANGE_OF_BANK"):
        return CheckResult(check_id="THIRD_PARTY_PAYMENT", result=CheckResultValue.NOT_APPLICABLE)
    if not remitter_account_last4:
        return CheckResult(check_id="THIRD_PARTY_PAYMENT", result=CheckResultValue.UNABLE_TO_VERIFY,
                           reason_codes=["TPP_UNABLE_TO_VERIFY"],
                           evidence=[EvidenceItem(source="transaction data", ref="remitter_account", value="No remitter account provided")])
    mandate = bank_tool.find_by_account(remitter_account_last4, folio_no, bank_mandates)
    if mandate:
        # Check if first holder is in account holders
        first_holder = folio_record.first_holder_name if folio_record else ""
        holders = (mandate.account_holders or "").lower()
        if first_holder and first_holder.lower() in holders:
            return CheckResult(check_id="THIRD_PARTY_PAYMENT", result=CheckResultValue.PASS)
    # Check if this is a minor folio with parent/guardian
    if is_minor and payer_relation and payer_relation.lower() in ("father", "mother", "legal guardian"):
        return CheckResult(check_id="THIRD_PARTY_PAYMENT", result=CheckResultValue.PASS)
    if is_minor:
        return CheckResult(check_id="THIRD_PARTY_PAYMENT", result=CheckResultValue.FAIL,
                           sop_clause="TCC-SOP v4.1 5.4",
                           reason_codes=["TPP_NO_EXCEPTION"],
                           evidence=[EvidenceItem(source="policy", ref="5.4", value="Grandparent/other relative not allowed for minor folios")])
    return CheckResult(check_id="THIRD_PARTY_PAYMENT", result=CheckResultValue.FAIL,
                       reason_codes=["TPP_NO_EXCEPTION"])