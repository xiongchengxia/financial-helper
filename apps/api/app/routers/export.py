from datetime import date

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from app.models import DocumentRecord, ExportBundle, VoucherRecord, utc_now
from app.services.export_excel import build_vouchers_workbook
from app.storage.json_store import get_store

router = APIRouter(prefix="/v1/export", tags=["export"])


def _filter_vouchers(
    vouchers: list[VoucherRecord],
    from_date: str | None,
    to_date: str | None,
) -> list[VoucherRecord]:
    result = vouchers
    if from_date:
        try:
            fd = date.fromisoformat(from_date[:10])
            result = [v for v in result if date.fromisoformat(v.voucherDate[:10]) >= fd]
        except ValueError:
            pass
    if to_date:
        try:
            td = date.fromisoformat(to_date[:10])
            result = [v for v in result if date.fromisoformat(v.voucherDate[:10]) <= td]
        except ValueError:
            pass
    return result


@router.get("/vouchers")
def export_vouchers(
    format: str = Query("json", alias="format"),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
):
    store = get_store()
    vouchers = _filter_vouchers(
        store.list_all("vouchers", VoucherRecord),
        from_date,
        to_date,
    )
    documents = {d.id: d for d in store.list_all("documents", DocumentRecord)}

    if format == "json":
        bundle = ExportBundle(
            exportedAt=utc_now(),
            vouchers=vouchers,
            documents=[documents.get(v.documentIds[0]) for v in vouchers if v.documentIds and documents.get(v.documentIds[0])],
        )
        return JSONResponse(content=bundle.model_dump())

    if format == "xlsx":
        content = build_vouchers_workbook(vouchers, documents)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="vouchers_export.xlsx"'},
        )

    raise HTTPException(status_code=400, detail="format 须为 json 或 xlsx")
