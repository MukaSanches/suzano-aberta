from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .http import PoliteHttpClient
from .models import IntegrityFinding, IntegrityReport
from .parsing import clean_text

TRANSPARENCIA_URL = "https://suzano.sp.gov.br/transparencia/"

# Serviços externos que aparecem como parte conhecida da navegação oficial.
# A lista é deliberadamente curta: domínios novos ficam visíveis para revisão humana.
DEFAULT_ALLOWED_EXTERNAL_HOSTS = frozenset(
    {
        "radardatransparencia.atricon.org.br",
        "suzano.giss.com.br",
        "sv.www5.fgv.br",
    }
)


def _hostname(url: str) -> str:
    return (urlparse(url).hostname or "").casefold().rstrip(".")


def _is_municipal_host(host: str) -> bool:
    return host == "suzano.sp.gov.br" or host.endswith(".suzano.sp.gov.br")


def check_transparency_integrity(
    http: PoliteHttpClient,
    *,
    url: str = TRANSPARENCIA_URL,
    allowed_external_hosts: Iterable[str] = DEFAULT_ALLOWED_EXTERNAL_HOSTS,
) -> IntegrityReport:
    """Verifica links externos inesperados na página municipal de transparência.

    O resultado não classifica o conteúdo como malicioso. Um achado significa apenas
    que a página oficial contém um link para um domínio que não pertence ao município
    e não consta na pequena lista de serviços externos conhecidos pelo projeto.
    """
    result = http.get(url)
    soup = BeautifulSoup(result.text, "html.parser")
    allowed = {host.casefold().rstrip(".") for host in allowed_external_hosts}
    external_hosts: set[str] = set()
    findings: list[IntegrityFinding] = []
    seen_targets: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        raw_href = str(anchor.get("href", "")).strip()
        if not raw_href or raw_href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        target = urljoin(url, raw_href)
        host = _hostname(target)
        if not host or _is_municipal_host(host):
            continue

        external_hosts.add(host)
        if host in allowed or target in seen_targets:
            continue

        seen_targets.add(target)
        label = clean_text(anchor.get_text(" ", strip=True))
        findings.append(
            IntegrityFinding(
                check="dominio_externo_nao_reconhecido",
                severity="attention",
                source_url=url,
                target_url=target,
                host=host,
                evidence=label or None,
                message=(
                    "A página oficial referencia um domínio externo que não está na "
                    "lista de serviços conhecidos pelo projeto. Requer revisão humana."
                ),
            )
        )

    return IntegrityReport(
        source_url=url,
        status_code=result.status_code,
        elapsed_ms=result.elapsed_ms,
        external_hosts=sorted(external_hosts),
        findings=findings,
    )
