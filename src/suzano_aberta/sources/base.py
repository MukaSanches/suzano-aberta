from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterator, Protocol

from bs4 import BeautifulSoup

from ..http import HttpResult, PoliteHttpClient
from ..models import PublicRecord, SourceRef
from ..parsing import absolute_url, canonical_url, clean_text


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    key: str
    name: str
    url: str
    authority: str
    category: str
    notes: str


class SourceAdapter(Protocol):
    definition: SourceDefinition

    def collect(self, *, year: int) -> list[PublicRecord]: ...


class BaseSource:
    definition: SourceDefinition

    def __init__(self, http: PoliteHttpClient) -> None:
        self.http = http

    def source_ref(
        self,
        result: HttpResult,
        *,
        name: str | None = None,
        url: str | None = None,
        hash_content: bool = True,
    ) -> SourceRef:
        return SourceRef(
            name=name or self.definition.name,
            url=url or result.url,
            observed_on=result.url if url and url != result.url else None,
            content_sha256=result.sha256 if hash_content else None,
            status_code=result.status_code,
        )

    def paged_listing(self, start_url: str, *, max_pages: int = 60) -> Iterator[HttpResult]:
        """Percorre paginação encontrada no HTML, sem fabricar URLs por tentativa."""
        current = canonical_url(start_url)
        seen: set[str] = set()
        pages = 0
        while current and current not in seen and pages < max_pages:
            seen.add(current)
            result = self.http.get(current)
            yield result
            pages += 1
            next_url = self._find_next_page(result.text, result.url)
            current = canonical_url(next_url) if next_url else ""

    @staticmethod
    def _find_next_page(html: str, base_url: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        for anchor in soup.find_all("a", href=True):
            rel = {str(item).casefold() for item in (anchor.get("rel") or [])}
            classes = {str(item).casefold() for item in (anchor.get("class") or [])}
            text = clean_text(anchor.get_text(" ", strip=True)).casefold()
            if (
                "next" in rel
                or "next" in classes
                or "nav-next" in classes
                or "next" in " ".join(classes)
                or text in {"próximo", "proximo", "seguinte", "next", "›", "»"}
                or text.startswith("próxima")
                or text.startswith("proxima")
            ):
                return absolute_url(base_url, str(anchor["href"]))
        return None

    @staticmethod
    def stable_hash(*parts: str, length: int = 16) -> str:
        payload = "|".join(parts).encode("utf-8")
        return sha256(payload).hexdigest()[:length]
