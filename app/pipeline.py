from __future__ import annotations

import time
from datetime import datetime
from app.schemas import (
    RequestIn, ResponseOut, ExtractedRequest, ResolvedInfo,
    CheckId, CheckResultValue, CheckResult, EvidenceItem,
    Outcome, TraceInfo, DraftReply, DataStore, FolioRecord,
    AmcCode, RequestType,
)
from app.trace import TraceCollector
from app import s1_intake, s2_extract, s3_resolve, s4_policy, s6_decide, s7_reply
from app.checks import identity, kyc, tpp, bank_mandate, cob, distributor as dist_check, minor, referral
from app.tools import folio as folio_tool


def run(request: RequestIn, store: DataStore) -> ResponseOut:
    trace = TraceCollector()
    start = time.perf_counter()
    request_type = RequestType.OTHER
    resolved_info = ResolvedInfo()
    folio_record = None
    all_checks = []
    outcome = Outcome.PEND
    reason_codes = []
    human_approval_required = False
    approver_role = None
    draft_reply = DraftReply()
    extracted = ExtractedRequest()
    is_invalid = False

    try:
        # S1: Intake
        attachment_texts = s1_intake.process_attachments(request.attachments, trace)
        if trace:
            trace.record_tool("s1_intake")

        # S2: Extract
        extracted = s2_extract.extract(request.subject, request.body, [a["text"] for a in attachment_texts], trace)
        if trace:
            trace.record_tool("s2_extract")

        # Determine request_type
        rt = extracted.request_type_hint or "OTHER"
        if rt in RequestType.__members__:
            request_type = RequestType(rt)
        else:
            rt_str = classify_request_type(request.subject, request.body, "\n".join(a["text"] for a in attachment_texts))
            request_type = RequestType(rt_str) if rt_str in RequestType.__members__ else RequestType.OTHER

        # S3: Resolve
        folio_record, resolved_info, error_code = s3_resolve.resolve(extracted, store.folios, store.transactions, store.bank_mandates, trace)
        if error_code == "FOLIO_PAN_MISMATCH":
            is_invalid = True
        elif error_code == "FOLIO_NOT_FOUND":
            is_invalid = True

        # S4: Policy
        amc_code = resolved_info.amc_code
        sops, addenda = s4_policy.select_policies(request.received_at, amc_code, trace)
        if trace:
            trace.record_tool("s4_policy")

        # S5: Run all 8 checks
        folio_no = resolved_info.folio_no or ""
        # 1. Folio Identity
        c1 = identity.run(extracted, store.folios)
        all_checks.append(c1)
        # 2. KYC — use PAN from resolved folio if extracted missing
        pan_for_kyc = extracted.pan or (resolved_info.first_holder_pan_masked if resolved_info.first_holder_pan_masked else None)
        c2 = kyc.run(pan_for_kyc, request_type, folio_record, amc_code, store.kra)
        all_checks.append(c2)
        # 3. TPP
        is_minor_flag = folio_record is not None and folio_tool.is_minor(folio_record)
        c3 = tpp.run(request_type, extracted.remitter_name, extracted.remitter_account_last4,
                     extracted.payer_relation_to_investor, folio_record, folio_no,
                     store.bank_mandates, is_minor_flag)
        all_checks.append(c3)
        # 4. Bank Mandate
        c4 = bank_mandate.run(request_type, folio_no, store.bank_mandates)
        all_checks.append(c4)
        # 5. COB Cooling
        contact_changed = folio_record.contact_last_changed_on if folio_record else None
        c5 = cob.run(request_type, folio_no, request.received_at, store.bank_mandates, contact_changed)
        all_checks.append(c5)
        # 6. Distributor
        c6 = dist_check.run(extracted.arn, extracted.euin, amc_code, request.received_at.date().isoformat(),
                           extracted.plan, store.distributors)
        all_checks.append(c6)
        # 7. Minor Rules
        c7 = minor.run(folio_record, request_type, request.received_at)
        all_checks.append(c7)
# 8. Referral
        pan_for_ref = extracted.pan or (resolved_info.first_holder_pan_masked if resolved_info.first_holder_pan_masked else None)
        c8 = referral.run(folio_record, amc_code, request_type, request.received_at,
                         folio_no, pan_for_ref, store.transactions, {})
        all_checks.append(c8)

        # S6: Decide
        outcome, reason_codes, human_approval_required, approver_role = s6_decide.decide(all_checks, is_invalid)
        if trace:
            trace.record_tool("s6_decide")

        # S7: Draft reply
        draft_reply = s7_reply.draft(outcome, reason_codes, all_checks, resolved_info, extracted, request, trace)
        if trace:
            trace.record_tool("s7_reply")

    except Exception as exc:
        outcome = Outcome.PEND
        human_approval_required = True
        approver_role = "CHECKER"
        for cid in CheckId:
            all_checks.append(CheckResult(check_id=cid, result=CheckResultValue.UNABLE_TO_VERIFY))
        draft_reply = DraftReply(to=request.from_, subject=f"Re: {request.subject}", body="Your request is under processing. We will update you shortly.")
        if trace:
            trace.record_doc("error", str(exc))

    elapsed = time.perf_counter() - start
    trace_info = TraceInfo(
        model_calls=[{"model": mc.model, "input_tokens": mc.input_tokens, "output_tokens": mc.output_tokens} for mc in trace.model_calls],
        tools_called=trace.tools_called,
        documents_used=[{"document": d.document, "version": d.version} for d in trace.documents_used],
        cost_usd=trace.cost_usd,
        latency_ms=round(elapsed * 1000, 1),
    )

    return ResponseOut(
        request_id=request.request_id,
        request_type=request_type,
        resolved=resolved_info,
        outcome=outcome,
        reason_codes=reason_codes,
        checks=all_checks,
        human_approval_required=human_approval_required,
        approver_role=approver_role,
        draft_reply=draft_reply,
        trace=trace_info,
    )


def classify_request_type(subject: str, body: str, att_text: str = "") -> str:
    combined = f"{subject} {body} {att_text}".lower()
    if any(w in combined for w in ["change of bank", "change bank", "new bank", "update bank"]):
        return "CHANGE_OF_BANK"
    if any(w in combined for w in ["redemption", "redeem", "withdraw"]):
        return "REDEMPTION"
    if any(w in combined for w in ["sip regist", "new sip", "start sip"]):
        return "SIP_REGISTRATION"
    if any(w in combined for w in ["sip instal", "sip installment"]):
        return "SIP_INSTALMENT"
    if any(w in combined for w in ["new folio", "new investment", "first purchase"]):
        return "NEW_FOLIO_PURCHASE"
    if any(w in combined for w in ["additional purchase", "top up", "further purchase"]):
        return "ADDITIONAL_PURCHASE"
    return "OTHER"