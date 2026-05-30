from pathlib import Path

import fitz

from app.config import get_settings


def is_pdf_path(path: Path) -> bool:
    return path.suffix.lower() == ".pdf"


def pdf_to_images(pdf_path: Path, output_dir: Path) -> list[Path]:
    """将 PDF 每页渲染为 PNG，供 OCR 使用。"""
    settings = get_settings()
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    try:
        if doc.page_count == 0:
            raise ValueError("PDF 文件无页面")
        if doc.page_count > settings.pdf_max_pages:
            raise ValueError(
                f"PDF 页数 {doc.page_count} 超过上限 {settings.pdf_max_pages}，请拆分后上传"
            )
        paths: list[Path] = []
        zoom = settings.pdf_dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        for i in range(doc.page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            out = output_dir / f"page_{i:03d}.png"
            pix.save(str(out))
            paths.append(out)
        return paths
    finally:
        doc.close()
