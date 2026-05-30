from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.config import get_settings
from app.models import MediaRecord, RecognitionTask, TaskStatus, new_id, utc_now
from app.services.pipeline import RecognitionPipeline, sha256_file
from app.storage.json_store import get_store

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])

ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_PDF_MIME = {"application/pdf"}
IMAGE_MAX_BYTES = 10 * 1024 * 1024

MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}


def _validate_upload(content_type: str | None, size: int) -> tuple[str, int]:
    settings = get_settings()
    mime = content_type or "image/jpeg"
    if mime in ALLOWED_IMAGE_MIME:
        if size > IMAGE_MAX_BYTES:
            raise HTTPException(status_code=400, detail="图片不能超过 10MB")
        return mime, IMAGE_MAX_BYTES
    if mime in ALLOWED_PDF_MIME:
        if size > settings.pdf_max_bytes:
            max_mb = settings.pdf_max_bytes // (1024 * 1024)
            raise HTTPException(status_code=400, detail=f"PDF 不能超过 {max_mb}MB")
        return mime, settings.pdf_max_bytes
    raise HTTPException(status_code=400, detail="仅支持 JPG/PNG/WebP/PDF")


@router.post("", response_model=RecognitionTask, status_code=201)
async def create_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> RecognitionTask:
    content = await file.read()
    mime, _ = _validate_upload(file.content_type, len(content))

    store = get_store()
    media_id = new_id()
    ext = MIME_TO_EXT.get(mime) or mimetypes.guess_extension(mime) or ".bin"
    rel_path = f"media/{media_id}{ext}"
    abs_path = store.root / rel_path
    abs_path.write_bytes(content)

    media = MediaRecord(
        id=media_id,
        storagePath=rel_path,
        mimeType=mime,
        byteSize=len(content),
        sha256=sha256_file(abs_path),
        createdAt=utc_now(),
    )
    store.save("media", media_id, media)

    task_id = new_id()
    task = RecognitionTask(
        id=task_id,
        status=TaskStatus.pending,
        mediaId=media_id,
        createdAt=utc_now(),
        updatedAt=utc_now(),
    )
    store.save("tasks", task_id, task)

    pipeline = RecognitionPipeline()
    background_tasks.add_task(pipeline.run, task_id, abs_path)
    return task


@router.get("/{task_id}", response_model=RecognitionTask)
def get_task(task_id: str) -> RecognitionTask:
    store = get_store()
    task = store.load("tasks", task_id, RecognitionTask)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("", response_model=list[RecognitionTask])
def list_tasks() -> list[RecognitionTask]:
    store = get_store()
    tasks = store.list_all("tasks", RecognitionTask)
    return sorted(tasks, key=lambda t: t.createdAt, reverse=True)
