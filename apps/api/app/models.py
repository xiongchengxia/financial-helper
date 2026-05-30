from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_id() -> str:
    return str(uuid4())


class TaskStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class DocumentKind(str, Enum):
    invoice = "invoice"
    bank = "bank"
    other = "other"


class RiskLevel(str, Enum):
    info = "info"
    warn = "warn"
    block = "block"


class InvoiceType(str, Enum):
    vat_special = "vat_special"
    vat_normal = "vat_normal"
    vat_electronic = "vat_electronic"


class BusinessEventType(str, Enum):
    PURCHASE_WITH_VAT = "PURCHASE_WITH_VAT"
    BANK_PAYMENT = "BANK_PAYMENT"
    BANK_RECEIPT = "BANK_RECEIPT"


class MediaRecord(BaseModel):
    id: str
    storagePath: str
    mimeType: str
    byteSize: int
    sha256: str
    createdAt: str


class RecognitionTask(BaseModel):
    id: str
    status: TaskStatus
    mediaId: str
    documentId: str | None = None
    documentKind: DocumentKind | None = None
    errorMessage: str | None = None
    durationMs: int | None = None
    createdAt: str
    updatedAt: str


class InvoiceItem(BaseModel):
    name: str
    spec: str | None = None
    unit: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None
    tax_rate: float | None = None
    tax_amount: float | None = None


class InvoicePayload(BaseModel):
    invoice_code: str = ""
    invoice_number: str = ""
    issue_date: str = ""
    buyer_name: str = ""
    buyer_tax_id: str = ""
    seller_name: str = ""
    seller_tax_id: str = ""
    amount_without_tax: float = 0.0
    tax_amount: float = 0.0
    total_with_tax: float = 0.0
    tax_rate: float | None = None
    invoice_type: InvoiceType = InvoiceType.vat_special
    check_code: str | None = None
    items: list[InvoiceItem] = Field(default_factory=list)


class RuleHit(BaseModel):
    ruleId: str
    passed: bool
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class ComplianceResult(BaseModel):
    passed: bool
    hits: list[RuleHit] = Field(default_factory=list)
    evaluatedAt: str


class RiskFlag(BaseModel):
    code: str
    level: RiskLevel
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class DocumentRecord(BaseModel):
    id: str
    kind: DocumentKind
    mediaId: str
    taskId: str
    payload: dict[str, Any]
    confidence: float
    compliance: ComplianceResult | None = None
    risks: list[RiskFlag] = Field(default_factory=list)
    rawOcrPath: str | None = None
    providerJobId: str | None = None
    createdAt: str
    updatedAt: str


class VoucherLine(BaseModel):
    lineNo: int
    accountCode: str
    accountName: str
    side: str
    debit: float = 0.0
    credit: float = 0.0
    summary: str = ""


class VoucherRecord(BaseModel):
    id: str
    voucherDate: str
    voucherWord: str = "记"
    voucherNo: str
    attachmentCount: int = 1
    eventType: BusinessEventType
    documentIds: list[str]
    lines: list[VoucherLine]
    debitTotal: float
    creditTotal: float
    createdAt: str


class ExportBundle(BaseModel):
    exportVersion: str = "1.0.0"
    exportedAt: str
    vouchers: list[VoucherRecord]
    documents: list[DocumentRecord] | None = None
