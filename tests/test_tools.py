from __future__ import annotations

import pytest
from app.schemas import FolioRecord, AmcCode, KRAEntry, BankMandate, TxnRecord
from app.tools import folio as folio_tool, bank as bank_tool, txn as txn_tool, kra as kra_tool, distributor as dist_tool
from app.checks import kyc, tpp, bank_mandate, minor, identity


# --- Folio tool tests ---

def test_normalise_10_digits():
    assert folio_tool.normalise("4011882323") == "40118823/23"


def test_normalise_with_slash():
    assert folio_tool.normalise("40118823/23") == "40118823/23"


def test_normalise_with_spaces():
    assert folio_tool.normalise("40115267 / 30") == "40115267/30"


def test_normalise_invalid_short():
    assert folio_tool.normalise("123") is None


def test_normalise_invalid_long():
    assert folio_tool.normalise("12345678901") is None


# --- KRA tool tests ---

def test_kra_derive_validated():
    entry = KRAEntry(pan_masked="ABCDP1234X", kra_status_code="307", kra_status="KYC Validated")
    status, code, ev = kra_tool.derive_status(entry)
    assert status == "VALIDATED"


def test_kra_derive_mismatch():
    entry = KRAEntry(pan_masked="ABCDP1234X", kra_status_code="307", kra_status="Rejected")
    status, code, ev = kra_tool.derive_status(entry)
    assert status == "UNABLE_TO_VERIFY"


def test_kra_derive_code_03():
    entry = KRAEntry(pan_masked="ABCDP1234X", kra_status_code="203", kra_status="On Hold")
    status, code, ev = kra_tool.derive_status(entry)
    assert status == "ON_HOLD"


def test_kra_lookup_not_found():
    result, ev = kra_tool.lookup("NOPAN", {})
    assert result is None


# --- Bank tool tests ---

def test_bank_find_by_account():
    mandates = {"40118823/23": [BankMandate(folio_no="40118823/23", account_no_masked="XXXX1234", status="VALIDATED", is_default="Y")]}
    result = bank_tool.find_by_account("1234", "40118823/23", mandates)
    assert result is not None
    assert result.status == "VALIDATED"


def test_bank_get_validated():
    mandates = {"40118823/23": [
        BankMandate(folio_no="40118823/23", account_no_masked="XXXX1234", status="VALIDATED"),
        BankMandate(folio_no="40118823/23", account_no_masked="XXXX5678", status="PENDING_VALIDATION"),
    ]}
    result = bank_tool.get_validated("40118823/23", mandates)
    assert len(result) == 1


# --- Txn tool tests ---

def test_txn_pending():
    txns = [TxnRecord(txn_id="T1", folio_no="40118823/23", amount_inr=5000, status="PENDING_TCC", amc_code=AmcCode.NMF)]
    result = txn_tool.pending("40118823/23", amount=5000, txns=txns)
    assert len(result) == 1
    assert result[0].txn_id == "T1"


# --- Check tests ---

def test_identity_folio_not_found():
    from app.schemas import ExtractedRequest
    ext = ExtractedRequest(folio_raw="40118823/23")
    result = identity.run(ext, {})
    assert result.result.value == "FAIL"


def test_identity_pass():
    from app.schemas import ExtractedRequest
    ext = ExtractedRequest(folio_raw="40118823/23", pan="ABCDP1234X")
    folios = {"40118823/23": FolioRecord(folio_no="40118823/23", amc_code=AmcCode.NMF, first_holder_pan_masked="ABCDP1234X", holding_mode="SI", tax_status="01 Individual")}
    result = identity.run(ext, folios)
    assert result.result.value == "PASS"


def test_identity_pan_mismatch():
    from app.schemas import ExtractedRequest
    ext = ExtractedRequest(folio_raw="40118823/23", pan="ZZZZP9999Z")
    folios = {"40118823/23": FolioRecord(folio_no="40118823/23", amc_code=AmcCode.NMF, first_holder_pan_masked="ABCDP1234X", holding_mode="SI", tax_status="01 Individual")}
    result = identity.run(ext, folios)
    assert result.reason_codes[0] == "FOLIO_PAN_MISMATCH"


def test_minor_not_minor():
    from app.schemas import FolioRecord, AmcCode
    from datetime import datetime
    rec = FolioRecord(folio_no="40118823/23", amc_code=AmcCode.NMF, tax_status="01 Individual", holding_mode="SI")
    result = minor.run(rec, "ADDITIONAL_PURCHASE", datetime(2026, 10, 6))
    assert result.result.value == "NOT_APPLICABLE"


def test_tpp_not_applicable_redemption():
    from app.schemas import FolioRecord, AmcCode
    rec = FolioRecord(folio_no="40118823/23", amc_code=AmcCode.NMF, holding_mode="SI", tax_status="01 Individual")
    result = tpp.run("REDEMPTION", None, None, None, rec, "40118823/23", {}, False)
    assert result.result.value == "NOT_APPLICABLE"


def test_bank_mandate_not_applicable():
    from datetime import datetime
    result = bank_mandate.run("ADDITIONAL_PURCHASE", "40118823/23", {})
    assert result.result.value == "NOT_APPLICABLE"