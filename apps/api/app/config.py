from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_port: int = 8001
    data_dir: str = "../../data"
    cors_origins: str = "http://localhost:3001"

    company_buyer_name: str = ""
    company_buyer_tax_id: str = ""
    reimburse_deadline: str = ""
    sensitive_item_keywords: str = ""

    paddleocr_token: str = ""
    paddleocr_model: str = "PaddleOCR-VL-1.6"
    paddleocr_poll_interval_sec: int = 5
    paddleocr_job_url: str = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    low_confidence_threshold: float = 0.6
    amount_tolerance: float = 0.06

    pdf_max_pages: int = 10
    pdf_dpi: int = 200
    pdf_max_bytes: int = 20 * 1024 * 1024

    @property
    def data_path(self) -> Path:
        base = Path(__file__).resolve().parent.parent
        path = (base / self.data_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sensitive_keywords(self) -> list[str]:
        if not self.sensitive_item_keywords.strip():
            return []
        return [k.strip() for k in self.sensitive_item_keywords.split(",") if k.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    """重新加载 .env（修改密钥后调用）。"""
    get_settings.cache_clear()
    return get_settings()
