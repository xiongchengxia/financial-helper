import json
import re
from typing import Any

import httpx

from app.config import get_settings
from app.models import DocumentKind, InvoicePayload, InvoiceType


STRUCTURE_PROMPT = """你是财税票据结构化助手。根据 OCR 识别的 Markdown 文本，判断文档类型并抽取字段。

仅输出一个 JSON 对象，不要 markdown 代码块，格式如下：
{
  "documentKind": "invoice" | "bank" | "other",
  "confidence": 0.0-1.0,
  "invoice": {
    "invoice_code": "发票代码",
    "invoice_number": "发票号码",
    "issue_date": "YYYY-MM-DD",
    "buyer_name": "",
    "buyer_tax_id": "",
    "seller_name": "",
    "seller_tax_id": "",
    "amount_without_tax": 0.0,
    "tax_amount": 0.0,
    "total_with_tax": 0.0,
    "tax_rate": null,
    "invoice_type": "vat_special" | "vat_normal" | "vat_electronic",
    "check_code": null,
    "items": [{"name": "", "amount": null, "tax_rate": null}]
  }
}

规则：
- 若为增值税发票，documentKind 为 invoice，尽量填满 invoice 字段；无法识别的字符串字段用空字符串，数字用 0。
- 专票 invoice_type 为 vat_special，普票 vat_normal，电子票 vat_electronic。
- 数电票/电子发票（vat_electronic）票面常无「发票代码」，仅有 20 位「发票号码」；此时 invoice_code 可留空字符串，勿编造。
- 非发票填 documentKind 为 other，invoice 可省略或留空。
- bank 类型本期仅占位，填 other 即可。
"""


class LlmDeepseekClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url.rstrip("/")
        self.model = settings.deepseek_model

    def structure_from_markdown(self, markdown: str) -> tuple[DocumentKind, InvoicePayload | None, float]:
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": STRUCTURE_PROMPT},
                {"role": "user", "content": f"OCR 文本：\n\n{markdown[:12000]}"},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        url = f"{self.base_url}/v1/chat/completions"
        with httpx.Client(timeout=120) as client:
            response = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if response.status_code != 200:
            raise RuntimeError(f"DeepSeek API error: {response.status_code} {response.text}")

        content = response.json()["choices"][0]["message"]["content"]
        parsed = self._parse_json(content)
        kind_str = parsed.get("documentKind", "other")
        try:
            kind = DocumentKind(kind_str)
        except ValueError:
            kind = DocumentKind.other

        confidence = float(parsed.get("confidence", 0.5))
        invoice_data = parsed.get("invoice")
        invoice: InvoicePayload | None = None
        if kind == DocumentKind.invoice and invoice_data:
            invoice = self._normalize_invoice(invoice_data)
        return kind, invoice, confidence

    def _parse_json(self, text: str) -> dict[str, Any]:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                return json.loads(match.group())
            raise

    def _normalize_invoice(self, data: dict[str, Any]) -> InvoicePayload:
        inv_type = data.get("invoice_type", "vat_special")
        try:
            invoice_type = InvoiceType(inv_type)
        except ValueError:
            invoice_type = InvoiceType.vat_special
        return InvoicePayload(
            invoice_code=str(data.get("invoice_code") or ""),
            invoice_number=str(data.get("invoice_number") or ""),
            issue_date=str(data.get("issue_date") or ""),
            buyer_name=str(data.get("buyer_name") or ""),
            buyer_tax_id=str(data.get("buyer_tax_id") or ""),
            seller_name=str(data.get("seller_name") or ""),
            seller_tax_id=str(data.get("seller_tax_id") or ""),
            amount_without_tax=float(data.get("amount_without_tax") or 0),
            tax_amount=float(data.get("tax_amount") or 0),
            total_with_tax=float(data.get("total_with_tax") or 0),
            tax_rate=data.get("tax_rate"),
            invoice_type=invoice_type,
            check_code=data.get("check_code"),
            items=data.get("items") or [],
        )
