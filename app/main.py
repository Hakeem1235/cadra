from __future__ import annotations

import os
import json
from datetime import datetime
from collections import defaultdict
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.schemas import RequestIn, ResponseOut, DataStore, FolioRecord, KRAEntry, BankMandate, TxnRecord, DistributorEntry, AmcCode
from app.pipeline import run as pipeline_run

app = FastAPI(title="TCC Compliance Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_store() -> DataStore:
    store = DataStore()
    import csv
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root, "Data", "data")

    # Folio master
    with open(os.path.join(data_dir, "folio_master.csv"), newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            folio = r.get("folio_no", "").strip()
            if folio:
                store.folios[folio] = FolioRecord(
                    folio_no=folio,
                    amc_code=AmcCode(r.get("amc_code", "NMF")) if r.get("amc_code") in ("NMF", "TMF") else AmcCode.NMF,
                    holding_mode=r.get("holding_mode", ""),
                    tax_status=r.get("tax_status", ""),
                    first_holder_name=r.get("first_holder_name"),
                    first_holder_pan_masked=r.get("first_holder_pan_masked"),
                    second_holder_name=r.get("second_holder_name"),
                    second_holder_pan_masked=r.get("second_holder_pan_masked"),
                    guardian_name=r.get("guardian_name"),
                    guardian_pan_masked=r.get("guardian_pan_masked"),
                    guardian_relation=r.get("guardian_relation"),
                    minor_dob=r.get("minor_dob"),
                    registered_email_masked=r.get("registered_email_masked"),
                    registered_mobile_masked=r.get("registered_mobile_masked"),
                    contact_last_changed_on=r.get("contact_last_changed_on"),
                    fatca_status=r.get("fatca_status"),
                    nomination=r.get("nomination"),
                    folio_flag=r.get("folio_flag", "NONE"),
                    opened_on=r.get("opened_on"),
                )

    # KRA
    with open(os.path.join(data_dir, "kra_kyc_snapshot.csv"), newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            pan = r.get("pan_masked", "").strip()
            if pan:
                store.kra[pan] = KRAEntry(
                    pan_masked=pan, name_as_per_kra=r.get("name_as_per_kra"),
                    dob=r.get("dob"), kra_name=r.get("kra_name"),
                    kra_status_code=r.get("kra_status_code"), kra_status=r.get("kra_status"),
                    email_validated=r.get("email_validated"), mobile_validated=r.get("mobile_validated"),
                    pan_aadhaar_linked=r.get("pan_aadhaar_linked"), last_checked_at=r.get("last_checked_at"),
                )

    # Bank mandates
    with open(os.path.join(data_dir, "bank_mandates.csv"), newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            folio = r.get("folio_no", "").strip()
            bm = BankMandate(
                folio_no=folio, account_no_masked=r.get("account_no_masked", ""),
                ifsc=r.get("ifsc"), bank_name=r.get("bank_name"),
                account_type=r.get("account_type"), account_holders=r.get("account_holders"),
                is_default=r.get("is_default", "N"), status=r.get("status", "PENDING_VALIDATION"),
                validation_method=r.get("validation_method"), registered_on=r.get("registered_on"),
                cob_request_received_on=r.get("cob_request_received_on"),
            )
            store.bank_mandates.setdefault(folio, []).append(bm)

    # Transactions
    with open(os.path.join(data_dir, "transactions.csv"), newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                amt = float(r["amount_inr"]) if r.get("amount_inr") else 0.0
            except ValueError:
                amt = 0.0
            try:
                units = float(r["units"]) if r.get("units") else None
            except ValueError:
                units = None
            try:
                nav = float(r["nav"]) if r.get("nav") else None
            except ValueError:
                nav = None
            store.transactions.append(TxnRecord(
                txn_id=r.get("txn_id", ""), folio_no=r.get("folio_no", ""),
                amc_code=AmcCode(r.get("amc_code", "NMF")) if r.get("amc_code") in ("NMF", "TMF") else AmcCode.NMF,
                scheme_code=r.get("scheme_code"), scheme_name=r.get("scheme_name"),
                plan=r.get("plan"), option=r.get("option"), txn_type=r.get("txn_type"),
                amount_inr=amt, units=units, nav=nav, txn_date=r.get("txn_date"),
                payment_mode=r.get("payment_mode"), remitter_account_masked=r.get("remitter_account_masked"),
                remitter_name=r.get("remitter_name"), utr=r.get("utr"),
                arn=r.get("arn"), euin=r.get("euin"), status=r.get("status", "PROCESSED"),
                tcc_reason_code=r.get("tcc_reason_code"),
            ))

    # Distributor
    with open(os.path.join(data_dir, "distributor_master.csv"), newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            arn = r.get("arn", "").strip()
            if arn:
                store.distributors[arn] = DistributorEntry(
                    arn=arn, distributor_name=r.get("distributor_name"),
                    arn_valid_till=r.get("arn_valid_till"), arn_status=r.get("arn_status"),
                    euin=r.get("euin"), euin_holder_name=r.get("euin_holder_name"),
                    euin_valid_till=r.get("euin_valid_till"),
                    empanelled_nmf=r.get("empanelled_nmf", "N"),
                    empanelled_tmf=r.get("empanelled_tmf", "N"),
                )
    return store


_STORE = None


def _get_store() -> DataStore:
    global _STORE
    if _STORE is None:
        _STORE = _load_store()
    return _STORE


@app.on_event("startup")
async def startup():
    _get_store()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/requests", response_model=ResponseOut)
async def process_request(request: RequestIn):
    store = _get_store()
    try:
        result = pipeline_run(request, store)
        return result
    except Exception:
        return _safe_fallback(request)


def _safe_fallback(request: RequestIn) -> ResponseOut:
    from app.schemas import Outcome, CheckResultValue, CheckResult, CheckId, ResolvedInfo
    return ResponseOut(
        request_id=request.request_id,
        request_type="OTHER",
        outcome=Outcome.PEND,
        human_approval_required=True,
        approver_role="CHECKER",
        checks=[CheckResult(check_id=cid, result=CheckResultValue.UNABLE_TO_VERIFY) for cid in CheckId],
        trace={"model_calls": [], "tools_called": [], "documents_used": [], "cost_usd": 0.0, "latency_ms": 0.0},
        draft_reply={"to": request.from_, "subject": f"Re: {request.subject}", "body": "Your request is under processing. We will update you shortly."},
    )


def main():
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    main()