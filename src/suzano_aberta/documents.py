from __future__ import annotations

import io
import zipfile
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

from pypdf import PdfReader

from .http import PoliteHttpClient
from .parsing import decode_bytes


TEXT_SUFFIXES = {".csv", ".json", ".md", ".txt", ".xml"}
ZIP_XML_SUFFIXES = {".docx", ".odt", ".pptx", ".xlsx"}


def document_suffix(url: str) -> str:
    path = unquote(urlsplit(url).path)
    return PurePosixPath(path).suffix.casefold()


def _truncate(text: str, max_chars: int) -> str:
    cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + "\n[… conteúdo truncado pelo limite do índice …]"


def _extract_pdf(content: bytes, *, max_chars: int) -> str:
    reader = PdfReader(io.BytesIO(content))
    chunks: list[str] = []
    total = 0
    for page in reader.pages:
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        chunks.append(text)
        total += len(text)
        if total >= max_chars:
            break
    return _truncate("\n\n".join(chunks), max_chars)


def _xml_text(xml: bytes) -> str:
    root = ElementTree.fromstring(xml)
    chunks: list[str] = []
    for node in root.iter():
        if node.text and node.text.strip():
            chunks.append(node.text.strip())
    return " ".join(chunks)


def _extract_zip_xml(content: bytes, suffix: str, *, max_chars: int) -> str:
    patterns: tuple[str, ...]
    if suffix == ".docx":
        patterns = ("word/document.xml", "word/header", "word/footer", "word/footnotes.xml", "word/endnotes.xml")
    elif suffix == ".pptx":
        patterns = ("ppt/slides/slide", "ppt/notesSlides/notesSlide")
    elif suffix == ".xlsx":
        patterns = ("xl/sharedStrings.xml", "xl/worksheets/sheet")
    elif suffix == ".odt":
        patterns = ("content.xml",)
    else:
        return ""

    chunks: list[str] = []
    total = 0
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for name in archive.namelist():
            if not name.endswith(".xml"):
                continue
            if not any(name == pattern or name.startswith(pattern) for pattern in patterns):
                continue
            try:
                text = _xml_text(archive.read(name))
            except (KeyError, ElementTree.ParseError):
                continue
            if not text:
                continue
            chunks.append(text)
            total += len(text)
            if total >= max_chars:
                break
    return _truncate("\n".join(chunks), max_chars)


def extract_document_text(
    content: bytes,
    url: str,
    *,
    content_type: str = "",
    max_chars: int = 500_000,
) -> str | None:
    """Extrai texto pesquisável de formatos públicos comuns sem OCR ou serviços externos."""
    suffix = document_suffix(url)
    lowered_type = content_type.casefold()
    try:
        if suffix == ".pdf" or "application/pdf" in lowered_type:
            text = _extract_pdf(content, max_chars=max_chars)
        elif suffix in ZIP_XML_SUFFIXES:
            text = _extract_zip_xml(content, suffix, max_chars=max_chars)
        elif suffix in TEXT_SUFFIXES or lowered_type.startswith("text/"):
            text = _truncate(decode_bytes(content), max_chars)
        else:
            return None
    except (OSError, ValueError, zipfile.BadZipFile, ElementTree.ParseError):
        return None
    return text or None


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
