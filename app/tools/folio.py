from __future__ import annotations

import re
from app.schemas import EvidenceItem, FolioRecord


NON_DIGIT = re.compile(r"\D+")

def normalise(folio_raw: str) -> str | None:
    digits = NON_DIGIT.sub("", folio_raw)
    if len(digits) != 10:
        return None
    return f"{digits[:8]}/{digits[8:]}"


def get(folio_no: str, store: dict[str, FolioRecord]) -> tuple[FolioRecord | None, list[EvidenceItem]]:
    record = store.get(folio_no)
    if record is None:
        return None, [EvidenceItem(source="folio_master.csv", ref=folio_no, value="Folio not found")]
    return record, [EvidenceItem(source="folio_master.csv", ref=folio_no, value=f"holder={record.first_holder_name}, amc={record.amc_code.value}")]


def by_pan(pan: str, store: dict[str, FolioRecord]) -> list[FolioRecord]:
    return [f for f in store.values() if f.first_holder_pan_masked == pan or f.second_holder_pan_masked == pan]

def is_minor(record: FolioRecord) -> bool:
    return record.tax_status and "minor" in record.tax_status.lower()

def is_stop_lock(record: FolioRecord) -> bool:
    return record.folio_flag and record.folio_flag.strip().upper() == "STOP_LOCK"