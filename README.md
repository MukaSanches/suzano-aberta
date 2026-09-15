<p align="center">
  <img src="brand/logo-horizontal.svg" width="520" alt="Suzano Aberta — informação pública, rastreável e aberta">
</p>

<p align="center">
  <strong>Infraestrutura aberta para descobrir, preservar, pesquisar e relacionar informações públicas sobre Suzano, SP.</strong>
</p>

<p align="center">
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="Licença Apache 2.0" src="https://img.shields.io/badge/licen%C3%A7a-Apache--2.0-102A43"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-0B6E4F">
  <img alt="Biblioteca 0.7.0" src="https://img.shields.io/badge/library-0.7.0-102A43">
  <img alt="API 1.2" src="https://img.shields.io/badge/API-1.2-0B6E4F">
</p>

> **Projeto cívico independente.** O Suzano Aberta não é um portal oficial da Prefeitura Municipal de Suzano nem da Câmara Municipal de Suzano. Em caso de divergência, prevalece a publicação da fonte responsável.

## O projeto em uma frase

O Suzano Aberta transforma publicações públicas dispersas em um acervo local, pesquisável, verificável e reutilizável, preservando o caminho de volta à fonte.

```text
fontes municipais + APIs nacionais + arquivos históricos
                           ↓
                coleta + normalização
                           ↓
        PublicRecord + SourceRef + histórico
                           ↓
             SQLite + FTS5 + snapshot
                           ↓
       entidades + proveniência + qualidade
                           ↓
┌──────────┬──────────┬──────────┬──────────┐
│  portal  │ API 1.2  │  Python  │   CLI    │
└──────────┴──────────┴──────────┴──────────┘
```

O projeto organiza evidências; não produz juízo político ou administrativo.

## O que existe hoje

- coleta estruturada da Câmara e da Prefeitura;
- integração com PNCP e Compras.gov.br;
- descoberta de páginas, documentos e referências históricas;
- extração pesquisável de formatos públicos suportados;
- SQLite local-first com histórico de mudanças;
- FTS5 com busca Unicode, prefixos e ranking;
- snapshot rolling validado por SHA-256 e `PRAGMA quick_check`;
- API HTTP somente leitura, OpenAPI e Problem Details;
- SDK HTTP `SuzanoClient` e consulta local `SuzanoIndex`;
- portal público com fallback estático;
- proveniência por registro e catálogo de fontes;
- motor de entidades 0.7 com IDs canônicos determinísticos;
- reconhecimento conservador de órgãos e fornecedores identificados por CNPJ;
- relatório mensurável de qualidade do conjunto de registros;
- CI em Python 3.11, 3.12 e 3.13, build de pacote, container e CodeQL.

## Começar

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

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Sincronize o snapshot e pesquise:

```bash
suzano sincronizar
suzano buscar "educação"
suzano buscar "transporte escolar"
```

## Biblioteca Python 0.7

### Busca local

```python
from suzano_aberta import SuzanoIndex

with SuzanoIndex("suzano-aberta.sqlite3") as index:
    pagina = index.search("educação", year=2026, limit=25)
    for registro in pagina.items:
        print(registro.title, registro.source.url)
```

### Grafo de entidades

O motor 0.7 trabalha diretamente com `PublicRecord`. A resolução inicial é propositalmente conservadora: usa a origem do registro como órgão e CNPJ explícito como identificador forte de fornecedor. Não cria vínculos por semelhança vaga de nomes.

```python
from suzano_aberta import SuzanoIndex, build_entity_graph

with SuzanoIndex("suzano-aberta.sqlite3") as index:
    pagina = index.procurements("", limit=100)

grafo = build_entity_graph(pagina.items)
for entidade in grafo.entities:
    print(entidade.id, entidade.kind, entidade.name, entidade.records)
```

IDs canônicos são determinísticos: a mesma categoria e o mesmo identificador normalizado produzem o mesmo ID. Isso prepara a persistência futura de relações sem depender de IDs aleatórios.

### Qualidade de dados

```python
from suzano_aberta import SuzanoIndex, quality_report

with SuzanoIndex("suzano-aberta.sqlite3") as index:
    pagina = index.records(limit=100)

relatorio = quality_report(pagina.items)
print(relatorio.completeness)
print(relatorio.uniqueness)
print(relatorio.duplicate_ids)
```

`QualityReport` mede propriedades técnicas do conjunto entregue: presença de título e URL de origem, unicidade de IDs, duplicações e quantidade de fontes. Ele não atribui nota a órgão, agente público ou política pública.

## API HTTP 1.2

```bash
suzano-api
```

Documentação local:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/openapi.json
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

A API é deliberadamente somente leitura. Coleta, reindexação e mutações não são expostas por HTTP. A versão do pacote, a versão do contrato HTTP e a versão do dataset são conceitos independentes.

## Fontes e cobertura

O catálogo inclui fontes da Câmara Municipal de Suzano, Prefeitura Municipal de Suzano, PNCP e Compras.gov.br. Também existem mecanismos de descoberta para documentos e referências históricas.

Cada fonte continua independente. Relações só devem ser apresentadas quando houver evidência verificável no próprio acervo, como CNPJ, número de processo, identificador PNCP ou outra chave pública suficientemente forte.

Bloqueios de automação não são contornados. Uma fonte indisponível pode reduzir a cobertura da coleta atual sem autorizar o projeto a inventar ou preencher lacunas.

## Snapshot e grandes volumes

Para processamento em massa, use o snapshot em vez de paginar a API inteira:

```text
suzano-aberta.sqlite3.gz
suzano-aberta.sqlite3.gz.sha256
data-latest.json
```

A sincronização valida checksum, cabeçalho SQLite e integridade do banco antes da instalação.

## Docker

```bash
docker compose up --build
```

A imagem da API roda sem root. A camada de serviço abre o SQLite como somente leitura com `mode=ro`, `immutable=1`, `query_only=ON` e `trusted_schema=OFF`.

## Confiabilidade

O projeto segue quatro regras operacionais centrais:

1. **Fonte antes da interpretação.** Um registro deve conservar o caminho para sua origem.
2. **Falhar sem destruir.** Falha de coleta não deve substituir automaticamente o último snapshot válido.
3. **Relações precisam de evidência.** O motor de entidades não deve transformar coincidência textual em vínculo factual.
4. **Qualidade precisa ser mensurável.** Métricas técnicas devem ter fórmula reproduzível e não ser confundidas com avaliação política.

Além disso, entradas externas são tratadas como não confiáveis, o crawler possui limites e política de redirects, a publicação valida o SQLite, e CI/CodeQL verificam regressões de engenharia.

## Estrutura

```text
suzano-aberta/
├── src/suzano_aberta/
│   ├── api/               API HTTP somente leitura
│   ├── sources/           adaptadores de fontes
│   ├── entities.py        resolução e agregação de entidades
│   ├── quality.py         métricas técnicas de qualidade
│   ├── provenance.py      proveniência e catálogo semântico
│   ├── index.py           consulta local tipada
│   └── client.py          cliente HTTP tipado
├── web/                   portal estático
├── docs/                  documentação técnica
├── tests/                 testes determinísticos
├── tests_live/            verificações contra fontes reais
├── scripts/               build e validação
└── .github/workflows/     CI, segurança, coleta e publicação
```

## Desenvolvimento

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src/suzano_aberta
pytest
python scripts/check_web.py
python -m build
```

## Documentação

- [Arquitetura](docs/arquitetura.md)
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
- [Identidade visual](brand/README.md)

## Licença

Código sob [Apache License 2.0](LICENSE). Dados e documentos acessados permanecem sujeitos às regras, licenças e condições das fontes originais.
