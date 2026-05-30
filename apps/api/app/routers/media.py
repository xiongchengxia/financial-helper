from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models import MediaRecord
from app.services.pipeline import resolve_media_path
from app.storage.json_store import get_store

router = APIRouter(prefix="/v1/media", tags=["media"])


@router.get("/{media_id}", response_model=MediaRecord)
def get_media(media_id: str) -> MediaRecord:
    store = get_store()
    media = store.load("media", media_id, MediaRecord)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    return media


@router.get("/{media_id}/file")
def get_media_file(media_id: str) -> FileResponse:
    store = get_store()
    media = store.load("media", media_id, MediaRecord)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    path = resolve_media_path(media.storagePath)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Media file missing")
    return FileResponse(path, media_type=media.mimeType)
