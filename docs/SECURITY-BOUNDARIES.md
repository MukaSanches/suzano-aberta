# Security boundaries

## Public API

The public API is read-only. It does not expose crawler execution, snapshot mutation, reindexing, file writes or shell execution.

## Collector boundary

Data obtained from the web is untrusted input even when the publisher is an official body. The central HTTP client therefore bounds response size and redirects, validates redirect targets, rejects literal private/local IP destinations by default and retries only transient failures.

## Data publication boundary

Collectors write into a working database. Publication workflows validate the SQLite database and derived indexes before promotion. A failed refresh must not replace the previously published snapshot.

## Browser boundary

GitHub Pages serves derived static datasets. The portal treats external links as external and does not require third-party analytics. The dynamic API, when deployed, remains a separate read-only service.

## What this does not provide

The repository does not claim formal government accreditation, classified-system controls, zero-trust certification or protection against every DNS-rebinding/network-layer attack. Production deployments still require TLS termination, edge rate limiting, network policy, dependency patching, logs, backups and operational monitoring appropriate to the hosting environment.
