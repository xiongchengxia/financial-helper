import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from app.config import get_settings

T = TypeVar("T", bound=BaseModel)


class JsonStore:
    def __init__(self) -> None:
        self.root = get_settings().data_path
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for name in ("media", "ocr", "index/media", "index/tasks", "index/documents", "index/vouchers"):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def index_dir(self, entity: str) -> Path:
        return self.root / "index" / entity

    def media_dir(self) -> Path:
        return self.root / "media"

    def ocr_dir(self, task_id: str) -> Path:
        path = self.root / "ocr" / task_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save(self, entity: str, record_id: str, model: BaseModel) -> None:
        path = self.index_dir(entity) / f"{record_id}.json"
        path.write_text(model.model_dump_json(indent=2), encoding="utf-8")

    def load(self, entity: str, record_id: str, model_type: type[T]) -> T | None:
        path = self.index_dir(entity) / f"{record_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return model_type.model_validate(data)

    def list_all(self, entity: str, model_type: type[T]) -> list[T]:
        directory = self.index_dir(entity)
        records: list[T] = []
        for path in sorted(directory.glob("*.json"), reverse=True):
            data = json.loads(path.read_text(encoding="utf-8"))
            records.append(model_type.model_validate(data))
        return records

    def delete(self, entity: str, record_id: str) -> bool:
        path = self.index_dir(entity) / f"{record_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False


_store: JsonStore | None = None


def get_store() -> JsonStore:
    global _store
    if _store is None:
        _store = JsonStore()
    return _store
