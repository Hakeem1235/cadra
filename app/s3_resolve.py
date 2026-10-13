from __future__ import annotations

from app.schemas import ExtractedRequest, FolioRecord, ResolvedInfo, AmcCode
from app.tools import folio as folio_tool, txn as txn_tool
from app.trace import TraceCollector


def resolve(extracted: ExtractedRequest, folios: dict, txns: list, bank_mandates: dict, trace: TraceCollector | None = None) -> tuple[FolioRecord | None, ResolvedInfo, str | None]:
    if not extracted.folio_raw:
        return None, ResolvedInfo(), "FOLIO_NOT_FOUND"
    canon = folio_tool.normalise(extracted.folio_raw)
    if not canon:
        return None, ResolvedInfo(), "FOLIO_NOT_FOUND"
    record, evidence = folio_tool.get(canon, folios)
    if trace:
        trace.record_tool("folio.get")
    if not record:
        return None, ResolvedInfo(folio_no=canon), "FOLIO_NOT_FOUND"
    amc = record.amc_code
    # PAN cross-check
    if extracted.pan and record.first_holder_pan_masked:
        if extracted.pan.replace(" ", "").upper() != record.first_holder_pan_masked.replace(" ", "").upper():
            return record, ResolvedInfo(folio_no=canon, amc_code=amc), "FOLIO_PAN_MISMATCH"
    # Find PENDING_TCC transaction
    pending_txns = txn_tool.pending(canon, extracted.amount_inr, extracted.utr, txns)
    txn_id = pending_txns[0].txn_id if pending_txns else None
    if trace and pending_txns:
        trace.record_tool("txn.pending")
    return record, ResolvedInfo(folio_no=canon, amc_code=amc, first_holder_pan_masked=record.first_holder_pan_masked, txn_id=txn_id), None