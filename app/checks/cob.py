from __future__ import annotations

from datetime import datetime, timedelta
from app.schemas import CheckResultValue, CheckResult, EvidenceItem
from app.tools import bank as bank_tool


def run(request_type: str, folio_no: str, received_at: datetime, bank_mandates: dict,
        contact_last_changed_on: str | None) -> CheckResult:
    if request_type != "REDEMPTION" and request_type != "CHANGE_OF_BANK":
        return CheckResult(check_id="COB_COOLING", result=CheckResultValue.NOT_APPLICABLE)
    mandates = bank_tool.accounts(folio_no, bank_mandates)
    cob_dates = []
    for m in mandates:
        if m.cob_request_received_on:
            cob_date = datetime.strptime(m.cob_request_received_on.split(" ")[0], "%Y-%m-%d").date() if " " in (m.cob_request_received_on or "") else datetime.strptime(m.cob_request_received_on, "%Y-%m-%d").date()
            cob_dates.append(cob_date)
    if not cob_dates:
        return CheckResult(check_id="COB_COOLING", result=CheckResultValue.PASS)
    latest_cob = max(cob_dates)
    days_diff = (received_at.date() - latest_cob).days
    # Return HIGH_RISK first if contact changed within 30 days before COB + redemption within cooling
    if request_type in ("REDEMPTION", "CHANGE_OF_BANK") and contact_last_changed_on and days_diff <= 10:
        try:
            contact_date = datetime.strptime(contact_last_changed_on.split(" ")[0], "%Y-%m-%d").date() if " " in (contact_last_changed_on or "") else datetime.strptime(contact_last_changed_on, "%Y-%m-%d").date()
            if 0 <= (latest_cob - contact_date).days <= 30:
                return CheckResult(
                    check_id="COB_COOLING", result=CheckResultValue.FAIL,
                    evidence=[EvidenceItem(source="folio_master.csv", ref=folio_no, value=f"Contact changed {contact_date}, COB {latest_cob}")],
                    reason_codes=["HIGH_RISK_CONTACT_COB"], sop_clause="TCC-SOP v4.1 6.5"
                )
        except ValueError:
            pass
    if days_diff <= 10:
        return CheckResult(
            check_id="COB_COOLING", result=CheckResultValue.FAIL,
            evidence=[EvidenceItem(source="bank_mandates.csv", ref=folio_no, value=f"COB on {latest_cob}, {days_diff} days before request")],
            reason_codes=["COB_COOLING"], sop_clause="TCC-SOP v4.1 6.3"
        )
    return CheckResult(check_id="COB_COOLING", result=CheckResultValue.PASS)