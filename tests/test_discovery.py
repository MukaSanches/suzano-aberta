from pathlib import Path

from suzano_aberta.discovery import WebDiscovery, normalize_url
from suzano_aberta.http import HttpResult
from suzano_aberta.store import Store


class FakeHttp:
    def __init__(self) -> None:
        self.pages = {
            "https://example.test/robots.txt": (
                "text/plain",
                b"User-agent: *\nAllow: /\nSitemap: https://example.test/sitemap.xml\n",
            ),
            "https://example.test/sitemap.xml": (
                "application/xml",
                b"<?xml version='1.0'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"
                b"<url><loc>https://example.test/saude</loc></url></urlset>",
            ),
            "https://example.test/": (
                "text/html",
                b"<html><head><title>Portal de Suzano</title></head><body>"
                b"<h1>Portal de Suzano</h1><p>Informacoes publicas municipais.</p>"
                b"<a href='/educacao?utm_source=test'>Educacao</a></body></html>",
            ),
            "https://example.test/educacao": (
                "text/html",
                "<html><body><h1>Educação municipal</h1>"
                "<p>Matrículas, escolas e programas da rede municipal de ensino.</p>"
                "</body></html>".encode(),
            ),
            "https://example.test/saude": (
                "text/html",
                b"<html><body><h1>Saude publica</h1>"
                b"<p>Unidades, atendimento e informacoes de saude da cidade.</p></body></html>",
            ),
            "https://example.test/manual.pdf": (
                "application/pdf",
                b"%PDF-1.4\n% documento de teste\n",
            ),
        }

    def get(self, url: str, *, attempts: int = 3) -> HttpResult:
        content_type, content = self.pages[url]
        return HttpResult(
            url=url,
            status_code=200,
            content=content,
            content_type=content_type,
            encoding="utf-8",
            elapsed_ms=1,
        )


def test_normalize_url_removes_tracking_and_fragment() -> None:
    assert (
        normalize_url("HTTPS://Example.Test/a//b?utm_source=x&id=1#top")
        == "https://example.test/a/b?id=1"
    )


def test_discovery_uses_sitemap_and_crawled_links(tmp_path: Path) -> None:
    discovery = WebDiscovery(FakeHttp())  # type: ignore[arg-type]
    records = discovery.discover(["https://example.test/"], max_pages=10, max_depth=2)

    titles = {record.title for record in records}
    assert "Portal de Suzano" in titles
    assert "Educação municipal" in titles
    assert "Saude publica" in titles
    assert discovery.stats.indexed == 3

    database = tmp_path / "discovery.sqlite3"
    with Store(database) as store:
        store.upsert_many(records)
        assert store.search("matriculas escola")[0].title == "Educação municipal"


def test_direct_document_seed_is_indexed_without_page_crawl() -> None:
    discovery = WebDiscovery(FakeHttp())  # type: ignore[arg-type]
    records = discovery.discover(
        ["https://example.test/manual.pdf"],
        max_pages=1,
        max_depth=0,
        max_documents=1,
        include_sitemaps=False,
    )

    assert len(records) == 1
    assert records[0].kind == "arquivo"
    assert records[0].title == "manual.pdf"
    assert records[0].source.content_sha256 is not None
    assert discovery.stats.documents_seen == 1
    assert discovery.stats.documents_fetched == 1
