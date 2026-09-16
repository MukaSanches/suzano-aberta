<p align="center">
  <img src="brand/logo-horizontal.svg" width="520" alt="Suzano Aberta — informação pública, rastreável e aberta">
</p>

<p align="center">
  <strong>Infraestrutura cívica aberta para coletar, preservar, verificar, pesquisar e distribuir dados públicos relacionados a Suzano, SP.</strong>
</p>

<p align="center">
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/portal.yml"><img alt="Portal" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/portal.yml/badge.svg"></a>
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/android-app.yml"><img alt="Android" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/android-app.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="Licença Apache 2.0" src="https://img.shields.io/badge/licen%C3%A7a-Apache--2.0-102A43"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-0B6E4F">
  <img alt="Android API 36" src="https://img.shields.io/badge/Android-API%2036-0B6E4F">
  <img alt="SQLite local-first" src="https://img.shields.io/badge/storage-SQLite-102A43">
</p>

> **Projeto cívico independente.** O Suzano Aberta não é um portal oficial da Prefeitura Municipal de Suzano, da Câmara Municipal de Suzano, de mandato, partido ou candidatura. Em caso de divergência, a publicação da fonte responsável é a referência.

# Suzano Aberta

O Suzano Aberta transforma informação pública fragmentada em uma infraestrutura única, verificável e reutilizável.

Portais, páginas, APIs, PDFs, diários oficiais, sistemas de contratação e outras fontes continuam sendo as referências de origem. O projeto preserva essa origem, cria uma camada comum de consulta e mantém histórico suficiente para que mudanças possam ser auditadas ao longo do tempo.

O mesmo núcleo abastece biblioteca Python, CLI, API HTTP, portal público e aplicativo Android. A operação cotidiana é automatizada por código e GitHub Actions; o funcionamento normal **não depende de ChatGPT ou de qualquer IA generativa**.

## Acesse

- **Portal:** https://mukasanches.github.io/suzano-aberta/
- **Aplicativo web/mobile:** https://mukasanches.github.io/suzano-aberta/app/
- **Repositório:** https://github.com/MukaSanches/suzano-aberta
- **API:** disponibilizada a partir da mesma infraestrutura de leitura do projeto

# Arquitetura

```text
FONTES PÚBLICAS
      │
      ▼
Source SDK + Registry
      │
      ▼
coleta / descoberta / normalização
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
      ├──────────────► OpenTelemetry opcional
      │
      ▼
SQLite + FTS5
      │
      ▼
manifesto + SHA-256 + last-known-good
      │
 ┌────┼────────┬───────────┬────────────┬─────────────┐
 ▼    ▼        ▼           ▼            ▼             ▼
CLI  Python   API        Portal      Web App       Android
                                              remote-first
                                                  +
                                           fallback local
```

A regra principal é simples: **quanto mais sofisticada a infraestrutura fica por dentro, mais simples deve ser verificar o que aconteceu por fora**.

# O que o projeto entrega

| Camada | Capacidade |
| --- | --- |
| Coleta | adaptadores para fontes municipais, estaduais e nacionais relevantes |
| Source SDK | registry extensível e plugins via entry points Python |
| Persistência | SQLite local-first, FTS5 e fingerprints determinísticos |
| Histórico | versões completas de registros, consulta temporal e diff |
| Qualidade | Data Contracts determinísticos e score reproduzível |
| Snapshot | checksum-first, cobertura mínima, FTS, `quick_check` e promoção atômica |
| Manifesto | identidade do dataset, SHA-256, tamanho, contrato e metadados da geração |
| CAS | armazenamento imutável endereçado por conteúdo |
| Lineage | journal local compatível com conceitos OpenLineage |
| Observabilidade | OpenTelemetry opcional e vendor-neutral |
| Autopilot | frescor, locks, backoff, last-known-good e estado persistente |
| CLI | consulta, diagnóstico, sincronização e operação autônoma |
| Python | `Suzano`, `SuzanoIndex`, `SuzanoClient` e primitives do engine |
| API | leitura, busca, histórico, diff, qualidade, manifesto, catálogo e mobilidade |
| Portal | interface pública derivada do snapshot validado |
| App | experiência mobile com busca, briefing, favoritos, status e resiliência offline |
| Android | wrapper nativo endurecido, Android 16/API 36 e fallback empacotado |
| Engenharia | Python 3.11–3.13, mypy strict, Hypothesis, container, CodeQL e Android Lint |

# Aplicativo Suzano Aberta

O aplicativo usa a mesma base do portal; ele não cria uma segunda verdade sobre a cidade.

A navegação principal é:

```text
Início
  ├─ Suzano, agora
  ├─ pulso público
  ├─ últimas mudanças
  ├─ notícias
  └─ acessos rápidos

Explorar
  ├─ busca unificada
  ├─ legislação
  ├─ documentos
  └─ contratações

Acompanhar
  ├─ favoritos
  └─ pesquisas salvas

Status
  ├─ registros
  ├─ fontes
  ├─ cobertura
  ├─ API
  └─ geração atual

Mais
  ├─ desenvolvedores
  ├─ metodologia
  ├─ acessibilidade
  └─ sobre o projeto
```

## Atualização autônoma

O app atualiza conteúdo sem depender de intervenção manual:

- sincroniza ao abrir;
- sincroniza quando a conexão volta;
- sincroniza quando retorna ao primeiro plano;
- atualiza periodicamente enquanto está visível;
- consulta a API quando disponível;
- usa o índice estático publicado como fallback;
- usa Service Worker para resiliência no web app;
- mantém uma shell local empacotada no Android como último fallback.

Favoritos e pesquisas salvas ficam no armazenamento local do usuário. Não há conta obrigatória, publicidade ou rastreador de terceiros como requisito de funcionamento.

## Android

Código nativo em [`mobile/android/`](mobile/android/).

Parâmetros principais:

```text
package: br.com.suzanoaberta.app
compileSdk: 36
targetSdk: 36
minSdk: 26
JDK: 17
AGP: 9.4
Gradle: 9.6
```

O wrapper Android é **remote-first**: abre a versão publicada em GitHub Pages para receber evolução de interface e conteúdo sem reinstalação do APK. Se a camada remota falhar, abre a cópia local empacotada.

Proteções aplicadas:

- HTTP em claro bloqueado;
- mixed content bloqueado;
- cookies de terceiros desativados;
- debugging da WebView desativado;
- navegação externa enviada ao navegador do sistema;
- suporte ao gesto preditivo de retorno do Android moderno;
- shell local disponível para falha de rede.

O workflow [`Android App`](.github/workflows/android-app.yml) valida JavaScript, testes do app, sincroniza a shell offline, executa Android Lint e compila o APK.

# Mobilidade — Linha 11-Coral

A API possui uma camada específica para situação operacional da Linha 11-Coral com foco nas estações:

```text
Calmon Viana
Suzano
Jundiapeba
Estudantes
```

Rota:

```text
GET /v1/transit/line-11
```

A implementação consulta apenas fontes explicitamente verificadas e diferencia:

- estado disponível;
- dado antigo (`stale`);
- indisponibilidade da fonte;
- operação normal;
- alteração operacional;
- ocorrência e trecho afetado quando a fonte oferece evidência suficiente.

A ausência de um dado não é convertida em afirmação positiva. Quando as fontes não sustentam um estado operacional, a API informa indisponibilidade em vez de inventar uma conclusão.

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

Para integrações opcionais de observabilidade:

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

`quality` executa o contrato do dataset. `timeline` mostra versões preservadas. `at` reconstrói o registro no instante solicitado. `diff` resume mudanças observadas. `manifest` descreve o snapshot e `verify` confere se os bytes continuam correspondendo à geração publicada.

# Modelo temporal

`PublicRecord` é a unidade normalizada. Mudanças substantivas podem gerar `RecordVersion` completa:

```text
record_id
version
observed_at
content_hash
record
```

Exemplo:

```python
from datetime import datetime
from suzano_aberta import SuzanoIndex

with SuzanoIndex("suzano-aberta.sqlite3") as index:
    versions = index.history("meu-id")
    old = index.record_at(
        "meu-id",
        datetime.fromisoformat("2026-09-01T12:00:00+00:00"),
    )
```

O sistema registra observações. Ausência temporária não vira automaticamente conclusão sobre revogação, cancelamento, exclusão jurídica ou inexistência no mundo real.

# Data Contracts

O `DataContract` protege a promoção do snapshot.

Entre as invariantes avaliadas:

- `PRAGMA quick_check`;
- quantidade mínima de registros ativos;
- diversidade mínima de fontes;
- IDs duplicados;
- campos obrigatórios;
- consistência entre `records` e FTS5;
- regressão anormal de cobertura;
- frescor quando aplicável.

```python
from suzano_aberta import validate_database_contract

report = validate_database_contract("suzano-aberta.sqlite3")
print(report.status, report.score, report.findings)
```

A segurança básica do snapshot é determinística. Integrações externas de qualidade podem complementar o sistema, mas não substituem o contrato interno.

# Manifestos e integridade

Cada geração pode publicar metadados como:

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

Artefatos rolling:

```text
suzano-aberta.sqlite3.gz
suzano-aberta.sqlite3.gz.sha256
suzano-aberta.manifest.json
data-latest.json
```

Antes da promoção, o pipeline valida SQLite, FTS, cobertura e contrato. Se a nova geração não passar, o último estado conhecido como saudável permanece disponível.

# Content-Addressed Storage

Objetos podem ser arquivados pelo próprio conteúdo:

```bash
suzano data archive documento.pdf
```

```python
from suzano_aberta import ContentAddressedStore

store = ContentAddressedStore(".suzano")
obj = store.put_file("documento.pdf")
print(obj.sha256, obj.path)
```

O mesmo conteúdo produz a mesma identidade SHA-256 e não precisa ser armazenado repetidamente.

# Lineage e observabilidade

Execuções importantes podem registrar eventos `START`, `COMPLETE` e `FAIL` no journal local, com conceitos compatíveis com OpenLineage: run, job, inputs e outputs.

```bash
suzano data lineage
```

OpenTelemetry é opcional. Sem SDK/exporter configurado, a instrumentação é no-op. Telemetria e lineage não fazem parte do caminho crítico de disponibilidade.

# Source SDK

Fontes implementam uma definição e um coletor. O registry padrão inclui integrações do próprio projeto e descobre plugins instalados pelo grupo Python:

```text
suzano_aberta.sources
```

```python
from suzano_aberta import default_source_registry

registry = default_source_registry()
for source in registry.registrations():
    print(source.definition.key, source.origin)
```

Isso permite adicionar integração em pacote separado sem editar o core.

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

A API pública é **somente leitura**.

Rotas principais:

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
GET /v1/transit/line-11
GET /metrics
```

O serviço usa OpenAPI, Problem Details, request IDs, ETags, limites explícitos e snapshots imutáveis de leitura. Não existe endpoint público para editar registros ou substituir o banco.

# Autopilot

A coleta pesada é centralizada nos workflows públicos. Instalações locais verificam checksums e só transferem o banco completo quando a geração muda.

Proteções:

- lock cross-process;
- backoff após falhas;
- last-known-good;
- rejeição por regressão de cobertura;
- checksum;
- SQLite `quick_check`;
- consistência FTS;
- Data Contract;
- manifesto de geração;
- promoção atômica.

Biblioteca, CLI, API, portal e app podem permanecer atualizados sem operação manual rotineira.

# Portal público

O portal em GitHub Pages utiliza o mesmo dataset validado, links para fontes de origem, busca e produtos derivados da infraestrutura comum.

```text
https://mukasanches.github.io/suzano-aberta/
```

O portal é reconstruído automaticamente pelo pipeline. Briefings, notícias agregadas e indicadores devem continuar rastreáveis às fontes que sustentam cada informação.

# Estrutura do repositório

```text
.github/workflows/   CI, segurança, portal, snapshots e Android
brand/               identidade visual
config/              configuração de fontes e operação
docs/                documentação técnica e operacional
mobile/android/      aplicativo Android nativo
scripts/             automação e utilitários de build/sync
src/suzano_aberta/   biblioteca, engine, CLI e API
tests/               testes unitários, integração e contratos
web/                 portal público e web app
```

# Engenharia e testes

Antes de integrar mudanças, o repositório pode executar:

```text
Python 3.11
Python 3.12
Python 3.13
compileall
ruff
mypy strict
pytest
Hypothesis property-based tests
wheel + sdist
instalação do wheel construído
smoke tests CLI / API / biblioteca
build do container
CodeQL Python + JavaScript
validação do portal
Node tests do app
Android Lint
build do APK
```

A intenção é detectar regressões em invariantes, não apenas verificar se o programa "abre".

# Segurança e limites

- conteúdo externo é tratado como dado, não como comando;
- a API pública é read-only;
- URLs de origem são preservadas para auditoria;
- hashes demonstram integridade dos bytes, não autenticidade jurídica;
- ausência numa coleta não prova ausência no mundo real;
- relacionamentos só devem ser publicados quando houver evidência nos registros;
- OpenTelemetry/OpenLineage são observabilidade, não componentes do caminho crítico;
- o último snapshot saudável deve sobreviver a falha de rede, fonte, validação ou promoção;
- o app Android não aceita HTTP em claro nem mixed content;
- a operação normal do sistema não depende de IA generativa.

# Desenvolvimento

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src/suzano_aberta
pytest
python -m build
```

Validação da camada móvel:

```bash
node --check web/app/app.js
node --check web/app/sw.js
node --test tests/mobile-app.test.mjs
python scripts/sync_mobile_shell.py --check-after-copy
```

Build Android, dentro de `mobile/android/`:

```bash
gradle :app:lintDebug :app:assembleDebug
```

# Contribuição, governança e segurança

Leia:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [GOVERNANCE.md](GOVERNANCE.md)
- [SECURITY.md](SECURITY.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [CHANGELOG.md](CHANGELOG.md)
- [`docs/`](docs/)

# Licença

Código distribuído sob a [Apache License 2.0](LICENSE), salvo quando um arquivo ou componente indicar condição diferente.

Dados e documentos provenientes de terceiros continuam sujeitos às regras, licenças, direitos e condições das respectivas fontes.

---

**Suzano Aberta** — infraestrutura independente para tornar informação pública local mais encontrável, verificável, preservável e reutilizável.
