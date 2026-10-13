from __future__ import annotations

from datetime import date
from app.schemas import DistributorEntry, EvidenceItem, AmcCode


def validate(arn: str, euin: str | None, amc: AmcCode, on_date: str, store: dict[str, DistributorEntry]) -> tuple[bool, str, list[EvidenceItem]]:
    evidence: list[EvidenceItem] = []
    entry = store.get(arn)
    if entry is None:
        return False, "ARN_NOT_FOUND", [EvidenceItem(source="distributor_master.csv", ref=arn, value="ARN not found in distributor master")]
    evidence.append(EvidenceItem(source="distributor_master.csv", ref=arn, value=f"status={entry.arn_status}, valid_till={entry.arn_valid_till}"))
    if entry.arn_status and entry.arn_status.upper() != "ACTIVE":
        return False, "ARN_NOT_ACTIVE", evidence
    if entry.arn_valid_till and on_date > entry.arn_valid_till:
        return False, "ARN_EXPIRED", evidence
    # check empanelment
    if amc == AmcCode.NMF and entry.empanelled_nmf != "Y":
        return False, "ARN_NOT_EMPANELLED", evidence
    if amc == AmcCode.TMF and entry.empanelled_tmf != "Y":
        return False, "ARN_NOT_EMPANELLED", evidence
    return True, "VALID", evidence