from app.models import (
    BusinessEventType,
    DocumentKind,
    DocumentRecord,
    InvoicePayload,
    VoucherLine,
    VoucherRecord,
    new_id,
    utc_now,
)
from app.storage.json_store import get_store


VOUCHER_TEMPLATES: dict[BusinessEventType, list[dict]] = {
    BusinessEventType.PURCHASE_WITH_VAT: [
        {
            "accountCode": "1401",
            "accountName": "材料采购",
            "side": "debit",
            "amountRef": "amount_without_tax",
        },
        {
            "accountCode": "22210101",
            "accountName": "应交税费-应交增值税-进项税额",
            "side": "debit",
            "amountRef": "tax_amount",
        },
        {
            "accountCode": "2202",
            "accountName": "应付账款",
            "side": "credit",
            "amountRef": "total_with_tax",
        },
    ],
}


class VoucherGenerator:
    def generate_for_document(self, document: DocumentRecord) -> VoucherRecord | None:
        if document.kind != DocumentKind.invoice:
            return None
        invoice = InvoicePayload.model_validate(document.payload)
        return self._build_purchase_vat(document.id, invoice)

    def _build_purchase_vat(self, document_id: str, invoice: InvoicePayload) -> VoucherRecord:
        amounts = {
            "amount_without_tax": round(invoice.amount_without_tax, 2),
            "tax_amount": round(invoice.tax_amount, 2),
            "total_with_tax": round(invoice.total_with_tax, 2),
        }
        lines: list[VoucherLine] = []
        for i, tpl in enumerate(VOUCHER_TEMPLATES[BusinessEventType.PURCHASE_WITH_VAT], start=1):
            amount = amounts[tpl["amountRef"]]
            if tpl["side"] == "debit":
                lines.append(
                    VoucherLine(
                        lineNo=i,
                        accountCode=tpl["accountCode"],
                        accountName=tpl["accountName"],
                        side="debit",
                        debit=amount,
                        credit=0.0,
                        summary=f"发票 {invoice.invoice_number}",
                    )
                )
            else:
                lines.append(
                    VoucherLine(
                        lineNo=i,
                        accountCode=tpl["accountCode"],
                        accountName=tpl["accountName"],
                        side="credit",
                        debit=0.0,
                        credit=amount,
                        summary=f"发票 {invoice.invoice_number}",
                    )
                )

        debit_total = round(sum(l.debit for l in lines), 2)
        credit_total = round(sum(l.credit for l in lines), 2)
        if abs(debit_total - credit_total) > 0.01:
            raise ValueError(f"凭证借贷不平衡: 借 {debit_total} 贷 {credit_total}")

        voucher_date = invoice.issue_date or utc_now()[:10]
        store = get_store()
        existing = store.list_all("vouchers", VoucherRecord)
        voucher_no = str(len(existing) + 1).zfill(4)

        return VoucherRecord(
            id=new_id(),
            voucherDate=voucher_date,
            voucherNo=voucher_no,
            eventType=BusinessEventType.PURCHASE_WITH_VAT,
            documentIds=[document_id],
            lines=lines,
            debitTotal=debit_total,
            creditTotal=credit_total,
            createdAt=utc_now(),
        )
