from __future__ import annotations

from app.schemas import CheckResultValue, CheckResult, EvidenceItem, AmcCode
from app.tools import distributor as dist_tool


def run(arn: str | None, euin: str | None, amc: AmcCode | None, on_date: str,
        plan: str | None, dist_store: dict) -> CheckResult:
    if plan and plan.upper() == "DIRECT":
        return CheckResult(check_id="DISTRIBUTOR_CODE", result=CheckResultValue.NOT_APPLICABLE)
    if not arn:
        return CheckResult(check_id="DISTRIBUTOR_CODE", result=CheckResultValue.PASS,
                           evidence=[EvidenceItem(source="distributor_master.csv", ref="n/a", value="No ARN quoted")])
    valid, status, evidence = dist_tool.validate(arn, euin, amc or AmcCode.NMF, on_date, dist_store)
    if not valid:
        return CheckResult(
            check_id="DISTRIBUTOR_CODE", result=CheckResultValue.FAIL,
            evidence=evidence, reason_codes=["ARN_INVALID_DIRECT"],
            sop_clause="TCC-SOP v4.1 7.1"
        )
    return CheckResult(
        check_id="DISTRIBUTOR_CODE", result=CheckResultValue.PASS,
        evidence=evidence
    )