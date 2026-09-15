from __future__ import annotations

import io

from pypdf import PdfReader

from .http import PoliteHttpClient


def extract_pdf_text(http: PoliteHttpClient, url: str, *, max_pages: int | None = None) -> str:
    result = http.get(url)
    if "pdf" not in result.content_type.lower() and not url.lower().split("?", 1)[0].endswith(".pdf"):
        raise ValueError("O recurso informado não parece ser um PDF.")
    reader = PdfReader(io.BytesIO(result.content))
    pages = reader.pages if max_pages is None else reader.pages[:max_pages]
    chunks: list[str] = []
    for page in pages:
        text = page.extract_text() or ""
        if text.strip():
            chunks.append(text.strip())
    return "\n\n".join(chunks)
