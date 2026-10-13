from __future__ import annotations

from datetime import datetime, date
from app.schemas import CheckResultValue, CheckResult, EvidenceItem
from app.tools import folio as folio_tool


def run(folio_record, request_type: str, received_at: datetime) -> CheckResult:
    if not folio_record:
        return CheckResult(check_id="MINOR_RULES", result=CheckResultValue.NOT_APPLICABLE)
    if not folio_tool.is_minor(folio_record):
        return CheckResult(check_id="MINOR_RULES", result=CheckResultValue.NOT_APPLICABLE)
    # Check if minor attained majority
    if folio_record.minor_dob:
        try:
            dob = datetime.strptime(folio_record.minor_dob.split(" ")[0], "%Y-%m-%d").date() if " " in (folio_record.minor_dob or "") else datetime.strptime(folio_record.minor_dob, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            dob = None
        if dob:
            eighteenth = date(dob.year + 18, dob.month, dob.day)
            if received_at.date() >= eighteenth:
                return CheckResult(
                    check_id="MINOR_RULES", result=CheckResultValue.FAIL,
                    evidence=[EvidenceItem(source="folio_master.csv", ref=folio_record.folio_no, value=f"Minor DOB {dob}, 18th birthday {eighteenth}")],
                    reason_codes=["MINOR_ATTAINED_MAJORITY"], sop_clause="TCC-SOP v4.1 5.5"
                )
    if request_type in ("REDEMPTION", "CHANGE_OF_BANK"):
        return CheckResult(check_id="MINOR_RULES", result=CheckResultValue.FAIL,
                           reason_codes=["MINOR_RESTRICTED"],
                           sop_clause="TCC-SOP v4.1")
    return CheckResult(check_id="MINOR_RULES", result=CheckResultValue.PASS)