<p align="center">
  <img src="brand/logo-horizontal.svg" width="520" alt="Suzano Aberta — informação pública, rastreável e aberta">
</p>

<p align="center">
  <strong>Infraestrutura aberta, local-first e rastreável para descobrir, preservar, pesquisar e reutilizar informação pública relacionada a Suzano, SP.</strong>
</p>

<p align="center">
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="Licença Apache 2.0" src="https://img.shields.io/badge/licen%C3%A7a-Apache--2.0-102A43"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-0B6E4F">
  <img alt="Biblioteca 0.7.0" src="https://img.shields.io/badge/library-0.7.0-102A43">
  <img alt="API 1.2" src="https://img.shields.io/badge/API-1.2-0B6E4F">
  <img alt="Windows CMD" src="https://img.shields.io/badge/Windows-CMD-102A43">
</p>

> **Projeto cívico independente.** O Suzano Aberta não é um portal oficial da Prefeitura Municipal de Suzano, da Câmara Municipal de Suzano ou de qualquer mandato, partido ou candidatura. Em caso de divergência, a publicação da fonte responsável é a referência.

## O que é

Informações públicas relevantes para Suzano estão espalhadas por páginas institucionais, portais de transparência, diários, documentos, APIs nacionais e arquivos históricos. O Suzano Aberta cria uma camada técnica comum sobre esse material: coleta o que é publicamente acessível, normaliza registros, preserva a origem, indexa o conteúdo e oferece várias formas de consulta.

O mesmo acervo pode ser usado por uma pessoa no CMD, por scripts Python, por uma aplicação via API HTTP ou pelo portal web. O projeto não precisa de IA para coletar ou pesquisar e não transforma correlação em acusação.

```text
Câmara + Prefeitura + PNCP + Compras.gov.br + web/arquivos públicos
                              │
                              ▼
                 coleta / descoberta responsável
                              │
                              ▼
                    PublicRecord + SourceRef
                              │
                   ┌──────────┴──────────┐
                   ▼                     ▼
             SQLite + histórico      documentos
                   │
                   ▼
                FTS5 / busca
                   │
        ┌──────────┼───────────┬─────────────┐
        ▼          ▼           ▼             ▼
      CLI/CMD   Python SDK   API HTTP     portal web
```

## Para que serve

O projeto permite pesquisar publicações por texto, consultar registros preservando a URL de origem, acompanhar mudanças observadas entre coletas, consultar leis/proposições/documentos/contratações, trabalhar com snapshots locais, criar aplicações sobre uma API somente leitura, analisar entidades por identificadores verificáveis e medir propriedades técnicas do conjunto de dados.

Ele pode ser útil para cidadãos, jornalistas, pesquisadores, universidades, desenvolvedores, organizações civis, equipes técnicas e órgãos que precisem reutilizar informação pública sem construir cada integração do zero.

## O que existe hoje

- coletores estruturados para Câmara e Prefeitura;
- integração com PNCP e Compras.gov.br;
- descoberta de páginas e documentos públicos;
- referências históricas via índices públicos de preservação;
- extração pesquisável de formatos documentais suportados;
- modelo normalizado `PublicRecord` + `SourceRef`;
- SQLite local-first com trilha de mudanças;
- busca FTS5 Unicode, prefixos e ranking BM25;
- snapshot rolling com SHA-256 e validação SQLite;
- CLI tradicional em português;
- console interativo para Windows/CMD;
- instalador e launcher `.cmd`;
- API HTTP v1.2 somente leitura com OpenAPI;
- `SuzanoClient` para HTTP e `SuzanoIndex` para SQLite local;
- portal público com estratégia API-first e fallback estático;
- proveniência por registro e catálogo interoperável;
- entidades canônicas determinísticas;
- reconhecimento conservador de órgão de origem e CNPJ explicitamente publicado;
- métricas técnicas de qualidade de dados;
- Docker para a API;
- CI em Python 3.11, 3.12 e 3.13;
- build de pacote, container, CodeQL, Dependabot e smoke tests de fontes reais.

---

# Comece aqui

## Windows — forma mais fácil

Requer **Python 3.11 ou superior**.

Clone ou baixe o repositório e, dentro da pasta, execute:

```cmd
instalar-windows.cmd
```

O instalador verifica o Python, cria um ambiente virtual isolado, instala as dependências, executa verificações e abre o programa somente quando a preparação termina corretamente.

Nas próximas vezes:

```cmd
suzano.cmd
```

Você verá um prompt persistente:

```text
suzano>
```

Primeiro uso recomendado:

```text
suzano> sincronizar
suzano> status
suzano> buscar educação
suzano> buscar "transporte escolar"
suzano> panorama
suzano> ajuda
```

O comando `buscar` mostra o ID de cada resultado. Para abrir um item:

```text
suzano> ver <ID>
```

Guia completo: [Windows e CMD](docs/windows-cmd.md).

## Windows — comandos diretos

Sem entrar no console interativo:

```cmd
suzano.cmd fontes
suzano.cmd sincronizar
suzano.cmd buscar "educação"
suzano.cmd panorama
suzano.cmd mudancas --limite 20
suzano.cmd doctor
suzano.cmd integridade
suzano.cmd atualizar
suzano.cmd exportar dados.json
```

Depois que o pacote está instalado, o console também possui entrypoint próprio:

```cmd
suzano-console
```

## Linux e macOS

```bash
git clone https://github.com/MukaSanches/suzano-aberta.git
cd suzano-aberta
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
suzano sincronizar
suzano buscar "educação"
```

## Instalação manual no Windows

```powershell
git clone https://github.com/MukaSanches/suzano-aberta.git
cd suzano-aberta
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
suzano sincronizar
```

---

# CLI

Os comandos operacionais principais são:

```text
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

Descubra opções sem consultar documentação externa:

```bash
suzano --help
suzano buscar --help
suzano atualizar --help
suzano acervo-maximo --help
```

### Exemplos

```bash
suzano coletar --ano 2026
suzano atualizar --anos 2024,2025,2026
suzano atualizar --max-paginas 1500 --profundidade 4
suzano buscar "educação"
suzano buscar "transporte escolar" --limite 10
suzano panorama --json
suzano mudancas --limite 50
suzano integridade --json
suzano exportar acervo.json
```

`acervo-maximo` aumenta os limites de descoberta e inclui índices históricos. É uma operação mais pesada que a atualização normal.

---

# Como os dados funcionam

## PublicRecord

`PublicRecord` é a unidade normalizada. Os campos comuns incluem ID estável, tipo, título, resumo, data, ano, atributos específicos e referência à fonte.

Tipos atuais incluem sessões, vereadores, proposições, leis, decretos, contratos, atas, comissões, presenças, diários, licitações, secretarias, documentos fiscais/orçamentários, atos oficiais, notícias, páginas web, arquivos e referências históricas.

## SourceRef

Cada registro conserva sua origem. `SourceRef` pode incluir nome, URL, instante de coleta, hash, autoridade, categoria, método de recuperação e media type. O objetivo é permitir que o consumidor volte à publicação original.

## Histórico

O SQLite mantém a versão mais recente observada de cada ID e uma tabela de mudanças. Fingerprints SHA-256 determinísticos identificam alteração substantiva sem considerar metadados operacionais voláteis.

O desaparecimento temporário de uma página não é automaticamente interpretado como revogação, cancelamento ou exclusão.

---

# Busca

FTS5 é o caminho principal da pesquisa textual. A tokenização Unicode remove diacríticos para pesquisa, então consultas como `educacao` podem encontrar `Educação`. Prefixos e BM25 ajudam a ordenar resultados.

Quando FTS5 não está disponível, existe fallback compatível. O banco utiliza ajustes locais de SQLite voltados à consulta e manutenção do índice sem exigir Elasticsearch, servidor proprietário ou serviço externo.

A busca normal pode instalar automaticamente o snapshot quando o banco ainda não está preparado. Se não houver resultado local, o modo tradicional pode tentar descoberta recente na web, salvo quando `--sem-web` é usado.

---

# Fontes e cobertura

O catálogo inclui publicações da **Câmara Municipal de Suzano**, **Prefeitura Municipal de Suzano**, **Portal Nacional de Contratações Públicas (PNCP)** e **Compras.gov.br Dados Abertos**, além de mecanismos de descoberta de documentos e referências históricas.

Entre os materiais municipais catalogados estão vereadores, sessões, proposições, contratos, comissões, diário legislativo, licitações, secretarias, contas públicas, orçamento, imprensa oficial, leis/decretos e notícias.

A cobertura depende do que cada fonte publica e de sua disponibilidade. Uma fonte indisponível reduz a observação daquela execução; o software não preenche lacunas por suposição.

Política detalhada: [Fontes](docs/fontes.md), [Metodologia](docs/metodologia.md) e [Política upstream](docs/UPSTREAM-SOURCES.md).

---

# Snapshot

O projeto separa coleta pesada de pesquisa rápida. Workflows podem produzir um snapshot SQLite já indexado e publicá-lo como conjunto rolling.

Arquivos principais:

```text
suzano-aberta.sqlite3.gz
suzano-aberta.sqlite3.gz.sha256
data-latest.json
```

`sincronizar` baixa o snapshot e valida checksum quando disponível, cabeçalho SQLite e integridade antes da instalação. Um snapshot inválido não deve substituir silenciosamente um banco local válido.

Para consumo em massa, prefira o snapshot a paginar todo o acervo pela API.

---

# Biblioteca Python

## Suzano — operações locais

```python
from suzano_aberta import Suzano

with Suzano() as suzano:
    resultados = suzano.search("educação", limit=20)
    for registro in resultados:
        print(registro.id, registro.title, registro.source.url)
```

Atualização programática:

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

## SuzanoIndex — consulta local somente leitura

Quando você já possui o SQLite:

```python
from suzano_aberta import SuzanoIndex

with SuzanoIndex("suzano-aberta.sqlite3") as index:
    pagina = index.search("transporte escolar", year=2026, limit=25)
    for registro in pagina.items:
        print(registro.id, registro.title)
```

`SuzanoIndex` oferece consulta de registros, busca, documentos, legislação, contratações, mudanças, estatísticas e iteração paginada sem precisar subir servidor HTTP.

## SuzanoClient — cliente HTTP tipado

```python
from suzano_aberta import SuzanoClient

with SuzanoClient("http://127.0.0.1:8000") as client:
    pagina = client.search("educação", year=2026)
    for registro in pagina.items:
        print(registro.title)
```

Erros HTTP estruturados são representados por `SuzanoApiError`.

Guia: [Interfaces Python](docs/python-client.md).

---

# Entidades e relações

A versão 0.7 adiciona uma camada derivada de entidades sem substituir os registros originais.

```python
from suzano_aberta import SuzanoIndex, build_entity_graph

with SuzanoIndex("suzano-aberta.sqlite3") as index:
    pagina = index.procurements("", limit=100)

grafo = build_entity_graph(pagina.items)
for entidade in grafo.entities:
    print(entidade.id, entidade.kind, entidade.name, entidade.records)
```

IDs canônicos são determinísticos. Quando existe identificador forte, ele tem precedência sobre semelhança de nomes. A geração atual reconhece o órgão declarado pela fonte e CNPJ explicitamente presente em registros.

A presença de uma entidade em um registro significa que existe evidência daquela menção; não significa automaticamente pagamento, propriedade, irregularidade, sociedade, responsabilidade ou vínculo político.

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

`QualityReport` mede propriedades técnicas reproduzíveis como presença de título/URL e unicidade de IDs. Não é uma nota de governo, órgão, agente público, política ou legalidade.

Detalhes: [Qualidade de dados](docs/qualidade-de-dados.md).

---

# API HTTP 1.2

Inicie:

```bash
suzano-api
```

Por padrão:

```text
http://127.0.0.1:8000
```

Documentação automática:

```text
/docs
/redoc
/openapi.json
```

Rotas principais:

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
GET /health/live
GET /health/ready
GET /metrics
```

A API é **somente leitura**. Ela não possui endpoint público para disparar crawler, alterar registros, apagar dados ou reindexar o banco.

Recursos incluem paginação limitada, filtros, ordenação, `ETag`, cache HTTP, request ID, `Server-Timing`, Problem Details, proveniência JSON-LD e catálogo inspirado em DCAT.

Guia completo: [API pública](docs/api.md) e [Governança da API](docs/api-governance.md).

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

A imagem da API usa usuário não privilegiado. A camada de serviço abre o snapshot como somente leitura com controles SQLite apropriados.

---

# Portal web

O portal é uma camada de leitura e não executa coletores. Quando uma API pública está configurada, usa a API v1; caso contrário, pode usar índice estático derivado do snapshot em Web Worker.

A publicação do portal valida o snapshot antes de gerar os artefatos. A interface foi desenhada para acessibilidade, funcionamento responsivo e ausência de analytics de terceiros no núcleo do projeto.

Detalhes: [Portal web](docs/portal-web.md).

---

# Integridade e saúde das fontes

Duas perguntas são tratadas separadamente:

```bash
suzano doctor
suzano integridade
```

`doctor` verifica acessibilidade básica das fontes catalogadas. `integridade` procura referências externas não reconhecidas em verificações específicas.

Um achado de integridade é um sinal técnico para revisão. Ele não é prova automática de invasão, fraude, autoria ou irregularidade.

Para automação:

```bash
suzano integridade --json
suzano integridade --falhar-se-encontrar
```

Detalhes: [Integridade](docs/integridade.md).

---

# Segurança

O projeto trata conteúdo remoto como entrada não confiável, mesmo quando publicado por uma fonte legítima. A camada HTTP aplica limites, redirects controlados, timeouts e retries restritos. O crawler respeita fronteiras configuradas e `robots.txt` onde aplicável.

A cadeia de desenvolvimento inclui CI, mypy, ruff, testes, CodeQL, Dependabot e Actions fixadas por SHA nos workflows mantidos.

O projeto não afirma certificação formal de segurança. Implantações públicas continuam precisando de TLS, rate limiting, política de rede, logs, backups e monitoramento adequados ao ambiente.

Leia [SECURITY.md](SECURITY.md) e [Fronteiras de segurança](docs/SECURITY-BOUNDARIES.md).

---

# Confiabilidade e princípios

1. **Fonte antes da interpretação.** Todo registro deve manter o caminho até a origem.
2. **Dado ausente é melhor que dado inventado.** Parsers não devem completar campos por adivinhação.
3. **Falhar sem destruir.** Uma coleta quebrada não deve apagar o último acervo válido.
4. **Relações exigem evidência.** Similaridade textual não basta para criar um vínculo factual.
5. **IDs estáveis antes de heurísticas.** Identificadores verificáveis têm precedência.
6. **Métricas precisam de definição reproduzível.** Qualidade técnica não é julgamento político.
7. **Local-first.** SQLite funciona sem infraestrutura obrigatória de servidor.
8. **API pública somente leitura.** Ingestão e serviço ficam separados.
9. **Mudanças importantes precisam de testes.** Parsers e regras relacionais devem ter regressão coberta.
10. **A fonte original permanece soberana.** O índice facilita acesso; não substitui o documento oficial.

---

# O que o projeto não faz

O Suzano Aberta não garante cobertura absoluta de toda informação pública existente, não contorna autenticação ou bloqueios para fingir que uma fonte é pública, não executa OCR automático de todo PDF digitalizado, não fornece parecer jurídico, não atribui culpa, não classifica desempenho político e não trata correlação como prova.

A série `0.x` continua em evolução. Interfaces podem mudar de maneira documentada no changelog.

---

# Estrutura do repositório

```text
suzano-aberta/
├── src/suzano_aberta/
│   ├── api/               API HTTP somente leitura
│   ├── sources/           adaptadores de fontes
│   ├── cli.py             CLI tradicional
│   ├── console.py         console interativo
│   ├── core.py            fachada de coleta/operação
│   ├── store.py           persistência e FTS5
│   ├── index.py           consulta SQLite tipada
│   ├── client.py          cliente HTTP tipado
│   ├── entities.py        entidades e menções
│   ├── provenance.py      proveniência e catálogo
│   └── quality.py         métricas técnicas
├── web/                   portal público
├── docs/                  documentação técnica
├── tests/                 testes determinísticos
├── tests_live/            verificações contra fontes reais
├── scripts/               build, validação e geração
├── brand/                 identidade visual
├── .github/workflows/     CI, segurança, coleta e publicação
├── instalar-windows.cmd   instalador Windows
└── suzano.cmd             launcher Windows
```

---

# Desenvolvimento

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src/suzano_aberta
pytest
python scripts/check_web.py
python -m build
```

O CI repete verificações em Python 3.11, 3.12 e 3.13, constrói o pacote e o container e executa smoke tests das interfaces principais. Testes unitários não devem depender da internet; verificações contra fontes reais ficam separadas.

Leia [CONTRIBUTING.md](CONTRIBUTING.md) antes de alterar parsers ou fontes.

---

# Documentação

- [Windows e CMD](docs/windows-cmd.md)
- [Arquitetura](docs/arquitetura.md)
- [Autonomia e busca](docs/autonomia-e-busca.md)
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

# Licença

O código é distribuído sob **Apache License 2.0**. Dados, páginas e documentos acessados pelo projeto continuam sujeitos às regras, licenças, direitos e condições das respectivas fontes originais.

Se utilizar o software em pesquisa ou análise reproduzível, registre também a versão do pacote e, quando relevante, a versão/data do snapshot consultado.
