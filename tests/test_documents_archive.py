from __future__ import annotations

import io
import zipfile

from suzano_aberta.archive import _looks_like_document, _year_from_timestamp
from suzano_aberta.documents import document_suffix, extract_document_text


def test_document_suffix_ignores_query_string() -> None:
    assert document_suffix("https://example.test/Edital.PDF?download=1") == ".pdf"


def test_extract_plain_text_document() -> None:
    text = extract_document_text(
        "Prefeitura de Suzano — orçamento 2026".encode(),
        "https://example.test/dados.txt",
        content_type="text/plain; charset=utf-8",
    )
    assert text is not None
    assert "orçamento 2026" in text


def test_extract_docx_xml_text() -> None:
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body><w:p><w:r><w:t>Plano Municipal de Suzano</w:t></w:r></w:p></w:body>
            </w:document>""",
        )
    text = extract_document_text(
        payload.getvalue(),
        "https://example.test/plano.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert text is not None
    assert "Plano Municipal de Suzano" in text


def test_archive_helpers_recognize_documents_and_year() -> None:
    assert _looks_like_document("https://example.test/lei.pdf")
    assert _looks_like_document("https://example.test/download", "application/pdf")
    assert not _looks_like_document("https://example.test/noticia", "text/html")
    assert _year_from_timestamp("20190405123456") == 2019
    assert _year_from_timestamp(None) is None
