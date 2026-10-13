from __future__ import annotations

from app.schemas import BankMandate, EvidenceItem


def accounts(folio_no: str, store: dict[str, list[BankMandate]]) -> list[BankMandate]:
    return store.get(folio_no, [])


def find_by_account(last4: str, folio_no: str, store: dict[str, list[BankMandate]]) -> BankMandate | None:
    for m in store.get(folio_no, []):
        if m.account_no_masked and m.account_no_masked.endswith(last4):
            return m
    return None


def get_default(folio_no: str, store: dict[str, list[BankMandate]]) -> BankMandate | None:
    for m in store.get(folio_no, []):
        if m.is_default == "Y":
            return m
    return None


def get_validated(folio_no: str, store: dict[str, list[BankMandate]]) -> list[BankMandate]:
    return [m for m in store.get(folio_no, []) if m.status == "VALIDATED"]