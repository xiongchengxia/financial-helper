from datetime import date, datetime

from app.config import get_settings
from app.models import (
    ComplianceResult,
    DocumentKind,
    DocumentRecord,
    InvoicePayload,
    InvoiceType,
    RiskFlag,
    RiskLevel,
    RuleHit,
    utc_now,
)
from app.storage.json_store import get_store


class ComplianceEngine:
    def evaluate_invoice(
        self,
        invoice: InvoicePayload,
        confidence: float,
        document_id: str,
    ) -> tuple[ComplianceResult, list[RiskFlag]]:
        settings = get_settings()
        hits: list[RuleHit] = []
        risks: list[RiskFlag] = []

        required_ok, required_msg, required_keys = self._check_required_fields(invoice)
        hits.append(
            RuleHit(
                ruleId="RULE_INV_REQUIRED_FIELDS",
                passed=required_ok,
                message=required_msg,
                evidence={
                    "requiredFields": required_keys,
                    "invoiceType": invoice.invoice_type.value,
                },
            )
        )

        buyer_ok, buyer_msg = self._check_tax_id(invoice.buyer_tax_id)
        seller_ok, seller_msg = self._check_tax_id(invoice.seller_tax_id)
        tax_ok = buyer_ok and seller_ok
        hits.append(
            RuleHit(
                ruleId="RULE_INV_TAX_ID_FORMAT",
                passed=tax_ok,
                message=buyer_msg if not buyer_ok else seller_msg,
                evidence={"buyer_tax_id": invoice.buyer_tax_id, "seller_tax_id": invoice.seller_tax_id},
            )
        )

        amount_ok, amount_msg = self._check_amount_consistency(invoice)
        hits.append(
            RuleHit(
                ruleId="RULE_INV_AMOUNT_CONSISTENCY",
                passed=amount_ok,
                message=amount_msg,
                evidence={
                    "amount_without_tax": invoice.amount_without_tax,
                    "tax_amount": invoice.tax_amount,
                    "total_with_tax": invoice.total_with_tax,
                },
            )
        )
        if not amount_ok:
            risks.append(
                RiskFlag(
                    code="RISK_AMOUNT_INCONSISTENT",
                    level=RiskLevel.block,
                    message=amount_msg,
                    evidence={"rule": "RULE_INV_AMOUNT_CONSISTENCY"},
                )
            )

        date_ok, date_msg = self._check_issue_date(invoice.issue_date)
        hits.append(
            RuleHit(
                ruleId="RULE_INV_ISSUE_DATE",
                passed=date_ok,
                message=date_msg,
                evidence={"issue_date": invoice.issue_date},
            )
        )

        if settings.company_buyer_name or settings.company_buyer_tax_id:
            mismatch = False
            if settings.company_buyer_name and invoice.buyer_name:
                if settings.company_buyer_name.strip() not in invoice.buyer_name.strip():
                    mismatch = True
            if settings.company_buyer_tax_id and invoice.buyer_tax_id:
                if settings.company_buyer_tax_id.strip() != invoice.buyer_tax_id.strip():
                    mismatch = True
            if mismatch:
                risks.append(
                    RiskFlag(
                        code="RISK_BUYER_MISMATCH",
                        level=RiskLevel.warn,
                        message="购买方名称或税号与当前主体配置不一致",
                        evidence={
                            "expected_name": settings.company_buyer_name,
                            "expected_tax_id": settings.company_buyer_tax_id,
                            "actual_name": invoice.buyer_name,
                            "actual_tax_id": invoice.buyer_tax_id,
                        },
                    )
                )

        if self._is_duplicate(invoice, document_id):
            risks.append(
                RiskFlag(
                    code="RISK_DUPLICATE",
                    level=RiskLevel.block,
                    message=self._duplicate_message(invoice),
                    evidence={
                        "invoice_code": invoice.invoice_code,
                        "invoice_number": invoice.invoice_number,
                    },
                )
            )

        if settings.reimburse_deadline and invoice.issue_date:
            try:
                issue = date.fromisoformat(invoice.issue_date[:10])
                deadline = date.fromisoformat(settings.reimburse_deadline[:10])
                if issue > deadline:
                    risks.append(
                        RiskFlag(
                            code="RISK_DATE_OUT_OF_RANGE",
                            level=RiskLevel.warn,
                            message=f"开票日期晚于报销截止日 {settings.reimburse_deadline}",
                            evidence={"issue_date": invoice.issue_date},
                        )
                    )
            except ValueError:
                pass

        for kw in settings.sensitive_keywords:
            for item in invoice.items:
                if kw and kw in (item.name or ""):
                    risks.append(
                        RiskFlag(
                            code="RISK_SENSITIVE_ITEM",
                            level=RiskLevel.warn,
                            message=f"明细含敏感词：{kw}",
                            evidence={"item_name": item.name, "keyword": kw},
                        )
                    )
                    break

        if confidence < settings.low_confidence_threshold:
            risks.append(
                RiskFlag(
                    code="RISK_LOW_CONFIDENCE",
                    level=RiskLevel.warn,
                    message=f"识别置信度 {confidence:.2f} 低于阈值 {settings.low_confidence_threshold}",
                    evidence={"confidence": confidence},
                )
            )

        passed = all(h.passed for h in hits) and not any(r.level == RiskLevel.block for r in risks)
        compliance = ComplianceResult(passed=passed, hits=hits, evaluatedAt=utc_now())
        return compliance, risks

    def _is_electronic_invoice(self, inv: InvoicePayload) -> bool:
        """数电/电子发票票面通常无 12 位发票代码。"""
        return inv.invoice_type == InvoiceType.vat_electronic

    def _check_required_fields(
        self, inv: InvoicePayload
    ) -> tuple[bool, str, list[str]]:
        fields: list[tuple[str, str]] = [
            ("invoice_number", inv.invoice_number),
            ("issue_date", inv.issue_date),
            ("buyer_name", inv.buyer_name),
            ("seller_name", inv.seller_name),
        ]
        if not self._is_electronic_invoice(inv):
            fields.insert(0, ("invoice_code", inv.invoice_code))

        required_keys = [name for name, _ in fields]
        missing = [name for name, val in fields if not str(val).strip()]
        if missing:
            return False, f"缺少必填字段: {', '.join(missing)}", required_keys
        if inv.total_with_tax <= 0:
            return False, "价税合计必须大于 0", required_keys
        if self._is_electronic_invoice(inv) and not inv.invoice_code.strip():
            return True, "必填字段齐全（数电票无发票代码，已豁免）", required_keys
        return True, "必填字段齐全", required_keys

    def _duplicate_message(self, inv: InvoicePayload) -> str:
        if self._is_electronic_invoice(inv) or not inv.invoice_code.strip():
            return "发票号码与库中已有记录重复"
        return "发票代码+号码与库中已有记录重复"

    def _check_tax_id(self, tax_id: str) -> tuple[bool, str]:
        tid = (tax_id or "").strip()
        if not tid:
            return True, "税号为空（跳过）"
        if len(tid) in (15, 18, 20):
            return True, "税号格式通过"
        return False, f"税号位数异常: {len(tid)}"

    def _check_amount_consistency(self, inv: InvoicePayload) -> tuple[bool, str]:
        tol = get_settings().amount_tolerance
        expected = inv.amount_without_tax + inv.tax_amount
        diff = abs(inv.total_with_tax - expected)
        if diff <= tol:
            return True, "金额勾稽一致"
        return False, f"价税合计与不含税+税额不符，差额 {diff:.2f} 元"

    def _check_issue_date(self, issue_date: str) -> tuple[bool, str]:
        if not issue_date.strip():
            return False, "开票日期为空"
        try:
            d = date.fromisoformat(issue_date[:10])
        except ValueError:
            return False, "开票日期格式无效"
        if d < date(2000, 1, 1):
            return False, "开票日期过早"
        if d > date.today():
            return False, "开票日期不能晚于今天"
        return True, "开票日期合理"

    def _is_duplicate(self, inv: InvoicePayload, current_id: str) -> bool:
        if not inv.invoice_number.strip():
            return False
        store = get_store()
        for doc in store.list_all("documents", DocumentRecord):
            if doc.id == current_id or doc.kind != DocumentKind.invoice:
                continue
            if self._same_invoice_identity(doc.payload, inv):
                return True
        return False

    def _same_invoice_identity(self, payload: dict, inv: InvoicePayload) -> bool:
        other_number = str(payload.get("invoice_number") or "").strip()
        if other_number != inv.invoice_number.strip():
            return False
        other_code = str(payload.get("invoice_code") or "").strip()
        my_code = inv.invoice_code.strip()
        if self._is_electronic_invoice(inv) or not my_code:
            return True
        if not other_code:
            return True
        return other_code == my_code
