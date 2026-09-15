# API Contract

**HTTP API:** 1.2.0  
**Schema:** 2026-09-15  
**Python package:** 0.5.0

## Compatibility promise

Within `/v1`, additive response fields and new GET endpoints may be introduced without a major API version change. Existing fields are not intentionally removed or repurposed. Consumers should ignore unknown fields.

A breaking semantic or structural change requires a new major path such as `/v2`.

## Response identity

Consultative responses expose:

- `X-Request-ID` — correlation identifier;
- `X-API-Version` — HTTP contract version;
- `X-Schema-Version` — logical response schema version;
- `ETag` where caching is safe;
- `Server-Timing` for server-side duration.

Collection responses also include `meta.dataset_version`. A dataset version identifies the snapshot being served; it is not the same thing as the API version.

## Errors

HTTP and validation errors use `application/problem+json` with fields compatible with RFC 9457:

```json
{
  "type": "https://mukasanches.github.io/suzano-aberta/problems/validation",
  "title": "Parâmetros inválidos",
  "status": 422,
  "detail": "Um ou mais parâmetros não atendem ao contrato da API.",
  "instance": "/v1/records",
  "request_id": "..."
}
```

## Bulk access

Do not scrape every page of `/v1/records`. Consumers that need the entire corpus should discover the rolling SQLite snapshot through `/v1/snapshot` and verify its checksum.

## Provenance

`/v1/records/{id}/provenance` exposes origin and collection metadata in JSON-LD using W3C PROV concepts. `/v1/catalog` exposes a DCAT-oriented catalog for dataset discovery.

These formats are interoperability aids; the project does not claim formal certification.
