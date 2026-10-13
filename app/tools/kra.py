from __future__ import annotations

from app.schemas import KRAEntry, EvidenceItem


def lookup(pan: str, store: dict[str, KRAEntry]) -> tuple[KRAEntry | None, list[EvidenceItem]]:
    if not pan:
        return None, [EvidenceItem(source="kra_kyc_snapshot.csv", ref="no_pan", value="No PAN provided")]
    entry = store.get(pan)
    if entry is None:
        return None, [EvidenceItem(source="kra_kyc_snapshot.csv", ref=pan, value="PAN not found in KRA snapshot")]
    evidence = [
        EvidenceItem(source="kra_kyc_snapshot.csv", ref=pan, value=f"status={entry.kra_status_code} ({entry.kra_status})"),
    ]
    return entry, evidence


def derive_status(entry: KRAEntry) -> tuple[str, str, list[EvidenceItem]]:
    code = (entry.kra_status_code or "").strip()
    text = (entry.kra_status or "").strip().lower()
    evidence: list[EvidenceItem] = [
        EvidenceItem(source="kra_kyc_snapshot.csv", ref=entry.pan_masked, value=f"code={code}, text={text}")
    ]
    if not code or len(code) < 3:
        return "UNABLE_TO_VERIFY", "KYC_UNABLE_TO_VERIFY", evidence
    status_map = {
        "07": ("VALIDATED", "KYC_VALIDATED"),
        "02": ("REGISTERED", "KYC_REGISTERED"),
        "03": ("ON_HOLD", "KYC_ON_HOLD"),
        "04": ("REJECTED", "KYC_REJECTED"),
        "01": ("UNDER_PROCESS", "KYC_UNDER_PROCESS"),
        "05": ("NOT_AVAILABLE", "KYC_NOT_AVAILABLE"),
        "99": ("SERVICE_NOT_REACHABLE", "KYC_SERVICE_NOT_REACHABLE"),
    }
    last_two = code[-2:]
    expected_status = status_map.get(last_two)
    if expected_status is None:
        return "UNABLE_TO_VERIFY", "KYC_UNABLE_TO_VERIFY", evidence
    # check code/text consistency if text is present
    text_map = {
        "validated": "07", "registered": "02", "on hold": "03",
        "rejected": "04", "under process": "01", "not available": "05",
    }
    if text and text in text_map and text_map[text] != last_two:
        evidence.append(EvidenceItem(
            source="kra_kyc_snapshot.csv", ref=entry.pan_masked,
            value=f"Code/text mismatch: code={code} suggests {expected_status[0]}, text says {text}"
        ))
        return "UNABLE_TO_VERIFY", "KYC_DATA_ISSUE", evidence
    status_name, reason_code = expected_status
    return status_name, reason_code, evidence