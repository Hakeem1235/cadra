from __future__ import annotations

from app.schemas import CheckResultValue, CheckResult, EvidenceItem, AmcCode
from app.tools import kra as kra_tool, folio as folio_tool


def run(pan: str | None, request_type: str, folio_record, amc_code: AmcCode | None, kra_store: dict) -> CheckResult:
    if not pan:
        return CheckResult(
            check_id="KYC_STATUS", result=CheckResultValue.UNABLE_TO_VERIFY,
            reason_codes=["KYC_UNABLE_TO_VERIFY"]
        )
    kra_entry, evidence = kra_tool.lookup(pan, kra_store)
    if kra_entry is None:
        return CheckResult(
            check_id="KYC_STATUS", result=CheckResultValue.UNABLE_TO_VERIFY,
            evidence=evidence, reason_codes=["KYC_UNABLE_TO_VERIFY"]
        )
    status, reason, status_evidence = kra_tool.derive_status(kra_entry)
    evidence.extend(status_evidence)
    if status == "VALIDATED":
        return CheckResult(check_id="KYC_STATUS", result=CheckResultValue.PASS, evidence=evidence, sop_clause="TCC-SOP v4.1 4.2")
    if status == "REGISTERED":
        return CheckResult(check_id="KYC_STATUS", result=CheckResultValue.PASS, evidence=evidence, sop_clause="TCC-SOP v4.1 4.2",
                           reason_codes=["KYC_REGISTERED"])
    if status in ("ON_HOLD", "REJECTED"):
        if request_type in ("REDEMPTION",):
            return CheckResult(check_id="KYC_STATUS", result=CheckResultValue.FAIL, evidence=evidence,
                               sop_clause="TCC-SOP v4.1 4.4", reason_codes=[f"KYC_{status.replace(' ', '_')}"])
        return CheckResult(check_id="KYC_STATUS", result=CheckResultValue.FAIL, evidence=evidence,
                           sop_clause="TCC-SOP v4.1 4.4", reason_codes=[f"KYC_{status.replace(' ', '_')}"])
    return CheckResult(
        check_id="KYC_STATUS", result=CheckResultValue.UNABLE_TO_VERIFY,
        evidence=evidence, reason_codes=["KYC_UNABLE_TO_VERIFY"]
    )