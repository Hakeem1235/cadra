from __future__ import annotations

from datetime import date
from app.schemas import TxnRecord, EvidenceItem, AmcCode


def pending(folio_no: str, amount: float | None = None, utr: str | None = None, txns: list[TxnRecord] | None = None) -> list[TxnRecord]:
    if txns is None:
        return []
    results = [t for t in txns if t.folio_no == folio_no and t.status == "PENDING_TCC"]
    if amount:
        results = [t for t in results if abs(t.amount_inr - amount) < 0.01]
    if utr:
        results = [t for t in results if t.utr and utr in t.utr]
    return results


def history(folio_no: str, since: str | None = None, txns: list[TxnRecord] | None = None) -> list[TxnRecord]:
    if txns is None:
        return []
    results = [t for t in txns if t.folio_no == folio_no]
    if since:
        results = [t for t in results if t.txn_date and t.txn_date >= since]
    return sorted(results, key=lambda t: t.txn_date or "")


def cash_total(pan: str, amc: AmcCode, fy: str, txns: list[TxnRecord], folio_map: dict[str, str]) -> float:
    if not pan:
        return 0.0
    total = 0.0
    for t in txns:
        if t.payment_mode != "CASH":
            continue
        if t.amc_code != amc:
            continue
        if t.status != "PROCESSED":
            continue
        if t.txn_date and _in_fy(t.txn_date, fy):
            total += t.amount_inr if t.amount_inr else 0.0
    return total


def _in_fy(txn_date_str: str, fy: str) -> bool:
    try:
        parts = txn_date_str.split("-")
        if len(parts) != 3:
            return False
        year = int(parts[0]) if len(parts[0]) == 4 else int(parts[2])
        month = int(parts[1])
        fy_start = int(fy.split("-")[0])
        if month >= 4:
            return year == fy_start
        return year == fy_start + 1
    except (ValueError, IndexError):
        return False