# Suzano Aberta

[![CI](https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml/badge.svg)](https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml)

Infraestrutura aberta para descobrir, preservar, organizar e pesquisar informações públicas relacionadas ao município de Suzano, em São Paulo.

O projeto reúne dados estruturados, páginas, documentos e referências históricas em um único índice pesquisável, mantendo a ligação com a fonte original. A partir da versão 0.4, esse acervo também pode ser consultado por uma API HTTP própria.

O Suzano Aberta é independente e não possui vínculo institucional com a Prefeitura Municipal de Suzano ou com a Câmara Municipal de Suzano.

## Em linguagem simples

Informações públicas de uma cidade costumam ficar espalhadas entre páginas, portais, PDFs, planilhas, diários oficiais e sistemas diferentes. O Suzano Aberta tenta transformar esse conjunto disperso em um acervo pesquisável.

A arquitetura atual faz quatro trabalhos principais:

1. coleta e normaliza fontes públicas de Suzano;
2. descobre páginas e arquivos relacionados e preserva sua origem;
3. indexa o conteúdo em SQLite FTS5 para busca rápida;
4. oferece o índice por linha de comando, Python e API HTTP.

```text
fontes públicas + documentos + arquivos históricos
                       │
                       ▼
             coleta e descoberta
                       │
                       ▼
          normalização + proveniência
                       │
                       ▼
                SQLite + FTS5
                       │
           ┌───────────┼───────────┐
           ▼           ▼           ▼
          CLI        Python       API v1
```

## O que existe hoje

A base do projeto inclui:

- Câmara Municipal: vereadores, sessões, proposições, contratos, comissões, presenças e Diário Oficial do Legislativo;
- Prefeitura: licitações, secretarias, contas públicas, orçamento, Imprensa Oficial, leis, decretos e notícias;
- crawler respeitando `robots.txt`, sitemaps e limites de profundidade;
- descoberta e catalogação de PDF, DOCX, XLSX, CSV, XML, TXT e outros formatos públicos;
- extração pesquisável de conteúdo em formatos compatíveis;
- descoberta histórica por Common Crawl, Wayback Machine e Internet Archive;
- histórico de registros novos e alterados;
- snapshot público rolling com checksum SHA-256;
- atualização autônoma diária;
- API HTTP versionada e somente leitura.

Nenhuma biblioteca consegue garantir uma cópia literal de toda a Internet. A meta do projeto é aumentar continuamente, de forma rastreável, a cobertura pública relacionada a Suzano.

## Instalação

Requer Python 3.11 ou superior.

```bash
git clone https://github.com/MukaSanches/suzano-aberta.git
cd suzano-aberta
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

Linux ou macOS:

```bash
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

## Começar rápido

Baixe o índice público já preparado:

```bash
suzano sincronizar
```

Pesquise localmente:

```bash
suzano buscar "educação"
suzano buscar "transporte escolar"
suzano buscar "licitação saúde"
```

Ver o tamanho do acervo:

```bash
suzano panorama
```

## API própria

A versão 0.4 adiciona a **Suzano Aberta API v1**.

Inicie localmente:

```bash
suzano-api
```

O serviço abre por padrão em:

```text
http://127.0.0.1:8000
```

Documentação interativa:

```text
http://127.0.0.1:8000/docs
```

OpenAPI:

```text
http://127.0.0.1:8000/openapi.json
```

Pesquisa:

```text
GET /v1/search?q=educacao
GET /v1/search?q=saude&year=2026
GET /v1/search?q=contrato&kind=arquivo
```

Outras rotas principais:

```text
GET /health/live
GET /health/ready
GET /v1/records
GET /v1/records/{id}
GET /v1/stats
GET /v1/changes
GET /v1/snapshot
```

A API é deliberadamente **somente leitura**. Ela não oferece endpoints públicos para disparar crawlers, alterar o banco ou reindexar o acervo.

Consulte [docs/api.md](docs/api.md) para configuração, contrato das rotas, Docker, CORS e operação.

## Docker

```bash
docker compose up --build
```

Ou diretamente:

```bash
docker build -t suzano-aberta-api .
docker run --rm -p 8000:8000 -v suzano-data:/data suzano-aberta-api
```

A imagem executa como usuário sem privilégios, usa `/data` como volume persistente e pode sincronizar periodicamente o snapshot rolling.

## Busca rápida

A busca textual usa SQLite FTS5 com tokenização Unicode, remoção de diacríticos, pesquisa por prefixos e ranking BM25.

Isso permite resolver consultas como `educacao`, `licit` ou `transporte escolar` no índice local sem varrer os sites novamente.

Para cargas em massa, a API aponta para o snapshot completo em `/v1/snapshot`. Esse caminho é preferível a paginar dezenas de milhares de itens pela rede.

## Acervo máximo

Para uma expansão pesada do acervo:

```bash
suzano acervo-maximo
```

O modo combina web atual, documentos e índices públicos históricos. Os limites podem ser ajustados:

```bash
suzano acervo-maximo \
  --max-paginas 6000 \
  --profundidade 6 \
  --max-arquivos 1800 \
  --max-historicos 40000 \
  --colecoes-common-crawl 12
```

Bloqueios atuais de um portal não são contornados. Quando possível, cobertura histórica é ampliada usando catálogos públicos independentes de preservação.

## Atualização autônoma

O ciclo normal é:

```bash
suzano atualizar
```

Ele pode combinar coletores estruturados, descoberta web, arquivos e menções públicas recentes.

O workflow `Daily autonomous index` restaura o snapshot anterior, atualiza o acervo, valida o SQLite, compacta o banco, gera SHA-256 e publica novamente a tag rolling `data-latest`.

## Snapshot público

O snapshot é distribuído como:

```text
suzano-aberta.sqlite3.gz
data-latest.json
suzano-aberta.sqlite3.gz.sha256
```

A sincronização verifica checksum quando disponível, cabeçalho SQLite e `PRAGMA quick_check` antes de instalar o banco.

## Uso como biblioteca Python

```python
from suzano_aberta import Suzano

with Suzano(database="suzano.sqlite3") as suzano:
    resultados = suzano.search("mobilidade")

for item in resultados[:5]:
    print(item.title)
    print(item.source.url)
```

Atualização:

```python
from suzano_aberta import Suzano

with Suzano(database="suzano.sqlite3", auto_sync=False) as suzano:
    relatorio = suzano.refresh(max_pages=1000, max_depth=3)

print(relatorio.indexed_records)
```

## Rastreabilidade

Todo registro normalizado conserva um identificador estável, tipo, título, campos extraídos, URL da fonte e instante de coleta.

O histórico usa fingerprints determinísticos. Se um registro conhecido reaparece com conteúdo diferente, a alteração pode ser registrada. Isso permite responder tanto “de onde veio este dado?” quanto “ele mudou desde a coleta anterior?”.

## Segurança e confiabilidade

A arquitetura adota algumas regras deliberadamente conservadoras:

- fontes de primeira parte permanecem prioritárias;
- dados ausentes não são inventados;
- requisições possuem timeout, retry limitado e controle de frequência;
- `robots.txt` é respeitado pelo crawler atual;
- a API pública não possui rotas de escrita;
- parâmetros de busca e paginação possuem limites;
- registros individuais usam `ETag`;
- CORS é restritivo até ser configurado explicitamente;
- imagem Docker roda sem root;
- CI cobre Python 3.11, 3.12 e 3.13;
- mypy estrito, Ruff, testes, build do pacote, build do contêiner e CodeQL fazem parte da validação.

Um achado técnico não é automaticamente evidência de irregularidade administrativa ou política. A fonte responsável continua sendo a referência final.

## Documentação

- [API](docs/api.md)
- [Índice autônomo e busca rápida](docs/autonomia-e-busca.md)
- [Arquitetura](docs/arquitetura.md)
- [Fontes](docs/fontes.md)
- [Metodologia](docs/metodologia.md)
- [Modelo de dados](docs/modelo-de-dados.md)
- [Integridade de fontes](docs/integridade.md)
- [Limitações](docs/limitacoes.md)
- [Demonstração institucional](docs/demo-institucional.md)

## Desenvolvimento

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src/suzano_aberta
pytest
python -m build
docker build -t suzano-aberta-api .
```

## Licença

Código sob Apache 2.0. Dados e documentos acessados permanecem sujeitos às regras, licenças e condições de suas fontes originais.
