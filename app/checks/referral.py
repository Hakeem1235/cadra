from __future__ import annotations

from datetime import datetime, timedelta
from app.schemas import CheckResultValue, CheckResult, EvidenceItem, AmcCode
from app.tools import folio as folio_tool, txn as txn_tool


def run(folio_record, amc: AmcCode | None, request_type: str, received_at: datetime,
        folio_no: str, pan: str | None, all_txns: list, folio_map: dict) -> CheckResult:
    if not folio_record or not amc:
        return CheckResult(check_id="REFERRAL", result=CheckResultValue.NOT_APPLICABLE)
    # STOP_LOCK check
    if folio_tool.is_stop_lock(folio_record):
        return CheckResult(
            check_id="REFERRAL", result=CheckResultValue.FAIL,
            evidence=[EvidenceItem("folio_master.csv", folio_no, "STOP_LOCK flag set")],
            reason_codes=["STOP_LOCK"], sop_clause="TCC-SOP v4.1 8.3"
        )
    # Cash limit check
    if pan:
        fy = "2026-2027"
        cash_tot = txn_tool.cash_total(pan, amc, fy, all_txns, folio_map)
        if cash_tot > 50000:
            return CheckResult(
                check_id="REFERRAL", result=CheckResultValue.FAIL,
                evidence=[EvidenceItem(source="transactions.csv", ref=pan, value=f"Total cash ₹{cash_tot:.2f} in FY {fy}")],
                reason_codes=["CASH_LIMIT_BREACH"], sop_clause="TCC-SOP v4.1 8.4"
            )
    # Referral trigger: purchase+redemption each >= 25L within 14 days
    folio_txns = [t for t in all_txns if t.folio_no == folio_no]
    purchases = [t for t in folio_txns if t.txn_type in ("NEW", "ADD", "SIP_REG") and t.amount_inr and t.amount_inr >= 2500000]
    redemptions = [t for t in folio_txns if t.txn_type == "RED" and t.amount_inr and t.amount_inr >= 2500000]
    for p in purchases:
        for r in redemptions:
            if p.txn_date and r.txn_date:
                try:
                    pd = datetime.strptime(p.txn_date.split(" ")[0], "%Y-%m-%d").date()
                    rd = datetime.strptime(r.txn_date.split(" ")[0], "%Y-%m-%d").date()
                except (ValueError, IndexError):
                    continue
                if abs((pd - rd).days) <= 14:
                    return CheckResult(
                        check_id="REFERRAL", result=CheckResultValue.FAIL,
                        evidence=[EvidenceItem(source="transactions.csv", ref=folio_no, value=f"Purchase {p.txn_id} ₹{p.amount_inr:.0f} on {p.txn_date} + redemption {r.txn_id} ₹{r.amount_inr:.0f} on {r.txn_date}")],
                        reason_codes=["REFERRAL_TRIGGER"], sop_clause="TCC-SOP v4.1 8.3"
                    )
    return CheckResult(check_id="REFERRAL", result=CheckResultValue.PASS)