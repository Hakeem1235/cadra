from __future__ import annotations

from app.schemas import CheckResultValue, CheckResult, EvidenceItem
from app.tools import bank as bank_tool


def run(request_type: str, folio_no: str, bank_mandates: dict) -> CheckResult:
    if request_type != "REDEMPTION":
        return CheckResult(check_id="BANK_MANDATE", result=CheckResultValue.NOT_APPLICABLE)
    validated = bank_tool.get_validated(folio_no, bank_mandates)
    if not validated:
        return CheckResult(
            check_id="BANK_MANDATE", result=CheckResultValue.FAIL,
            evidence=[EvidenceItem("bank_mandates.csv", folio_no, "No VALIDATED account for payout")],
            reason_codes=["BANK_NO_VALIDATED_MANDATE"]
        )
    default = bank_tool.get_default(folio_no, bank_mandates)
    if default and default.status != "VALIDATED":
        return CheckResult(
            check_id="BANK_MANDATE", result=CheckResultValue.FAIL,
            evidence=[EvidenceItem(source="bank_mandates.csv", ref=default.account_no_masked, value=f"Default account status={default.status}")],
            reason_codes=["BANK_DEFAULT_NOT_VALIDATED"]
        )
    return CheckResult(check_id="BANK_MANDATE", result=CheckResultValue.PASS)