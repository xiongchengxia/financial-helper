import json
import time
from pathlib import Path

import requests

from app.config import get_settings


class OcrPaddleClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.job_url = settings.paddleocr_job_url
        self.token = settings.paddleocr_token
        self.model = settings.paddleocr_model
        self.poll_interval = settings.paddleocr_poll_interval_sec
        self.optional_payload = {
            "useDocOrientationClassify": False,
            "useDocUnwarping": False,
            "useChartRecognition": False,
        }

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"bearer {self.token}"}

    def submit_file(self, file_path: Path) -> str:
        if not self.token:
            raise RuntimeError("PADDLEOCR_TOKEN is not configured")
        if not file_path.exists():
            raise FileNotFoundError(str(file_path))

        data = {
            "model": self.model,
            "optionalPayload": json.dumps(self.optional_payload),
        }
        with file_path.open("rb") as f:
            response = requests.post(
                self.job_url,
                headers=self.headers,
                data=data,
                files={"file": f},
                timeout=120,
            )
        if response.status_code != 200:
            raise RuntimeError(f"PaddleOCR submit failed: {response.status_code} {response.text}")
        return response.json()["data"]["jobId"]

    def poll_until_done(self, job_id: str) -> dict:
        while True:
            response = requests.get(
                f"{self.job_url}/{job_id}",
                headers=self.headers,
                timeout=60,
            )
            if response.status_code != 200:
                raise RuntimeError(f"PaddleOCR poll failed: {response.status_code}")
            data = response.json()["data"]
            state = data["state"]
            if state == "done":
                return data
            if state == "failed":
                raise RuntimeError(data.get("errorMsg", "OCR job failed"))
            time.sleep(self.poll_interval)

    def recognize_image(
        self, file_path: Path, output_dir: Path, page_prefix: str = ""
    ) -> str:
        """提交单张图片 OCR，返回该页 markdown 文本。"""
        job_id = self.submit_file(file_path)
        job_data = self.poll_until_done(job_id)
        markdown, _ = self.extract_markdown(job_data, output_dir, page_prefix=page_prefix)
        return markdown

    def extract_markdown(
        self,
        job_data: dict,
        output_dir: Path,
        page_prefix: str = "",
    ) -> tuple[str, str]:
        json_url = job_data["resultUrl"]["jsonUrl"]
        response = requests.get(json_url, timeout=120)
        response.raise_for_status()
        lines = response.text.strip().split("\n")
        parts: list[str] = []
        page_num = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            result = json.loads(line)["result"]
            for res in result.get("layoutParsingResults", []):
                md_text = res.get("markdown", {}).get("text", "")
                md_path = output_dir / f"{page_prefix}doc_{page_num}.md"
                md_path.write_text(md_text, encoding="utf-8")
                parts.append(md_text)
                page_num += 1
        combined = "\n\n---\n\n".join(parts)
        combined_path = output_dir / "combined.md"
        combined_path.write_text(combined, encoding="utf-8")
        return combined, str(combined_path.relative_to(get_settings().data_path))
