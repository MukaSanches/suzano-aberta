from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, Field

from .models import PublicRecord

EntityKind = Literal["organizacao", "fornecedor", "orgao", "pessoa", "local"]

_CNPJ = re.compile(r"(?<!\d)(\d{2})\.?\s?(\d{3})\.?\s?(\d{3})[/-]?(\d{4})-?(\d{2})(?!\d)")


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def normalize_cnpj(value: str) -> str | None:
    digits = "".join(ch for ch in value if ch.isdigit())
    return digits if len(digits) == 14 else None


def canonical_entity_id(kind: EntityKind, name: str, identifier: str | None = None) -> str:
    key = identifier or normalize_name(name)
    digest = sha256(f"{kind}|{key}".encode()).hexdigest()[:20]
    return f"ent_{digest}"


class Provenance(BaseModel):
    record_id: str
    source_name: str
    source_url: str
    first_seen: str | None = None
    last_seen: str | None = None


class EntityMention(BaseModel):
    entity_id: str
    kind: EntityKind
    name: str
    identifier: str | None = None
    record_id: str
    source_name: str
    source_url: str
    confidence: float = Field(ge=0, le=1)


class Entity(BaseModel):
    id: str
    kind: EntityKind
    name: str
    identifier: str | None = None
    aliases: list[str] = Field(default_factory=list)
    records: int = Field(ge=0)
    sources: list[str] = Field(default_factory=list)


class EntityGraph(BaseModel):
    entities: list[Entity]
    mentions: list[EntityMention]


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for child in value.values():
            result.extend(_strings(child))
        return result
    if isinstance(value, list):
        result = []
        for child in value:
            result.extend(_strings(child))
        return result
    return []


def extract_mentions(record: PublicRecord) -> list[EntityMention]:
    payload = record.model_dump(mode="json")
    texts = _strings(payload)
    mentions: dict[str, EntityMention] = {}
    for text in texts:
        for match in _CNPJ.finditer(text):
            identifier = "".join(match.groups())
            entity_id = canonical_entity_id("fornecedor", identifier, identifier)
            mentions[entity_id] = EntityMention(
                entity_id=entity_id,
                kind="fornecedor",
                name=f"CNPJ {identifier}",
                identifier=identifier,
                record_id=record.id,
                source_name=record.source.name,
                source_url=record.source.url,
                confidence=1.0,
            )
    source_name = record.source.name.strip()
    if source_name:
        entity_id = canonical_entity_id("orgao", source_name)
        mentions.setdefault(entity_id, EntityMention(
            entity_id=entity_id,
            kind="orgao",
            name=source_name,
            record_id=record.id,
            source_name=record.source.name,
            source_url=record.source.url,
            confidence=1.0,
        ))
    return list(mentions.values())


def build_entity_graph(records: list[PublicRecord]) -> EntityGraph:
    mentions = [mention for record in records for mention in extract_mentions(record)]
    grouped: dict[str, list[EntityMention]] = defaultdict(list)
    for mention in mentions:
        grouped[mention.entity_id].append(mention)
    entities: list[Entity] = []
    for entity_id, group in grouped.items():
        names = Counter(item.name for item in group)
        sources = sorted({item.source_name for item in group})
        entities.append(Entity(
            id=entity_id,
            kind=group[0].kind,
            name=names.most_common(1)[0][0],
            identifier=group[0].identifier,
            aliases=sorted(names),
            records=len({item.record_id for item in group}),
            sources=sources,
        ))
    entities.sort(key=lambda item: (-item.records, item.kind, item.name))
    return EntityGraph(entities=entities, mentions=mentions)
