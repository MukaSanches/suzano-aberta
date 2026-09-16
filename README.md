<p align="center">
  <img src="brand/logo-horizontal.svg" width="520" alt="Suzano Aberta — informação pública, rastreável e aberta">
</p>

<p align="center">
  <strong>Infraestrutura cívica aberta para coletar, preservar, verificar, pesquisar e distribuir informação pública relacionada a Suzano, SP.</strong>
</p>

<p align="center">
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/pages.yml"><img alt="Portal" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/pages.yml/badge.svg"></a>
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/android-app.yml"><img alt="Android" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/android-app.yml/badge.svg"></a>
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ios-app.yml"><img alt="iOS" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ios-app.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="Apache License 2.0" src="https://img.shields.io/badge/licen%C3%A7a-Apache--2.0-102A43"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-0B6E4F">
  <img alt="Android API 36" src="https://img.shields.io/badge/Android-API%2036-0B6E4F">
  <img alt="iOS 16+" src="https://img.shields.io/badge/iOS-16%2B-102A43">
  <img alt="SQLite local-first" src="https://img.shields.io/badge/storage-SQLite-102A43">
</p>

> **Projeto cívico independente.** O Suzano Aberta não é um portal oficial da Prefeitura Municipal de Suzano, da Câmara Municipal de Suzano, da CPTM, de mandato, partido ou candidatura. Quando houver divergência, a publicação da fonte responsável deve ser tratada como referência.

# Suzano Aberta

O **Suzano Aberta** transforma informação pública fragmentada em uma infraestrutura pesquisável, rastreável e reutilizável.

Portais, páginas, APIs, PDFs, diários oficiais, sistemas de contratação, notícias e outras fontes continuam sendo as referências de origem. O projeto preserva essa origem, normaliza o que pode ser normalizado, registra mudanças e oferece interfaces mais simples para consulta pública.

O mesmo núcleo abastece biblioteca Python, CLI, API HTTP, portal, Web App, Android e iOS. A operação rotineira é automatizada por código e GitHub Actions: **o funcionamento normal não depende do ChatGPT nem de qualquer IA generativa**.

## Acesso rápido

| Produto | Endereço / instalação |
| --- | --- |
| Portal público | https://mukasanches.github.io/suzano-aberta/ |
| Web App | https://mukasanches.github.io/suzano-aberta/app/ |
| Android | https://github.com/MukaSanches/suzano-aberta/releases/latest/download/suzano-aberta-android.apk |
| iPhone / iPad | abra o Web App no Safari e use **Compartilhar → Adicionar à Tela de Início** |
| Linha 11–Coral | https://mukasanches.github.io/suzano-aberta/linha-11.html |
| Código-fonte | https://github.com/MukaSanches/suzano-aberta |

Guias detalhados: [Android](ANDROID.md) · [iOS](IOS.md) · [App móvel](docs/mobile-app.md)

# Princípios

1. **Fonte antes da interface.** A informação deve apontar para a origem sempre que possível.
2. **Ausência não vira certeza.** Falha de coleta ou falta de evidência não deve ser apresentada como fato positivo.
3. **Histórico importa.** Mudanças relevantes devem poder ser comparadas ao longo do tempo.
4. **Automação não elimina transparência.** Toda classificação automatizada precisa ser explicável e auditável.
5. **Falha segura.** Quando uma fonte quebra, o último estado saudável deve sobreviver sem inventar dados.
6. **Uma infraestrutura, várias interfaces.** Portal, API, CLI, biblioteca, Web App, Android e iOS não devem criar verdades paralelas.
7. **Distribuição reproduzível.** Builds, validações e artefatos devem ser gerados por processos verificáveis no repositório.

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
      ├──────────────► histórico temporal
      │
      ▼
Data Contract Engine
      │
      ├──────────────► lineage local
      ├──────────────► OpenTelemetry opcional
      │
      ▼
SQLite + FTS5
      │
      ▼
manifesto + SHA-256 + last-known-good
      │
 ┌────┼────────┬──────────┬──────────┬─────────┬─────────┐
 ▼    ▼        ▼          ▼          ▼         ▼         ▼
CLI  Python   API       Portal     Web App   Android    iOS
                                           remote-    remote-
                                            first      first
                                              +          +
                                           fallback   fallback
                                            local      local
```

A interface móvel canônica vive em `web/app/`. Android e iOS usam essa mesma camada visual e de dados, mas acrescentam um wrapper nativo e um fallback empacotado. Isso reduz divergência funcional e mantém uma única origem de verdade para a experiência móvel.

Em paralelo, módulos especializados podem gerar artefatos públicos derivados. O acompanhamento da Linha 11–Coral, por exemplo, produz um JSON estático a partir de notícias recentes e o publica junto com o portal.

# O que o projeto entrega

| Camada | Capacidade |
| --- | --- |
| Coleta | adaptadores para fontes públicas municipais, estaduais e nacionais relevantes |
| Source SDK | registry extensível e plugins por entry points Python |
| Persistência | SQLite local-first, FTS5 e fingerprints determinísticos |
| Histórico | versões de registros, consulta temporal e diff |
| Qualidade | Data Contracts determinísticos e score reproduzível |
| Snapshot | `quick_check`, cobertura mínima, FTS, checksum e promoção atômica |
| Manifesto | identidade do dataset, SHA-256, tamanho e metadados da geração |
| CAS | armazenamento imutável endereçado por conteúdo |
| Lineage | journal local compatível com conceitos OpenLineage |
| Observabilidade | OpenTelemetry opcional e vendor-neutral |
| Autopilot | frescor, locks, backoff e last-known-good |
| CLI | consulta, diagnóstico, sincronização e operação autônoma |
| Python | `Suzano`, `SuzanoIndex`, `SuzanoClient` e primitives do engine |
| API | leitura, busca, histórico, diff, qualidade, manifesto, catálogo e status |
| Portal | interface pública construída a partir dos artefatos validados |
| Mobilidade | estimativa transparente da Linha 11–Coral baseada em notícias recentes |
| Web App | experiência móvel instalável, busca, briefing, favoritos, status e resiliência |
| Android | wrapper nativo, Android 16/API 36, release em GitHub e fallback local |
| iOS | wrapper SwiftUI + WKWebView, iOS/iPadOS 16+, XcodeGen e fallback local |
| Engenharia | Python 3.11–3.13, mypy strict, Hypothesis, container, CodeQL, Android Lint e Xcode build |

# Aplicativo Suzano Aberta

O aplicativo usa a mesma infraestrutura do portal; ele não mantém uma segunda base de fatos sobre a cidade.

## Navegação

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

O app foi desenhado para continuar útil sem operação manual rotineira:

- sincroniza ao abrir;
- sincroniza quando a conexão volta;
- sincroniza quando retorna ao primeiro plano;
- atualiza periodicamente enquanto está visível;
- usa a API quando a capacidade consultada estiver disponível;
- recorre ao índice estático publicado quando necessário;
- usa Service Worker na experiência web;
- mantém shell local empacotada nos wrappers Android e iOS como último fallback;
- preserva favoritos e pesquisas salvas no armazenamento local.

Não há conta obrigatória, publicidade ou rastreador de terceiros como requisito de funcionamento.

# Android

O wrapper Android está em [`mobile/android/`](mobile/android/).

```text
package: br.com.suzanoaberta.app
compileSdk: 36
targetSdk: 36
minSdk: 26
JDK: 17
AGP: 9.4
Gradle: 9.6
```

A aplicação é **remote-first**: abre a versão publicada no GitHub Pages para receber melhorias compatíveis e conteúdo novo sem exigir reinstalação do APK. Se a camada remota falhar, a shell empacotada em `android_asset` funciona como fallback local.

Proteções principais:

- HTTP em claro bloqueado;
- mixed content bloqueado;
- cookies de terceiros desativados;
- debugging da WebView desativado;
- links externos enviados ao navegador do sistema;
- suporte ao retorno preditivo nas versões modernas do Android;
- compatibilidade mantida a partir da API 26;
- fallback local para falha de rede.

## Instalar no Android

Download público:

```text
https://github.com/MukaSanches/suzano-aberta/releases/latest/download/suzano-aberta-android.apk
```

O workflow [`Android App`](.github/workflows/android-app.yml) valida a shell, executa os testes móveis, sincroniza o fallback, executa Android Lint, compila o APK Release, verifica assinatura, gera SHA-256 e publica a versão quando aplicável.

Mais detalhes: [ANDROID.md](ANDROID.md).

# iOS / iPadOS

O wrapper nativo está em [`mobile/ios/`](mobile/ios/) e usa **SwiftUI + WKWebView**.

```text
bundle id: br.com.suzanoaberta.app
deployment target: iOS 16.0
dispositivos: iPhone + iPad
projeto: XcodeGen
interface: web/app compartilhada
fallback: shell local empacotada
```

A aplicação também é **remote-first**. O host principal do Suzano Aberta permanece dentro do app; links externos são entregues ao sistema. O wrapper oferece gesto de voltar, pull-to-refresh, carregamento remoto e fallback local.

## Instalar no iPhone ou iPad sem custo

A forma pública e sem taxa de instalação é o Web App:

1. abra `https://mukasanches.github.io/suzano-aberta/app/` no Safari;
2. toque em **Compartilhar**;
3. escolha **Adicionar à Tela de Início**;
4. confirme a adição.

O ícone passa a ficar disponível na Tela de Início e a experiência abre em modo de aplicativo.

## Build nativo

O workflow [`iOS App`](.github/workflows/ios-app.yml) usa um runner macOS para:

1. validar JavaScript e os testes móveis compartilhados;
2. instalar XcodeGen;
3. gerar o projeto Xcode a partir de `mobile/ios/project.yml`;
4. compilar com `xcodebuild` para iOS Simulator;
5. empacotar e publicar um artifact de simulador em builds da `main`.

Um `.app` de simulador **não é instalável em iPhones físicos**. Distribuição nativa em aparelho real exige assinatura/provisionamento Apple; publicação ampla pode ser feita futuramente via TestFlight/App Store quando houver a conta e os certificados apropriados.

Mais detalhes: [IOS.md](IOS.md).

# Linha 11–Coral

O módulo de mobilidade acompanha **Calmon Viana, Suzano, Jundiapeba e Estudantes** por meio de notícias recentes.

Ele **não se apresenta como telemetria em tempo real** e não consulta uma API operacional da CPTM ou da ARTESP. O objetivo é transformar manchetes recentes em um indicador simples, preservando as evidências e mostrando a incerteza.

Estados possíveis:

- **verde** — não foi encontrado alerta operacional recente mais novo do que eventual notícia de normalização;
- **amarelo** — há alteração, manutenção, ocorrência antiga sem confirmação posterior ou incerteza temporal;
- **vermelho** — há notícia recente indicando interrupção, falha, pane, suspensão ou problema operacional;
- **cinza** — a descoberta falhou ou a estimativa publicada ficou desatualizada.

O gerador [`scripts/build_line11_news_status.py`](scripts/build_line11_news_status.py) usa descoberta de notícias via Google News RSS e produz:

```text
web/data/line11-news-status.json
```

O workflow do portal atualiza esse artefato a cada **30 minutos**. O cliente considera a estimativa velha após a janela definida no próprio JSON e passa a exibir estado de cautela.

Cada evidência preserva, quando disponível:

- título;
- veículo;
- data;
- link encontrado;
- resumo da evidência;
- motivo provável;
- confiança;
- horário de geração.

**Importante:** verde não significa “a CPTM confirmou operação normal neste minuto”. Significa somente que, na janela monitorada, não apareceu evidência jornalística negativa mais recente do que uma normalização, ou não surgiu alerta operacional recente. Para decisões de viagem, confira também os canais oficiais da operadora responsável.

Documentação detalhada: [`docs/linha-11-tempo-real.md`](docs/linha-11-tempo-real.md).

# Começar no Windows

Requer Python 3.11 ou superior.

```cmd
instalar-windows.cmd
suzano.cmd
```

Exemplos no console:

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

Ambiente de desenvolvimento:

```bash
python -m pip install -e ".[dev]"
```

Observabilidade opcional:

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

`quality` executa o contrato do dataset. `timeline` mostra versões preservadas. `at` reconstrói o registro no instante solicitado. `diff` resume mudanças observadas. `manifest` descreve a geração e `verify` confere sua integridade.

# Modelo temporal

`PublicRecord` é a unidade normalizada. Mudanças substantivas podem gerar uma `RecordVersion` completa:

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

A segurança básica do snapshot é determinística. Integrações externas podem complementar a observação, mas não substituem o contrato interno.

# Manifestos e integridade

Uma geração pode publicar metadados como:

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

Artefatos rolling incluem:

```text
suzano-aberta.sqlite3.gz
suzano-aberta.sqlite3.gz.sha256
suzano-aberta.manifest.json
data-latest.json
```

Antes da promoção, o pipeline valida SQLite, FTS, cobertura e contrato. Se a nova geração falhar, o último estado conhecido como saudável permanece disponível.

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

Execuções importantes podem registrar eventos `START`, `COMPLETE` e `FAIL` no journal local, com conceitos compatíveis com OpenLineage.

```bash
suzano data lineage
```

OpenTelemetry é opcional. Sem SDK/exporter configurado, a instrumentação é no-op. Telemetria e lineage não fazem parte do caminho crítico de disponibilidade.

# Source SDK

Fontes implementam definição e coletor. O registry padrão inclui integrações do projeto e descobre plugins instalados pelo grupo Python:

```text
suzano_aberta.sources
```

```python
from suzano_aberta import default_source_registry

registry = default_source_registry()
for source in registry.registrations():
    print(source.definition.key, source.origin)
```

Isso permite adicionar integrações em pacotes separados sem editar o core.

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

Rotas centrais incluem:

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

O serviço utiliza OpenAPI, Problem Details, request IDs, ETags, limites explícitos e snapshots de leitura. Não existe endpoint público destinado a substituir ou editar arbitrariamente o banco.

O módulo da Linha 11 é deliberadamente separado da API operacional: ele é publicado como artefato estático de notícias no GitHub Pages.

# Autopilot

A coleta pesada é centralizada em workflows públicos. Instalações locais verificam checksums e só transferem o banco completo quando a geração muda.

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

Biblioteca, CLI, API, portal e aplicativos podem permanecer atualizados sem operação manual rotineira.

# Portal público

O portal em GitHub Pages consome artefatos validados, mantém links para as fontes e publica produtos derivados da infraestrutura comum.

```text
https://mukasanches.github.io/suzano-aberta/
```

A reconstrução é automatizada por GitHub Actions. Briefings, notícias agregadas, indicadores e módulos especiais devem continuar rastreáveis ao material que sustenta cada afirmação.

# Estrutura do repositório

```text
.github/workflows/   CI, segurança, portal, snapshots, Android e iOS
brand/               identidade visual
config/              configuração de fontes e operação
docs/                documentação técnica e operacional
mobile/android/      wrapper Android nativo
mobile/ios/          wrapper iOS/iPadOS nativo em SwiftUI + WKWebView
scripts/             automação, geração e utilitários
src/suzano_aberta/   biblioteca, engine, CLI e API
tests/               testes unitários, integração e contratos
web/                 portal público e Web App canônico
```

# Engenharia e testes

A matriz de qualidade inclui, conforme o workflow:

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
build do APK Release
verificação de assinatura Android
XcodeGen
xcodebuild para iOS Simulator
artifact iOS de simulador
```

A intenção é detectar regressões em invariantes e contratos, não apenas verificar se a interface abre.

# Segurança e limites

- conteúdo externo é tratado como dado, não como comando;
- a API pública é read-only;
- URLs de origem são preservadas para auditoria;
- hashes demonstram integridade de bytes, não autenticidade jurídica;
- ausência numa coleta não prova ausência no mundo real;
- classificações automatizadas devem expor sua metodologia;
- o status da Linha 11 é estimativa por notícias, não telemetria da operadora;
- OpenTelemetry/OpenLineage são observabilidade, não dependências de disponibilidade;
- o último snapshot saudável deve sobreviver a falhas de rede, fonte, validação ou promoção;
- o app Android bloqueia HTTP em claro e mixed content;
- o wrapper iOS restringe a navegação interna ao host do Suzano Aberta e entrega links externos ao sistema;
- o Web App continua disponível mesmo sem distribuição por loja;
- a operação normal do sistema não depende de IA generativa.

# Desenvolvimento

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src/suzano_aberta
pytest
python -m build
```

Validação mobile compartilhada:

```bash
node --check web/app/app.js
node --check web/app/sw.js
node --test tests/mobile-app.test.mjs
```

Build Android, dentro de `mobile/android/`:

```bash
gradle :app:lintRelease :app:assembleRelease
```

Build iOS, em macOS com XcodeGen e Xcode instalados:

```bash
cd mobile/ios
xcodegen generate
xcodebuild \
  -project SuzanoAberta.xcodeproj \
  -scheme SuzanoAberta \
  -configuration Debug \
  -destination "generic/platform=iOS Simulator" \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  clean build
```

# Contribuição, governança e segurança

Leia também:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [GOVERNANCE.md](GOVERNANCE.md)
- [SECURITY.md](SECURITY.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [CHANGELOG.md](CHANGELOG.md)
- [ANDROID.md](ANDROID.md)
- [IOS.md](IOS.md)
- [`docs/`](docs/)

# Licença

Código distribuído sob a [Apache License 2.0](LICENSE), salvo quando um arquivo ou componente indicar condição diferente.

Dados, notícias e documentos provenientes de terceiros continuam sujeitos às regras, licenças, direitos e condições das respectivas fontes.

---

**Suzano Aberta** — infraestrutura independente para tornar informação pública local mais encontrável, verificável, preservável e reutilizável em web, Android e iOS.