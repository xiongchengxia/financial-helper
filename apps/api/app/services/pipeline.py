import hashlib
import time
from pathlib import Path

from app.config import get_settings
from app.models import (
    DocumentKind,
    DocumentRecord,
    RecognitionTask,
    TaskStatus,
    new_id,
    utc_now,
)
from app.services.compliance import ComplianceEngine
from app.services.llm_deepseek import LlmDeepseekClient
from app.services.ocr_paddle import OcrPaddleClient
from app.services.pdf_convert import is_pdf_path, pdf_to_images
from app.services.voucher import VoucherGenerator
from app.storage.json_store import get_store


class RecognitionPipeline:
    def __init__(self) -> None:
        self.store = get_store()
        self.ocr = OcrPaddleClient()
        self.llm = LlmDeepseekClient()
        self.compliance = ComplianceEngine()
        self.voucher_gen = VoucherGenerator()

    def run(self, task_id: str, media_path: Path) -> None:
        task = self.store.load("tasks", task_id, RecognitionTask)
        if not task:
            return
        start = time.time()
        try:
            task.status = TaskStatus.processing
            task.updatedAt = utc_now()
            self.store.save("tasks", task_id, task)

            ocr_dir = self.store.ocr_dir(task_id)
            markdown, raw_path, provider_job_id = self._run_ocr(media_path, ocr_dir)

            kind, invoice, confidence = self.llm.structure_from_markdown(markdown)
            if kind == DocumentKind.bank:
                raise RuntimeError("银行流水识别尚未开放，请上传增值税发票")

            doc_id = new_id()
            payload: dict = {}
            compliance = None
            risks = []

            if kind == DocumentKind.invoice and invoice:
                payload = invoice.model_dump()
                compliance, risks = self.compliance.evaluate_invoice(
                    invoice, confidence, doc_id
                )
            else:
                payload = {"raw_text_preview": markdown[:2000]}
                kind = DocumentKind.other
                confidence = min(confidence, 0.3)

            document = DocumentRecord(
                id=doc_id,
                kind=kind,
                mediaId=task.mediaId,
                taskId=task_id,
                payload=payload,
                confidence=confidence,
                compliance=compliance,
                risks=risks,
                rawOcrPath=raw_path,
                providerJobId=provider_job_id,
                createdAt=utc_now(),
                updatedAt=utc_now(),
            )
            self.store.save("documents", doc_id, document)

            if kind == DocumentKind.invoice:
                voucher = self.voucher_gen.generate_for_document(document)
                if voucher:
                    self.store.save("vouchers", voucher.id, voucher)

            elapsed = int((time.time() - start) * 1000)
            task.status = TaskStatus.completed
            task.documentId = doc_id
            task.documentKind = kind
            task.durationMs = elapsed
            task.errorMessage = None
            task.updatedAt = utc_now()
            self.store.save("tasks", task_id, task)

        except Exception as exc:
            task = self.store.load("tasks", task_id, RecognitionTask)
            if task:
                task.status = TaskStatus.failed
                task.errorMessage = str(exc)
                task.durationMs = int((time.time() - start) * 1000)
                task.updatedAt = utc_now()
                self.store.save("tasks", task_id, task)

    def _run_ocr(self, media_path: Path, ocr_dir: Path) -> tuple[str, str, str | None]:
        if is_pdf_path(media_path):
            page_images = pdf_to_images(media_path, ocr_dir / "pages")
            if not page_images:
                raise RuntimeError("PDF 转图失败")
            parts: list[str] = []
            job_ids: list[str] = []
            for i, img_path in enumerate(page_images):
                job_id = self.ocr.submit_file(img_path)
                job_ids.append(job_id)
                job_data = self.ocr.poll_until_done(job_id)
                md, _ = self.ocr.extract_markdown(
                    job_data, ocr_dir, page_prefix=f"p{i}_"
                )
                parts.append(md)
            combined = "\n\n---\n\n".join(parts)
            combined_path = ocr_dir / "combined.md"
            combined_path.write_text(combined, encoding="utf-8")
            rel = str(combined_path.relative_to(get_settings().data_path))
            return combined, rel, ",".join(job_ids)

        job_id = self.ocr.submit_file(media_path)
        job_data = self.ocr.poll_until_done(job_id)
        return *self.ocr.extract_markdown(job_data, ocr_dir), job_id


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_media_path(storage_path: str) -> Path:
    return get_settings().data_path / storage_path
