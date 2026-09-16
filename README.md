<p align="center">
  <img src="brand/logo-horizontal.svg" width="520" alt="Suzano Aberta — informação pública, rastreável e aberta">
</p>

<p align="center">
  <strong>Uma infraestrutura cívica local-first para encontrar, preservar, pesquisar e reutilizar informação pública relacionada a Suzano, SP — sempre mantendo o caminho de volta à fonte.</strong>
</p>

<p align="center">
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="Licença Apache 2.0" src="https://img.shields.io/badge/licen%C3%A7a-Apache--2.0-102A43"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-0B6E4F">
  <img alt="Biblioteca 0.9.0" src="https://img.shields.io/badge/library-0.9.0-102A43">
  <img alt="API 1.2" src="https://img.shields.io/badge/API-1.2-0B6E4F">
  <img alt="SQLite local-first" src="https://img.shields.io/badge/storage-SQLite-102A43">
  <img alt="Windows CMD" src="https://img.shields.io/badge/Windows-CMD-0B6E4F">
</p>

> **Projeto cívico independente.** O Suzano Aberta não é um portal oficial da Prefeitura Municipal de Suzano, da Câmara Municipal de Suzano ou de qualquer mandato, partido ou candidatura. Em caso de divergência, a publicação da fonte responsável é a referência.

## A ideia em 20 segundos

Informação pública existe, mas normalmente está separada entre portais, páginas, PDFs, diários, sistemas de contratação e APIs. O Suzano Aberta cria uma camada técnica comum sobre esse material: descobre, coleta, normaliza, preserva, indexa e disponibiliza os registros por terminal, Python, HTTP e web.

O projeto não tenta substituir a fonte oficial. Ele faz o oposto: **cada registro deve continuar apontando para ela**.

```text
┌──────────────────────────────── FONTES PÚBLICAS ────────────────────────────────┐
│ Câmara · Prefeitura · PNCP · Compras.gov.br · páginas · documentos · arquivos │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │
                                       ▼
                         coleta + descoberta responsável
                                       │
                                       ▼
                           PublicRecord + SourceRef
                                       │
                     ┌─────────────────┴─────────────────┐
                     ▼                                   ▼
             SQLite + histórico                  documentos/arquivos
                     │
                     ▼
              FTS5 + ranking BM25
                     │
        ┌────────────┼────────────┬───────────────┬──────────────┐
        ▼            ▼            ▼               ▼              ▼
   Windows/CMD      CLI       Python SDK       API HTTP       Portal web
        │            │            │               │              │
        └────────────┴────────────┴───────┬───────┴──────────────┘
                                          ▼
                              mesma origem rastreável
```

## Experimente primeiro, leia depois

No Windows, dentro da pasta do projeto:

```cmd
instalar-windows.cmd
suzano.cmd
```

Na primeira tela, o programa mostra o estado real do ambiente local. Depois:

```text
suzano› sincronizar
suzano› diagnostico
suzano› recentes
suzano› educação
```

Uma busca produz resultados numerados. Você pode abrir o primeiro apenas digitando:

```text
suzano› 1
```

E consultar ou abrir a fonte pública original:

```text
suzano› fonte 1
suzano› abrir 1
```

Não é necessário decorar a sintaxe de busca: no console, texto que não corresponde a um comando conhecido é tratado como consulta.

---

# O que a versão 0.9 entrega

| Camada | Capacidade |
| --- | --- |
| Coleta | adaptadores independentes para fontes municipais e nacionais |
| Descoberta | páginas, sitemaps, documentos e referências históricas públicas |
| Normalização | `PublicRecord` + `SourceRef` com origem preservada |
| Persistência | SQLite local-first com histórico e fingerprints determinísticos |
| Busca | FTS5 Unicode, remoção de diacríticos, prefixos e BM25 |
| Snapshot | distribuição rolling validada, checksum-first e instalação atômica |
| Autopilot | política de frescor, locks, backoff, last-known-good e estado persistente |
| Windows | instalador verificado, launcher UTF-8, console navegável e autorreparo |
| Diagnóstico | inspeção local de Python, disco, SQLite, FTS5, JSON1 e `quick_check` |
| Python | `Suzano`, `SuzanoIndex`, `SuzanoClient`, `AutonomousDataManager` e modelos tipados |
| HTTP | API v1.2 somente leitura, OpenAPI, Problem Details e estado do Autopilot |
| Proveniência | metadados por registro e representação interoperável |
| Entidades | IDs canônicos determinísticos e menções com evidência |
| Qualidade | métricas técnicas reproduzíveis sobre conjuntos de registros |
| Portal | interface pública API-first com fallback estático e operação autônoma |
| Engenharia | CI multi-Python, mypy strict, testes, build, container e CodeQL |

O núcleo de coleta e consulta não depende de IA. O objetivo é que resultados importantes possam ser reproduzidos e auditados com regras explícitas.

---

# Instalação

## Windows — experiência recomendada

Requer Python 3.11, 3.12 ou 3.13.

```cmd
instalar-windows.cmd
```

O instalador procura uma versão compatível do Python, cria um ambiente virtual isolado, atualiza `pip`, instala as dependências declaradas, executa `pip check`, compila o pacote e roda smoke tests. Ele interrompe o processo se uma etapa falhar.

Depois:

```cmd
suzano.cmd
```

Se o ambiente virtual ficar corrompido, o reparo recria somente `.venv` e preserva o banco:

```cmd
suzano.cmd reparar
```

Guia detalhado: [Windows e CMD](docs/windows-cmd.md).

## Linux e macOS

```bash
git clone https://github.com/MukaSanches/suzano-aberta.git
cd suzano-aberta
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
suzano sincronizar
suzano inicio
```

## Instalação manual no Windows

```powershell
git clone https://github.com/MukaSanches/suzano-aberta.git
cd suzano-aberta
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
suzano sincronizar
```

---

# Console interativo

O console mantém estado apenas durante a sessão para facilitar navegação. A última lista de resultados pode ser referenciada por posição, sem alterar o ID real do registro.

```text
suzano› ajuda
suzano› status
suzano› diagnostico
suzano› recentes 20
suzano› transporte escolar
suzano› 2
suzano› fonte 2
suzano› abrir 2
suzano› panorama
suzano› mudancas 20
suzano› fontes
suzano› sobre
suzano› sair
```

Atalhos:

```text
b = buscar       v = ver          r = recentes
p = panorama     m = mudancas     f = fontes
diag = diagnostico               q = sair
```

A abertura do navegador é sempre explícita. Uma busca normal não abre páginas externas automaticamente.

---

# CLI

O CLI continua adequado para scripts, automação e uso técnico. A partir da 0.9, a manutenção automática do snapshot é uma superfície de primeira classe.

```text
suzano inicio
suzano diagnostico
suzano recentes
suzano console
suzano auto status
suzano auto agora
suzano auto vigiar
suzano fontes
suzano doctor
suzano integridade
suzano coletar
suzano atualizar
suzano acervo-maximo
suzano sincronizar
suzano reindexar
suzano buscar
suzano ver
suzano panorama
suzano mudancas
suzano exportar
```

Exemplos:

```bash
suzano inicio
suzano auto status
suzano auto agora
suzano auto vigiar --intervalo 900
suzano diagnostico --json
suzano recentes --limite 25
suzano coletar --ano 2026
suzano atualizar --anos 2024,2025,2026
suzano atualizar --max-paginas 1500 --profundidade 4
suzano buscar "educação"
suzano buscar "transporte escolar" --limite 10
suzano ver <id-exato>
suzano panorama --json
suzano mudancas --limite 50
suzano integridade --json
suzano exportar acervo.json
```

`auto vigiar` mantém um processo verificando novas gerações do snapshot enquanto estiver ativo. Após falha transitória usa backoff menor; após sucesso retorna à cadência normal. `ver` usa o ID exato do registro. `acervo-maximo` amplia os limites de descoberta e inclui índices históricos; é propositalmente mais pesado que a atualização normal.

---

# Diagnóstico local

O projeto diferencia problemas da máquina local de problemas das fontes na internet.

```bash
suzano diagnostico
```

A inspeção local verifica:

- Python suportado;
- existência e permissão de escrita do diretório de dados;
- espaço livre;
- abertura do banco SQLite;
- presença da tabela de registros;
- quantidade de registros ativos;
- FTS5;
- `PRAGMA quick_check` no modo profundo;
- extensão JSON1 utilizada por consultas estruturadas.

Para automação:

```bash
suzano diagnostico --json
```

A função também está disponível na biblioteca:

```python
from suzano_aberta import inspect_local_environment

report = inspect_local_environment("suzano-aberta.sqlite3", deep=True)
print(report.healthy)
for check in report.checks:
    print(check.status, check.name, check.detail)
```

O diagnóstico abre o snapshot para leitura e não executa coleta, reindexação ou mutação do acervo.

---

# Modelo de dados

## `PublicRecord`

É a unidade normalizada do acervo. Campos compartilhados incluem:

```text
id
kind
title
summary
date
year
attributes
source
```

Os tipos atuais abrangem sessões, vereadores, proposições, leis, decretos, contratos, atas, comissões, presenças, diários, licitações, secretarias, documentos fiscais/orçamentários, atos oficiais, notícias, páginas web, arquivos e referências históricas.

## `SourceRef`

Preserva nome e URL da origem, instante de coleta e, quando disponível, hash, autoridade, categoria, método de recuperação e media type.

Um hash é uma ferramenta técnica de rastreabilidade; não equivale a assinatura digital ou autenticação jurídica da publicação.

## Fingerprint e mudanças

Cada registro possui uma impressão determinística sobre campos substantivos. Se o mesmo ID reaparece com conteúdo canônico diferente, a observação pode gerar um evento `alterado`.

O desaparecimento temporário de um item não é automaticamente convertido em revogação, exclusão ou cancelamento, porque uma fonte pública pode estar incompleta ou indisponível.

---

# Busca local

O caminho principal usa SQLite FTS5 com tokenização Unicode e remoção de diacríticos. Assim, `educacao` pode encontrar `Educação`, e prefixos ajudam a localizar variações do termo.

O ranking BM25 dá pesos diferentes para título, resumo, atributos e fonte. Se FTS5 não estiver disponível, existe fallback compatível de pesquisa.

O mesmo snapshot alimenta diferentes interfaces; a ideia é evitar que o portal, o CLI e a biblioteca tenham definições conflitantes de pesquisa.

---

# Fontes e cobertura

O catálogo inclui fontes da Câmara Municipal de Suzano, Prefeitura Municipal de Suzano, Portal Nacional de Contratações Públicas (PNCP) e Compras.gov.br Dados Abertos, além de mecanismos de descoberta de páginas, documentos e referências históricas.

Entre os materiais municipais coletados ou descobertos estão sessões, proposições, contratos, comissões, diário legislativo, licitações, secretarias, contas públicas, orçamento, imprensa oficial, atos normativos e notícias.

A cobertura nunca é apresentada como absoluta. Ela depende do que as fontes publicam, da estrutura disponível e da disponibilidade observada. Uma falha em uma fonte não autoriza preencher lacunas por suposição.

Leitura recomendada: [Fontes](docs/fontes.md), [Metodologia](docs/metodologia.md) e [Política de fontes upstream](docs/UPSTREAM-SOURCES.md).

---

# Snapshot e Autopilot

Coletar é mais caro que pesquisar. Por isso, o projeto publica um snapshot SQLite já indexado:

```text
suzano-aberta.sqlite3.gz
suzano-aberta.sqlite3.gz.sha256
data-latest.json
```

O comando:

```bash
suzano sincronizar
```

consulta primeiro o checksum remoto. Se o release instalado ainda for o atual e o SQLite local estiver íntegro, o banco completo não é transferido de novo. Quando existe uma geração nova, o candidato passa por checksum, cabeçalho SQLite, `PRAGMA quick_check`, cobertura mínima e consistência FTS antes de uma substituição atômica.

A biblioteca usa a mesma política automaticamente nas operações de leitura. Estado, falhas e próxima checagem ficam disponíveis em `suzano auto status` e programaticamente por `AutonomousDataManager`.

Para processamento do corpus inteiro, o snapshot é preferível a paginar milhares de respostas pela API.

---

# Python

## `Suzano` — coleta e operação autônoma

```python
from suzano_aberta import Suzano

with Suzano() as suzano:
    resultados = suzano.search("educação", limit=20)
    for registro in resultados:
        print(registro.id, registro.title, registro.source.url)
    print(suzano.autopilot_status())
```

Com `auto_sync=True` (padrão), leituras verificam periodicamente se há snapshot validado mais novo. A checagem é limitada por intervalo e normalmente consulta apenas o checksum.

Controle explícito:

```python
from suzano_aberta import AutoUpdatePolicy, AutonomousDataManager

manager = AutonomousDataManager(
    "suzano-aberta.sqlite3",
    policy=AutoUpdatePolicy(check_interval_seconds=900),
)
result = manager.ensure_fresh()
print(result.action, result.records)
```

Atualização pesada programática continua disponível separadamente:

```python
from suzano_aberta import Suzano

with Suzano(auto_sync=False) as suzano:
    relatorio = suzano.refresh(
        years=[2025, 2026],
        max_pages=1000,
        max_depth=3,
    )
    print(relatorio.indexed_records)
```

## `SuzanoIndex` — snapshot local somente leitura

```python
from suzano_aberta import SuzanoIndex

with SuzanoIndex("suzano-aberta.sqlite3") as index:
    pagina = index.search("transporte escolar", year=2026, limit=25)
    for registro in pagina.items:
        print(registro.id, registro.title)
```

`SuzanoIndex` compartilha a camada de consulta da API e oferece `record`, `records`, `search`, `documents`, `legislation`, `procurements`, `changes`, `stats` e iteração paginada.

## `SuzanoClient` — HTTP tipado

```python
from suzano_aberta import SuzanoClient

with SuzanoClient("http://127.0.0.1:8000") as client:
    pagina = client.search("educação", year=2026)
    for registro in pagina.items:
        print(registro.title)
    print(client.autopilot().fresh)
```

Falhas HTTP estruturadas são representadas por `SuzanoApiError`.

Guia: [Interfaces Python](docs/python-client.md) e [Núcleo autônomo](docs/autonomous-core.md).

---

# Entidades e relações

A camada de entidades é derivada; ela não substitui o registro original.

```python
from suzano_aberta import SuzanoIndex, build_entity_graph

with SuzanoIndex("suzano-aberta.sqlite3") as index:
    pagina = index.procurements("", limit=100)

grafo = build_entity_graph(pagina.items)
for entidade in grafo.entities:
    print(entidade.id, entidade.kind, entidade.identifier, entidade.records)
```

IDs canônicos são determinísticos. Quando um identificador forte está disponível, ele tem precedência sobre semelhança vaga de nomes. A geração atual reconhece o órgão declarado pela fonte e CNPJ explicitamente publicado.

Uma menção de CNPJ significa que aquele identificador foi observado no registro. Sozinha, ela não prova pagamento, propriedade, responsabilidade, irregularidade, sociedade empresarial ou qualquer vínculo político.

Detalhes: [Entidades e relações](docs/entidades-e-relacoes.md).

---

# Qualidade de dados

```python
from suzano_aberta import SuzanoIndex, quality_report

with SuzanoIndex("suzano-aberta.sqlite3") as index:
    pagina = index.records(limit=100)

relatorio = quality_report(pagina.items)
print(relatorio.completeness)
print(relatorio.uniqueness)
```

`QualityReport` mede propriedades técnicas com definição reproduzível, como presença de título/URL e unicidade de IDs. Não é uma nota sobre governo, órgão, agente público, política ou legalidade.

Detalhes: [Qualidade de dados](docs/qualidade-de-dados.md).

---

# API HTTP 1.2

Inicie:

```bash
suzano-api
```

Padrão local:

```text
http://127.0.0.1:8000
```

Documentação automática:

```text
/docs
/redoc
/openapi.json
```

Superfície principal:

```text
GET /v1/search
GET /v1/records
GET /v1/records/{id}
GET /v1/documents
GET /v1/legislation
GET /v1/procurements
GET /v1/changes
GET /v1/stats
GET /v1/sources
GET /v1/capabilities
GET /v1/catalog
GET /v1/records/{id}/provenance
GET /v1/snapshot
GET /v1/autopilot
GET /health/live
GET /health/ready
GET /metrics
```

A API é deliberadamente **somente leitura** para clientes HTTP. Não existem endpoints públicos para disparar crawlers, alterar registros, apagar dados ou reindexar o banco. A manutenção do snapshot ocorre internamente, por padrão a cada 900 segundos, usando a mesma estratégia checksum-first.

Ela inclui limites de paginação, filtros, ordenação, `ETag`, cache HTTP, request ID, `Server-Timing`, erros compatíveis com Problem Details, proveniência JSON-LD, catálogo orientado a interoperabilidade e status observável do Autopilot.

A versão do pacote (`0.9.0`) e a versão do contrato HTTP (`1.2.0`) são independentes.

Detalhes: [API pública](docs/api.md), [Núcleo autônomo](docs/autonomous-core.md), [Contrato](docs/API-CONTRACT.md) e [Governança da API](docs/api-governance.md).

---

# Docker

```bash
docker compose up --build
```

Ou:

```bash
docker build -t suzano-aberta-api .
docker run --rm -p 8000:8000 -v suzano-data:/data suzano-aberta-api
```

A imagem da API usa usuário não privilegiado. A camada de serviço abre o snapshot em modo somente leitura e aplica controles SQLite voltados a esse limite de confiança.

---

# Portal web

O portal em GitHub Pages é uma interface pública de leitura. Ele não dispara coletores e não altera o acervo.

Quando uma API pública está configurada, usa a API v1. Sem ela, pode trabalhar com um índice estático derivado do snapshot em Web Worker. A publicação valida o banco antes de gerar o artefato.

A implementação prioriza navegação responsiva, acessibilidade, origem visível e ausência de analytics de terceiros no núcleo.

Portal: https://mukasanches.github.io/suzano-aberta/

Detalhes: [Portal web](docs/portal-web.md) e [Autopilot do portal](docs/autopilot.md).

---

# Saúde, integridade e segurança

Há quatro perguntas diferentes:

```text
suzano diagnostico  -> minha instalação local está funcional?
suzano auto status  -> meu dataset local está fresco e atualizando?
suzano doctor       -> as fontes catalogadas estão acessíveis agora?
suzano integridade  -> uma verificação específica encontrou referência externa inesperada?
```

Esses sinais não são misturados. Um domínio externo inesperado, por exemplo, é um item para revisão humana e não uma conclusão automática sobre invasão, fraude, autoria ou irregularidade.

Conteúdo remoto é tratado como entrada não confiável. A camada HTTP usa timeout, limites de resposta, redirects controlados e retries restritos. O crawler possui fronteiras de host e respeita `robots.txt` onde aplicável.

O repositório usa CI, mypy em modo estrito, testes determinísticos, build de pacote, build de container, CodeQL, Dependabot e Actions fixadas por SHA nos workflows mantidos.

O projeto não afirma certificação formal de segurança. Uma implantação pública continua precisando de TLS, rate limiting, política de rede, logs, backups e observabilidade compatíveis com o ambiente.

Leia [SECURITY.md](SECURITY.md), [Integridade](docs/integridade.md) e [Fronteiras de segurança](docs/SECURITY-BOUNDARIES.md).

---

# Princípios de engenharia

1. **Fonte antes da interpretação.** O caminho até a publicação original faz parte do dado.
2. **Dado ausente é melhor que dado inventado.** Parsers não completam campos por conveniência.
3. **Falhar sem destruir.** Uma atualização quebrada não deve eliminar o último acervo válido.
4. **Relações exigem evidência.** Similaridade de texto, sozinha, não vira vínculo factual.
5. **Identificadores fortes têm precedência.** Chaves públicas estáveis superam heurísticas vagas.
6. **Métricas precisam ser reproduzíveis.** Qualidade técnica não é avaliação política.
7. **Local-first por padrão.** Uma pesquisa deve poder existir sem uma plataforma externa obrigatória.
8. **Ingestão e serviço são separados.** A API pública continua somente leitura.
9. **Regressões importantes precisam de teste.** Parsers, busca, versões e contratos são verificáveis.
10. **A fonte responsável permanece a referência.** O projeto melhora acesso, não substitui autoridade documental.

---

# Limitações deliberadas

O Suzano Aberta não garante uma cópia completa de toda informação pública existente; não contorna autenticação ou bloqueios para fingir que um serviço é aberto; não faz OCR automático de todo PDF digitalizado; não fornece parecer jurídico; não infere intenção; não transforma ausência temporária em revogação; e não trata correlação como prova.

A série `0.x` continua permitindo evolução de interface. Mudanças relevantes devem ser registradas no [Changelog](CHANGELOG.md).

Detalhes: [Limitações](docs/limitacoes.md).

---

# Estrutura do repositório

```text
suzano-aberta/
├── src/suzano_aberta/
│   ├── api/               API HTTP somente leitura
│   ├── sources/           adaptadores de fontes públicas
│   ├── autopilot.py       política e estado de atualização automática
│   ├── autopilot_cli.py   comandos `suzano auto`
│   ├── cli.py             CLI para uso direto e automação
│   ├── console.py         experiência interativa navegável
│   ├── diagnostics.py     saúde local reproduzível
│   ├── core.py            coleta e operações principais
│   ├── snapshot.py        instalação validada e checksum-first
│   ├── store.py           persistência, histórico e FTS5
│   ├── index.py           consulta SQLite tipada
│   ├── client.py          cliente HTTP tipado
│   ├── entities.py        entidades e menções auditáveis
│   ├── provenance.py      proveniência e catálogo
│   └── quality.py         métricas técnicas
├── web/                   portal público
├── docs/                  documentação técnica
├── tests/                 testes determinísticos
├── tests_live/            verificações separadas contra fontes reais
├── scripts/               geração, build e validação
├── brand/                 identidade visual
├── .github/workflows/     CI, segurança, coleta e publicação
├── instalar-windows.cmd   instalação/reparo Windows
└── suzano.cmd             launcher Windows
```

---

# Desenvolvimento

Prepare o ambiente:

```bash
python -m pip install -e ".[dev]"
```

Execute a mesma família de verificações esperada pelo projeto:

```bash
python -m compileall -q src tests
ruff check .
mypy src/suzano_aberta
pytest
python scripts/check_web.py
python -m build
```

O CI testa Python 3.11, 3.12 e 3.13, instala as dependências declaradas, executa verificação estática, type checking, testes, smoke tests das superfícies públicas, constrói wheel/sdist e constrói o container da API.

Testes unitários não devem depender da internet. Verificações de fontes reais permanecem isoladas em `tests_live/` para que uma indisponibilidade externa não torne o teste determinístico imprevisível.

Leia [CONTRIBUTING.md](CONTRIBUTING.md) antes de alterar parsers ou fontes.

---

# Documentação

- [Windows e CMD](docs/windows-cmd.md)
- [Arquitetura](docs/arquitetura.md)
- [Autonomia e busca](docs/autonomia-e-busca.md)
- [Núcleo autônomo](docs/autonomous-core.md)
- [Autopilot do portal](docs/autopilot.md)
- [Modelo de dados](docs/modelo-de-dados.md)
- [Entidades e relações](docs/entidades-e-relacoes.md)
- [Qualidade de dados](docs/qualidade-de-dados.md)
- [API pública](docs/api.md)
- [Interfaces Python](docs/python-client.md)
- [Contrato da API](docs/API-CONTRACT.md)
- [Governança da API](docs/api-governance.md)
- [Fronteiras de segurança](docs/SECURITY-BOUNDARIES.md)
- [Política de fontes upstream](docs/UPSTREAM-SOURCES.md)
- [Fontes](docs/fontes.md)
- [Metodologia](docs/metodologia.md)
- [Integridade](docs/integridade.md)
- [Limitações](docs/limitacoes.md)
- [Portal web](docs/portal-web.md)
- [Demonstração institucional](docs/demo-institucional.md)
- [Identidade visual](brand/README.md)
- [Governança](GOVERNANCE.md)
- [Segurança](SECURITY.md)
- [Contribuição](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

---

# Licença e citação

O código é distribuído sob **Apache License 2.0**. Dados, páginas e documentos acessados pelo projeto permanecem sujeitos às regras, licenças, direitos e condições das respectivas fontes originais.

Se utilizar o software em pesquisa ou análise reproduzível, registre a versão do pacote e, quando relevante, a versão/data do snapshot. Metadados de citação estão em [CITATION.cff](CITATION.cff).
