from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class Outcome(str, Enum):
    PROCEED = "PROCEED"
    PROCEED_MODIFIED = "PROCEED_MODIFIED"
    PEND = "PEND"
    REJECT = "REJECT"
    HOLD_AND_REFER = "HOLD_AND_REFER"
    INVALID_REQUEST = "INVALID_REQUEST"


class CheckResultValue(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNABLE_TO_VERIFY = "UNABLE_TO_VERIFY"


class ApproverRole(str, Enum):
    CHECKER = "CHECKER"
    OPS_MANAGER = "OPS_MANAGER"


class RequestType(str, Enum):
    NEW_FOLIO_PURCHASE = "NEW_FOLIO_PURCHASE"
    ADDITIONAL_PURCHASE = "ADDITIONAL_PURCHASE"
    SIP_REGISTRATION = "SIP_REGISTRATION"
    SIP_INSTALMENT = "SIP_INSTALMENT"
    REDEMPTION = "REDEMPTION"
    CHANGE_OF_BANK = "CHANGE_OF_BANK"
    OTHER = "OTHER"


class CheckId(str, Enum):
    KYC_STATUS = "KYC_STATUS"
    THIRD_PARTY_PAYMENT = "THIRD_PARTY_PAYMENT"
    BANK_MANDATE = "BANK_MANDATE"
    COB_COOLING = "COB_COOLING"
    DISTRIBUTOR_CODE = "DISTRIBUTOR_CODE"
    MINOR_RULES = "MINOR_RULES"
    REFERRAL = "REFERRAL"
    FOLIO_IDENTITY = "FOLIO_IDENTITY"


class AmcCode(str, Enum):
    NMF = "NMF"
    TMF = "TMF"


class PlanType(str, Enum):
    REGULAR = "REGULAR"
    DIRECT = "DIRECT"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    source: str
    ref: str
    value: str


class CheckResult(BaseModel):
    check_id: CheckId
    result: CheckResultValue
    evidence: list[EvidenceItem] = Field(default_factory=list)
    sop_clause: str | None = None
    reason_codes: list[str] = Field(default_factory=list)


class Attachment(BaseModel):
    file_name: str
    content_type: str
    content_base64: str


class RequestIn(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), populate_by_name=True)
    request_id: str
    received_at: datetime
    channel: str = "email"
    from_: str = Field(alias="from")
    to: str | None = None
    cc: str | None = None
    subject: str
    body: str
    attachments: list[Attachment] = Field(default_factory=list)


class ResolvedInfo(BaseModel):
    folio_no: str | None = None
    amc_code: AmcCode | None = None
    first_holder_pan_masked: str | None = None
    txn_id: str | None = None


class ModelCall(BaseModel):
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class DocUsed(BaseModel):
    document: str
    version: str


class TraceInfo(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_calls: list[ModelCall] = Field(default_factory=list)
    tools_called: list[str] = Field(default_factory=list)
    documents_used: list[DocUsed] = Field(default_factory=list)
    cost_usd: float = 0.0
    latency_ms: float = 0.0


class DraftReply(BaseModel):
    to: str | None = None
    subject: str | None = None
    body: str | None = None


class ResponseOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    request_id: str
    request_type: RequestType
    resolved: ResolvedInfo = Field(default_factory=ResolvedInfo)
    outcome: Outcome
    reason_codes: list[str] = Field(default_factory=list)
    checks: list[CheckResult] = Field(default_factory=list)
    human_approval_required: bool = False
    approver_role: str | None = None
    draft_reply: DraftReply = Field(default_factory=DraftReply)
    trace: TraceInfo = Field(default_factory=TraceInfo)


class ExtractedRequest(BaseModel):
    request_type_hint: str | None = None
    folio_raw: str | None = None
    pan: str | None = None
    investor_name: str | None = None
    minor_name: str | None = None
    scheme_name: str | None = None
    plan: PlanType | None = None
    option: str | None = None
    amount_inr: float | None = None
    payment_mode: str | None = None
    remitter_name: str | None = None
    remitter_account_last4: str | None = None
    payer_relation_to_investor: str | None = None
    utr: str | None = None
    arn: str | None = None
    euin: str | None = None
    txn_date: str | None = None
    new_bank_account_last4: str | None = None
    new_bank_ifsc: str | None = None
    documents_enclosed: list[dict] = Field(default_factory=list)
    is_cash: bool = False
    execution_only_declaration: bool = False
    sender_role: str | None = None


class FolioRecord(BaseModel):
    folio_no: str
    amc_code: AmcCode
    holding_mode: str
    tax_status: str
    first_holder_name: str | None = None
    first_holder_pan_masked: str | None = None
    second_holder_name: str | None = None
    second_holder_pan_masked: str | None = None
    guardian_name: str | None = None
    guardian_pan_masked: str | None = None
    guardian_relation: str | None = None
    minor_dob: str | None = None
    registered_email_masked: str | None = None
    registered_mobile_masked: str | None = None
    contact_last_changed_on: str | None = None
    fatca_status: str | None = None
    nomination: str | None = None
    folio_flag: str = "NONE"
    opened_on: str | None = None


class KRAEntry(BaseModel):
    pan_masked: str
    name_as_per_kra: str | None = None
    dob: str | None = None
    kra_name: str | None = None
    kra_status_code: str | None = None
    kra_status: str | None = None
    email_validated: str | None = None
    mobile_validated: str | None = None
    pan_aadhaar_linked: str | None = None
    last_checked_at: str | None = None


class BankMandate(BaseModel):
    folio_no: str
    account_no_masked: str
    ifsc: str | None = None
    bank_name: str | None = None
    account_type: str | None = None
    account_holders: str | None = None
    is_default: str = "N"
    status: str = "PENDING_VALIDATION"
    validation_method: str | None = None
    registered_on: str | None = None
    cob_request_received_on: str | None = None


class TxnRecord(BaseModel):
    txn_id: str
    folio_no: str
    amc_code: AmcCode
    scheme_code: str | None = None
    scheme_name: str | None = None
    plan: str | None = None
    option: str | None = None
    txn_type: str | None = None
    amount_inr: float = 0.0
    units: float | None = None
    nav: float | None = None
    txn_date: str | None = None
    payment_mode: str | None = None
    remitter_account_masked: str | None = None
    remitter_name: str | None = None
    utr: str | None = None
    arn: str | None = None
    euin: str | None = None
    status: str = "PROCESSED"
    tcc_reason_code: str | None = None


class DistributorEntry(BaseModel):
    arn: str
    distributor_name: str | None = None
    arn_valid_till: str | None = None
    arn_status: str | None = None
    euin: str | None = None
    euin_holder_name: str | None = None
    euin_valid_till: str | None = None
    empanelled_nmf: str = "N"
    empanelled_tmf: str = "N"


class DataStore:
    def __init__(self):
        self.folios: dict[str, FolioRecord] = {}
        self.kra: dict[str, KRAEntry] = {}
        self.bank_mandates: dict[str, list[BankMandate]] = {}
        self.transactions: list[TxnRecord] = []
        self.distributors: dict[str, DistributorEntry] = {}