from fastapi import APIRouter, HTTPException

from app.models import DocumentKind, DocumentRecord, InvoicePayload, VoucherRecord, utc_now
from app.services.compliance import ComplianceEngine
from app.services.document_cleanup import delete_document
from app.services.voucher import VoucherGenerator
from app.storage.json_store import get_store

router = APIRouter(prefix="/v1/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRecord])
def list_documents() -> list[DocumentRecord]:
    store = get_store()
    docs = store.list_all("documents", DocumentRecord)
    return sorted(docs, key=lambda d: d.createdAt, reverse=True)


@router.get("/{document_id}", response_model=DocumentRecord)
def get_document(document_id: str) -> DocumentRecord:
    store = get_store()
    doc = store.load("documents", document_id, DocumentRecord)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=204)
def remove_document(document_id: str) -> None:
    """删除发票文档及关联凭证；若无其它文档引用则同时删除原文件。"""
    store = get_store()
    if not store.load("documents", document_id, DocumentRecord):
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        delete_document(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{document_id}/compliance/refresh", response_model=DocumentRecord)
def refresh_compliance(document_id: str) -> DocumentRecord:
    """按最新规则重新计算合规与风险（无需重新上传）。"""
    store = get_store()
    doc = store.load("documents", document_id, DocumentRecord)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.kind != DocumentKind.invoice:
        raise HTTPException(status_code=400, detail="仅发票类文档可刷新合规")
    invoice = InvoicePayload.model_validate(doc.payload)
    compliance, risks = ComplianceEngine().evaluate_invoice(
        invoice, doc.confidence, doc.id
    )
    doc.compliance = compliance
    doc.risks = risks
    doc.updatedAt = utc_now()
    store.save("documents", document_id, doc)
    return doc


@router.post("/{document_id}/vouchers", response_model=VoucherRecord, status_code=201)
def create_voucher_for_document(document_id: str) -> VoucherRecord:
    store = get_store()
    doc = store.load("documents", document_id, DocumentRecord)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.kind != DocumentKind.invoice:
        raise HTTPException(status_code=400, detail="仅发票类文档可生成凭证")
    gen = VoucherGenerator()
    voucher = gen.generate_for_document(doc)
    if not voucher:
        raise HTTPException(status_code=400, detail="无法生成凭证")
    store.save("vouchers", voucher.id, voucher)
    return voucher
