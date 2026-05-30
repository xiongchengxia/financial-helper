import shutil

from app.models import DocumentRecord, MediaRecord, RecognitionTask, VoucherRecord, utc_now
from app.storage.json_store import get_store


def delete_document(document_id: str) -> None:
    store = get_store()
    doc = store.load("documents", document_id, DocumentRecord)
    if not doc:
        raise ValueError("Document not found")

    for voucher in store.list_all("vouchers", VoucherRecord):
        if document_id in voucher.documentIds:
            store.delete("vouchers", voucher.id)

    other_uses_media = any(
        d.mediaId == doc.mediaId and d.id != document_id
        for d in store.list_all("documents", DocumentRecord)
    )
    if not other_uses_media:
        media = store.load("media", doc.mediaId, MediaRecord)
        if media:
            media_path = store.root / media.storagePath
            if media_path.exists():
                media_path.unlink()
            store.delete("media", doc.mediaId)

    ocr_path = store.root / "ocr" / doc.taskId
    if ocr_path.exists():
        shutil.rmtree(ocr_path, ignore_errors=True)

    task = store.load("tasks", doc.taskId, RecognitionTask)
    if task and task.documentId == document_id:
        task.documentId = None
        task.updatedAt = utc_now()
        store.save("tasks", doc.taskId, task)

    store.delete("documents", document_id)
