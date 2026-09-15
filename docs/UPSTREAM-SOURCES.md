# Upstream source policy

Suzano Aberta combines municipal publications with public national procurement APIs. An upstream service is treated as evidence-producing infrastructure, not as an infallible dependency.

## Current structured procurement sources

- Prefeitura Municipal de Suzano — editais, licitações and detail pages;
- Câmara Municipal de Suzano — licitações, dispensas and contracts;
- Portal Nacional de Contratações Públicas (PNCP) — procurements, contracts and price-registration minutes;
- Compras.gov.br Dados Abertos — Lei 14.133 procurement records.

## Rules

1. Keep the original source URL.
2. Preserve the source name and collection time.
3. Do not turn upstream inconsistencies into accusations.
4. Prefer stable public identifiers such as PNCP control numbers, process numbers and CNPJ for deterministic joins.
5. Keep independent source confirmations instead of hiding them during deduplication.
6. Bound pagination and network response size.
7. A failure in one source must not erase successful data from other sources.
8. Authentication-gated or undocumented services are not silently scraped as if they were public APIs.

A future connector should follow these rules before it is enabled in the recurring production collection.
