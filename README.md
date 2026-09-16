<p align="center">
  <img src="brand/logo-horizontal.svg" width="520" alt="Suzano Aberta — informação pública, rastreável e aberta">
</p>

<p align="center">
  <strong>Civic Data Engine local-first para coletar, preservar, versionar, verificar, pesquisar e distribuir dados públicos relacionados a Suzano, SP.</strong>
</p>

<p align="center">
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="Licença Apache 2.0" src="https://img.shields.io/badge/licen%C3%A7a-Apache--2.0-102A43"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-0B6E4F">
  <img alt="Biblioteca 1.0.0" src="https://img.shields.io/badge/library-1.0.0-102A43">
  <img alt="API 1.2" src="https://img.shields.io/badge/API-1.2-0B6E4F">
  <img alt="SQLite local-first" src="https://img.shields.io/badge/storage-SQLite-102A43">
</p>

> **Projeto cívico independente.** O Suzano Aberta não é um portal oficial da Prefeitura Municipal de Suzano, da Câmara Municipal de Suzano, de mandato, partido ou candidatura. Em caso de divergência, a publicação da fonte responsável é a referência.

# Suzano Aberta 1.0 — Civic Data Engine

Informação pública costuma estar fragmentada entre portais, APIs, páginas, PDFs, diários, sistemas de contratação e arquivos históricos. O Suzano Aberta transforma esse material em uma infraestrutura comum sem apagar a origem de cada registro.

A versão 1.0 adiciona uma camada de confiança e memória ao sistema: **contratos de dados, histórico temporal completo, manifestos verificáveis, armazenamento endereçado por conteúdo, lineage, observabilidade e um Source SDK extensível**.

```text
FONTES PÚBLICAS
      │
      ▼
Source SDK + Registry
      │
      ▼
coleta / descoberta
      │
      ▼
PublicRecord + SourceRef
      │
      ├──────────────► histórico temporal imutável
      │
      ▼
Data Contract Engine
      │
      ├──────────────► OpenLineage journal
      ├──────────────► OpenTelemetry
      │
      ▼
SQLite + FTS5
      │
      ▼
manifesto + SHA-256 + last-known-good
      │
 ┌────┼────────┬─────────┬─────────────┐
 ▼    ▼        ▼         ▼             ▼
CLI  Python   API       Portal       Snapshot
```

## O que existe na 1.0

| Camada | Capacidade |
| --- | --- |
| Coleta | adaptadores para fontes municipais e nacionais |
| Source SDK | registry extensível e plugins via entry points Python |
| Persistência | SQLite local-first, FTS5 e fingerprints determinísticos |
| Tempo | versões completas de registros, consulta histórica e diff |
| Qualidade | Data Contracts determinísticos e score reproduzível |
| Snapshot | checksum-first, cobertura mínima, FTS, quick_check e promoção atômica |
| Manifesto | identidade do dataset, SHA-256, tamanho, contrato e metadados de geração |
| CAS | armazenamento imutável endereçado por SHA-256 |
| Lineage | journal local compatível com o modelo OpenLineage |
| Observabilidade | instrumentação OpenTelemetry opcional e vendor-neutral |
| Autopilot | frescor, locks, backoff, last-known-good e estado persistente |
| CLI | consulta, operação autônoma e central `suzano data` |
| Python | `Suzano`, `SuzanoIndex`, `SuzanoClient` e primitives 1.0 |
| HTTP | API somente leitura, OpenAPI, histórico, diff, qualidade e manifesto |
| Feed | Atom de mudanças observadas |
| Windows | instalador, launcher CMD, console interativo e autorreparo |
| Engenharia | Python 3.11–3.13, mypy strict, Hypothesis, container e CodeQL |

O caminho de confiança não depende de IA. Regras que decidem se um snapshot pode ser promovido são determinísticas e auditáveis.

# Começar no Windows

Requer Python 3.11 ou superior.

```cmd
instalar-windows.cmd
suzano.cmd
```

No console:

```text
suzano› sincronizar
suzano› diagnostico
suzano› recentes
suzano› educação
suzano› 1
suzano› fonte 1
```

Para reparar apenas o ambiente Python sem apagar o banco:

```cmd
suzano.cmd reparar
```

# Instalação Python

```bash
git clone https://github.com/MukaSanches/suzano-aberta.git
cd suzano-aberta
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e .
```

Para desenvolver:

```bash
python -m pip install -e ".[dev]"
```

Para exportadores OpenTelemetry e cliente OpenLineage opcionais:

```bash
python -m pip install -e ".[observability]"
```

# CLI

## Operação diária

```bash
suzano inicio
suzano diagnostico
suzano recentes
suzano buscar "educação"
suzano panorama
suzano sincronizar
suzano auto status
suzano auto agora
suzano auto vigiar
```

## Civic Data Engine

A versão 1.0 adiciona a central `data`:

```bash
suzano data quality
suzano data timeline <ID>
suzano data at <ID> --at 2026-09-16T10:00:00-03:00
suzano data diff --from 2026-09-15T00:00:00-03:00 --to 2026-09-16T23:59:59-03:00
suzano data manifest
suzano data verify
suzano data lineage
suzano data catalog
suzano data archive arquivo.pdf
```

`quality` executa o contrato do dataset. `timeline` mostra todas as versões preservadas. `at` reconstrói o registro no instante solicitado. `diff` resume mudanças observadas. `manifest` cria uma descrição verificável do snapshot e `verify` confere se o banco ainda corresponde ao manifesto.

# Modelo temporal

`PublicRecord` continua sendo a unidade normalizada. A partir da 1.0, mudanças substantivas também preservam uma `RecordVersion` completa.

```text
record_id
version
observed_at
content_hash
record
```

Isso permite duas operações fundamentais:

```python
from datetime import datetime
from suzano_aberta import SuzanoIndex

with SuzanoIndex("suzano-aberta.sqlite3") as index:
    versions = index.history("meu-id")
    old = index.record_at("meu-id", datetime.fromisoformat("2026-09-01T12:00:00+00:00"))
```

E um diff de intervalo:

```python
with SuzanoIndex("suzano-aberta.sqlite3") as index:
    changes = index.diff(start, end)
    print(changes.new, changes.changed, changes.absent)
```

O sistema registra observações; ele não transforma ausência temporária em conclusão automática sobre revogação, cancelamento ou exclusão jurídica.

# Data Contracts

O `DataContract` protege o caminho de promoção do snapshot. Entre as invariantes avaliadas estão:

- `PRAGMA quick_check`;
- registros ativos mínimos;
- diversidade mínima de fontes;
- IDs duplicados;
- campos obrigatórios;
- consistência entre `records` e FTS5;
- regressão anormal de cobertura;
- frescor quando aplicável.

Uso local:

```python
from suzano_aberta import validate_database_contract

report = validate_database_contract("suzano-aberta.sqlite3")
print(report.status, report.score, report.findings)
```

O contrato é uma primitive do projeto. Integrações externas de qualidade podem ser adicionadas, mas a segurança básica do snapshot não depende delas.

# Manifestos e integridade

Cada geração pode possuir um manifesto determinístico com informações como:

```text
software_version
dataset_version
database_sha256
database_bytes
records
sources
contract_sha256
lineage_run_id
generated_at
```

Gerar e verificar:

```bash
suzano data manifest
suzano data verify
```

O snapshot rolling publica:

```text
suzano-aberta.sqlite3.gz
suzano-aberta.sqlite3.gz.sha256
suzano-aberta.manifest.json
data-latest.json
```

Antes de promover uma geração, o pipeline valida SQLite, FTS, cobertura e contrato. Em falha, preserva o último estado conhecido como saudável.

# Content-Addressed Storage

Objetos podem ser arquivados por conteúdo, não por nome:

```bash
suzano data archive documento.pdf
```

ou:

```python
from suzano_aberta import ContentAddressedStore

store = ContentAddressedStore(".suzano")
obj = store.put_file("documento.pdf")
print(obj.sha256, obj.path)
```

O mesmo conteúdo produz a mesma identidade SHA-256 e não precisa ser armazenado repetidamente.

# Lineage

Cada execução importante pode registrar eventos `START`, `COMPLETE` e `FAIL` no journal local. O formato usa conceitos compatíveis com OpenLineage: run, job, inputs e outputs.

```bash
suzano data lineage
```

Quando configurado, os eventos também podem ser encaminhados a um backend OpenLineage. A indisponibilidade desse backend não interrompe coleta ou sincronização.

# OpenTelemetry

O core usa a API OpenTelemetry de forma opcional. Sem SDK/exporter configurado, a instrumentação é no-op. Isso permite adicionar traces e métricas em produção sem acoplar o projeto a um fornecedor específico de observabilidade.

O objetivo é observar operações como sincronização, validação de contrato e promoção sem transformar telemetria em dependência de disponibilidade.

# Source SDK

Fontes implementam uma definição e um coletor. O registry padrão inclui as integrações do próprio projeto e também descobre plugins instalados pelo grupo Python:

```text
suzano_aberta.sources
```

Uma integração externa pode ser distribuída como pacote separado sem editar o core.

```python
from suzano_aberta import default_source_registry

registry = default_source_registry()
for source in registry.registrations():
    print(source.definition.key, source.origin)
```

# Python

## Consulta local

```python
from suzano_aberta import SuzanoIndex

with SuzanoIndex("suzano-aberta.sqlite3") as index:
    page = index.search("transporte escolar")
    for item in page.items:
        print(item.id, item.title, item.source.url)

    print(index.quality().score)
```

## Cliente HTTP

```python
from suzano_aberta import SuzanoClient

with SuzanoClient("https://sua-api.example") as client:
    print(client.autopilot().fresh)
    print(client.quality().report.score)
    print(client.manifest().verification.ok)
```

# API HTTP

A API pública permanece **somente leitura**. A versão 1.0 da biblioteca adiciona recursos de engine sem quebrar a família `/v1` existente.

Principais rotas:

```text
GET /health/live
GET /health/ready
GET /v1/search
GET /v1/records
GET /v1/documents
GET /v1/legislation
GET /v1/procurements
GET /v1/records/{id}
GET /v1/records/{id}/provenance
GET /v1/records/{id}/history
GET /v1/records/{id}/at?at=...
GET /v1/changes
GET /v1/diff?from=...&to=...
GET /v1/quality
GET /v1/manifest
GET /v1/autopilot
GET /v1/feed/changes.atom
GET /v1/catalog
GET /v1/sources
GET /v1/stats
GET /v1/snapshot
GET /metrics
```

O serviço usa OpenAPI, Problem Details, request IDs, ETags, limites explícitos e snapshots imutáveis de leitura. Não há endpoint público para disparar coleta, editar registros ou substituir o banco.

# Autopilot

A coleta pesada é centralizada nos workflows públicos. Instalações locais fazem verificação checksum-first e só transferem o banco completo quando a geração muda.

Proteções principais:

- lock cross-process;
- backoff após falhas;
- last-known-good;
- rejeição por regressão de cobertura;
- checksum;
- SQLite `quick_check`;
- consistência FTS;
- Data Contract;
- manifesto da geração;
- promoção atômica.

Isso permite que biblioteca, CLI e API permaneçam atualizadas sem depender de intervenção manual rotineira.

# Portal

Portal público:

https://mukasanches.github.io/suzano-aberta/

A interface usa o mesmo dataset validado e mantém links para fontes oficiais. Notícias e briefing autônomo são derivados de fontes e regras verificáveis; automação não deve ser apresentada como autoria humana quando não houver autoria humana.

# Engenharia e testes

Antes de integrar mudanças na `main`, o repositório executa:

```text
Python 3.11
Python 3.12
Python 3.13
compileall
ruff
mypy --strict
pytest
Hypothesis property-based tests
wheel + sdist
instalação do wheel construído
smoke tests CLI/API/lib
container
CodeQL Python + JavaScript
validação do portal
```

Os testes de propriedades procuram automaticamente entradas que violem invariantes de normalização, IDs, CAS, manifestos e outras primitives.

# Segurança e limites

- conteúdo externo é tratado como dado, não como comando;
- a API pública é read-only;
- URLs de fontes são preservadas para auditoria;
- hashes demonstram integridade de bytes, não autenticidade jurídica;
- ausência numa coleta não prova ausência no mundo real;
- relacionamentos só devem ser publicados quando houver evidência nos registros;
- OpenTelemetry/OpenLineage são observabilidade, não componentes do caminho crítico;
- o último snapshot saudável deve sobreviver a falhas de rede, fonte, validação ou promoção.

Leia também [SECURITY.md](SECURITY.md), [GOVERNANCE.md](GOVERNANCE.md) e a documentação em [`docs/`](docs/).

# Desenvolvimento

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src/suzano_aberta
pytest
python -m build
```

Princípio de engenharia do projeto:

> Quanto mais sofisticada a infraestrutura fica por dentro, mais simples e verificável deve ficar para quem usa.

# Licença

Apache License 2.0. Veja [LICENSE](LICENSE).
