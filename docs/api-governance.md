# Governança da API

A API do Suzano Aberta é uma camada pública **somente leitura** sobre snapshots validados do acervo. O desenho procura manter simplicidade operacional sem abrir mão de propriedades normalmente exigidas em serviços públicos de alta confiabilidade.

## Princípios

1. **Fonte antes da conveniência** — todo registro deve apontar para a publicação de origem.
2. **Imutabilidade na consulta** — a API abre o SQLite em modo somente leitura e trata o snapshot como imutável durante cada conexão.
3. **Separação entre ingestão e serviço** — crawlers e rotinas de atualização não são expostos pela API pública.
4. **Falha segura** — snapshot inválido não substitui a última versão válida; readiness falha quando o acervo essencial não está disponível.
5. **Limites explícitos** — paginação, tamanho de resposta upstream, redirects e retries são limitados.
6. **Compatibilidade deliberada** — versão da biblioteca, versão da API, versão do esquema e versão do dataset são conceitos separados.
7. **Erros legíveis por máquina** — falhas HTTP usam Problem Details (`application/problem+json`).
8. **Proveniência interoperável** — `/v1/records/{id}/provenance` expõe uma representação JSON-LD inspirada em W3C PROV.
9. **Catálogo reutilizável** — `/v1/catalog` publica metadados JSON-LD inspirados em DCAT 3.
10. **Observabilidade sem rastreamento do cidadão** — métricas técnicas agregadas não dependem de analytics de terceiros nem de perfil de usuário.

## Superfície pública

### Consulta

- `GET /v1/search`
- `GET /v1/records`
- `GET /v1/records/{id}`
- `GET /v1/documents`
- `GET /v1/legislation`
- `GET /v1/procurements`
- `GET /v1/changes`

### Governança e interoperabilidade

- `GET /v1/capabilities`
- `GET /v1/sources`
- `GET /v1/catalog`
- `GET /v1/records/{id}/provenance`
- `GET /v1/stats`
- `GET /v1/snapshot`
- `GET /health/live`
- `GET /health/ready`
- `GET /metrics`

Não existem endpoints públicos de escrita, exclusão, coleta, reindexação ou execução de crawler.

## Versionamento

O projeto mantém quatro identificadores independentes:

- **Package version** — versão distribuída da biblioteca Python.
- **API version** — contrato funcional da API HTTP.
- **Schema version** — versão do formato lógico das respostas.
- **Dataset version** — impressão derivada do snapshot servido naquele momento.

Uma atualização do acervo não implica uma nova versão da API. Uma evolução de metadados internos não deve gerar milhares de falsas alterações no histórico.

## Consumo de recursos

A API limita `limit` a 100 e `offset` a 100.000. Consumidores que necessitam percorrer todo o acervo devem usar o snapshot publicado em `/v1/snapshot`.

O cliente HTTP da biblioteca também aplica:

- timeouts explícitos;
- limite padrão de 64 MiB por resposta;
- número máximo de redirects;
- validação de redirects antes de segui-los;
- bloqueio de localhost e IPs privados/literalmente não públicos por padrão;
- retry apenas para falhas transitórias conhecidas;
- espera limitada para `Retry-After`.

Essas proteções existem porque dados externos são insumos não confiáveis até serem validados, mesmo quando a origem é legítima.

## Cache e identidade da requisição

Respostas consultivas podem publicar `ETag` e `Cache-Control`. A API também devolve `X-Request-ID`, `X-API-Version`, `X-Schema-Version` e `Server-Timing` para diagnóstico sem exigir estado de sessão.

## Métricas

`/metrics` expõe contadores básicos em formato compatível com Prometheus quando habilitado. O endpoint pode ser desligado com `SUZANO_API_METRICS=false`.

As métricas atuais são locais à instância. Em ambiente com múltiplas réplicas, a agregação deve ser feita pelo stack de observabilidade da infraestrutura.

## Referências de arquitetura

O desenho acompanha ideias públicas e amplamente adotadas em APIs de alta confiabilidade:

- NIST — proteção de APIs durante ciclo de vida e runtime;
- OWASP API Security Top 10 — consumo seguro de APIs, limites de recursos, inventário e configuração;
- RFC 9457 — Problem Details for HTTP APIs;
- W3C PROV-O — proveniência interoperável;
- W3C DCAT 3 — catálogos e distribuição de dados;
- OpenAPI — contrato descobrível da API.

O Suzano Aberta não afirma certificação ou conformidade formal com esses padrões. Eles são usados como referências de engenharia e interoperabilidade.
