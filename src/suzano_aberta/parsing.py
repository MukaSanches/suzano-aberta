from __future__ import annotations

import csv
import io
import re
import unicodedata
from datetime import datetime
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from charset_normalizer import from_bytes


SPACE_RE = re.compile(r"\s+")
DATE_RE = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](20\d{2})\b")
YEAR_RE = re.compile(r"\b(20\d{2})\b")


def decode_bytes(data: bytes, declared_encoding: str | None = None) -> str:
    """Decodifica conteúdo sem mascarar silenciosamente erros comuns de charset."""
    if declared_encoding:
        try:
            return data.decode(declared_encoding, errors="strict")
        except (LookupError, UnicodeDecodeError):
            pass
    match = from_bytes(data).best()
    if match is not None:
        return str(match)
    return data.decode("utf-8", errors="replace")


def clean_text(value: str) -> str:
    return SPACE_RE.sub(" ", value.replace("\xa0", " ")).strip()


def normalize_search(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return clean_text(re.sub(r"[^a-z0-9]+", " ", text))


def normalize_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text


def parse_br_date(value: str) -> str | None:
    match = DATE_RE.search(value)
    if not match:
        return None
    day, month, year = match.groups()
    try:
        return datetime(int(year), int(month), int(day)).date().isoformat()
    except ValueError:
        return None


def years_in_text(value: str) -> set[int]:
    return {int(year) for year in YEAR_RE.findall(value)}


def absolute_url(base: str, href: str) -> str:
    return urljoin(base, href)


def canonical_url(url: str) -> str:
    """Remove fragmento e normaliza apenas o necessário para deduplicação segura."""
    parsed = urlparse(url)
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", parsed.query, ""))


def table_rows(html: str) -> list[list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[list[str]] = []
    for tr in soup.select("table tr"):
        cells = [clean_text(cell.get_text(" ", strip=True)) for cell in tr.select("th,td")]
        if cells:
            rows.append(cells)
    return rows


def dict_rows(html: str) -> list[dict[str, str]]:
    rows = table_rows(html)
    if len(rows) < 2:
        return []
    header = [normalize_key(item) for item in rows[0]]
    if not any(header):
        return []
    result: list[dict[str, str]] = []
    for row in rows[1:]:
        if len(row) != len(header):
            continue
        result.append(dict(zip(header, row, strict=True)))
    return result


def csv_dicts(data: bytes) -> list[dict[str, str]]:
    text = decode_bytes(data)
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    result: list[dict[str, str]] = []
    for row in reader:
        normalized = {
            normalize_key(str(key)): clean_text(str(value or ""))
            for key, value in row.items()
            if key is not None
        }
        if any(normalized.values()):
            result.append(normalized)
    return result
