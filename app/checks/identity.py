from __future__ import annotations

from app.schemas import CheckResultValue, CheckResult, EvidenceItem, ExtractedRequest
from app.tools import folio as folio_tool


def run(extracted: ExtractedRequest, folios: dict) -> CheckResult:
    if not extracted.folio_raw:
        return CheckResult(
            check_id="FOLIO_IDENTITY", result=CheckResultValue.FAIL,
            evidence=[EvidenceItem(source="folio_master.csv", ref="n/a", value="No folio provided")],
            reason_codes=["FOLIO_NOT_FOUND"]
        )
    canon = folio_tool.normalise(extracted.folio_raw)
    if not canon:
        return CheckResult(
            check_id="FOLIO_IDENTITY", result=CheckResultValue.FAIL,
            evidence=[EvidenceItem(source="folio_master.csv", ref=extracted.folio_raw, value="Cannot normalise to 10 digits")],
            reason_codes=["FOLIO_NOT_FOUND"]
        )
    record, ev = folio_tool.get(canon, folios)
    if not record:
        return CheckResult(
            check_id="FOLIO_IDENTITY", result=CheckResultValue.FAIL,
            evidence=[EvidenceItem(source="folio_master.csv", ref=canon, value="Folio not found")],
            reason_codes=["FOLIO_NOT_FOUND"]
        )
    # PAN cross-check
    if extracted.pan and record.first_holder_pan_masked:
        if extracted.pan.replace(" ", "").upper() != record.first_holder_pan_masked.replace(" ", "").upper():
            return CheckResult(
                check_id="FOLIO_IDENTITY", result=CheckResultValue.FAIL,
                evidence=ev + [EvidenceItem(source="extracted", ref="pan", value=f"Extracted {extracted.pan} != folio {record.first_holder_pan_masked}")],
                reason_codes=["FOLIO_PAN_MISMATCH"]
            )
    return CheckResult(
        check_id="FOLIO_IDENTITY", result=CheckResultValue.PASS,
        evidence=ev, sop_clause="TCC-SOP"
    )