from fastapi import APIRouter, HTTPException

from app.models import VoucherRecord
from app.storage.json_store import get_store

router = APIRouter(prefix="/v1/vouchers", tags=["vouchers"])


@router.get("", response_model=list[VoucherRecord])
def list_vouchers() -> list[VoucherRecord]:
    store = get_store()
    vouchers = store.list_all("vouchers", VoucherRecord)
    return sorted(vouchers, key=lambda v: v.createdAt, reverse=True)


@router.get("/{voucher_id}", response_model=VoucherRecord)
def get_voucher(voucher_id: str) -> VoucherRecord:
    store = get_store()
    voucher = store.load("vouchers", voucher_id, VoucherRecord)
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found")
    return voucher
