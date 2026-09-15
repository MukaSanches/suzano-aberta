<p align="center">
  <img src="brand/logo-horizontal.svg" width="520" alt="Suzano Aberta — informação pública, rastreável e aberta">
</p>

<p align="center">
  <strong>Infraestrutura aberta para descobrir, preservar, relacionar e pesquisar informações públicas sobre Suzano, SP.</strong>
</p>

<p align="center">
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="Licença Apache 2.0" src="https://img.shields.io/badge/licen%C3%A7a-Apache--2.0-102A43"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-0B6E4F">
  <img alt="Biblioteca 0.6.0" src="https://img.shields.io/badge/library-0.6.0-102A43">
  <img alt="API 1.2" src="https://img.shields.io/badge/API-1.2-0B6E4F">
</p>

> **Projeto cívico independente.** O Suzano Aberta não é um portal oficial da Prefeitura Municipal de Suzano nem da Câmara Municipal de Suzano. Em caso de divergência, prevalece a publicação da fonte responsável.

## O que é, em linguagem simples

Informações públicas não costumam morar em um só lugar. Um contrato pode estar em uma página; um edital em PDF; uma lei em outro sistema; uma compra pública pode aparecer tanto no município quanto em bases nacionais; uma publicação antiga pode ter mudado de endereço.

O **Suzano Aberta** constrói uma camada de pesquisa e rastreabilidade sobre esse material. Ele coleta e organiza registros públicos, preserva a origem, indexa conteúdo pesquisável, relaciona evidências compatíveis e distribui o mesmo acervo por diferentes caminhos:

```text
fontes municipais + APIs públicas + arquivos históricos
                         ↓
              coleta + normalização
                         ↓
        SQLite + FTS5 + proveniência
                         ↓
      validação + checksum + snapshot
                         ↓
┌─────────┬──────────┬─────────┬────────┐
│ portal  │ API 1.2  │ Python  │  CLI   │
└─────────┴──────────┴─────────┴────────┘
```

O objetivo não é dizer ao cidadão no que acreditar. É permitir que ele **encontre, relacione e confira a fonte**.

## Portal público

O portal oficial do projeto é publicado pelo GitHub Pages:

**https://mukasanches.github.io/suzano-aberta/**

A interface foi desenhada com princípios de serviços públicos digitais: linguagem direta, acessibilidade, navegação previsível, foco em tarefas e transparência sobre a origem dos dados.

A pesquisa segue uma estratégia de resiliência:

1. se uma URL da API estiver configurada, o portal consulta a API dinâmica;
2. se a API estiver indisponível, ele usa um índice estático derivado do snapshot;
3. uma coleta que falha não substitui automaticamente a última versão válida.

O dataset web é gerado automaticamente a partir do snapshot SQLite validado. Não há contador fictício nem conteúdo de demonstração misturado ao acervo real.

## Fontes e acervo

O motor de coleta trabalha, entre outros, com:

- Câmara Municipal: sessões, proposições, legislação consolidada, contratos, licitações, dispensas, comissões, presenças e Diário Oficial;
- Prefeitura: licitações, secretarias, contas públicas, orçamento, Imprensa Oficial, atos e notícias;
- **PNCP**: contratações, contratos e atas de registro de preços relacionadas ao município;
- **Compras.gov.br Dados Abertos**: fonte nacional complementar para contratações da Lei 14.133;
- PDF, DOCX, XLSX, CSV, XML, TXT e outros formatos públicos suportados;
- descoberta web por páginas, links, `robots.txt` e sitemaps;
- referências históricas em Common Crawl, Wayback Machine e Internet Archive.

As fontes permanecem independentes. Quando dois registros compartilham identificadores públicos verificáveis — por exemplo número de controle PNCP, processo, CNPJ ou norma citada — o projeto pode registrar a relação sem transformar isso em julgamento sobre regularidade.

Bloqueios de portais atuais não são contornados. Quando uma fonte não permite determinada automação, a cobertura pode ser ampliada por APIs públicas, arquivos históricos ou outras fontes oficiais acessíveis.

## Começar em 30 segundos

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

Baixe o índice já pronto e pesquise:

```bash
suzano sincronizar
suzano buscar "educação"
suzano buscar "transporte escolar"
suzano buscar "Santa Casa"
```

## API 1.2

A API é uma camada HTTP **somente leitura** sobre snapshots validados. Coleta, reindexação, execução de crawler e mutações não são expostas como operações públicas.

```bash
suzano-api
```

Por padrão:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/openapi.json
```

Principais rotas:

```text
GET /v1/search?q=educacao&sort=date_desc
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

A API mantém **versão do pacote, versão do contrato HTTP, versão do schema e versão do dataset separadas**. Erros são serializados como `application/problem+json`; respostas consultivas usam request ID, cache HTTP/ETag quando aplicável e headers de versão. Proveniência e catálogo possuem representações JSON-LD inspiradas em W3C PROV e DCAT.

A paginação da API informa `total`, `limit`, `offset`, `next_offset`, `previous_offset`, `returned` e `has_more`, permitindo construir clientes sem recriar a lógica de navegação.

### Grandes volumes: use o snapshot

A API não deve ser usada para baixar o acervo inteiro página por página. Para jornalismo de dados, pesquisa acadêmica ou processamento em massa, use a release rolling `data-latest`:

```text
suzano-aberta.sqlite3.gz
suzano-aberta.sqlite3.gz.sha256
data-latest.json
```

A sincronização verifica SHA-256, cabeçalho SQLite e `PRAGMA quick_check` antes da instalação.

## Uso como biblioteca Python

A biblioteca 0.6.0 separa claramente três responsabilidades.

### Coleta e atualização: `Suzano`

```python
from suzano_aberta import Suzano

with Suzano(database="suzano.sqlite3") as suzano:
    resultados = suzano.search("mobilidade")

for item in resultados[:5]:
    print(item.title, item.source.url)
```

### Consulta local tipada: `SuzanoIndex`

```python
from suzano_aberta import SuzanoIndex

with SuzanoIndex("suzano.sqlite3") as index:
    pagina = index.search("educação", year=2026, limit=25)
    print(pagina.total)
    for item in pagina.items:
        print(item.title)
```

`SuzanoIndex` reutiliza a camada SQLite somente leitura da API. Isso mantém filtros, ordenação, paginação e busca consistentes sem exigir um servidor HTTP.

### Consumo da API: `SuzanoClient`

```python
from suzano_aberta import SuzanoClient

with SuzanoClient("http://127.0.0.1:8000") as client:
    pagina = client.search("transporte escolar", year=2026)
    for item in pagina.items:
        print(item.id, item.source.url)
```

O cliente HTTP converte as respostas em modelos tipados, trata Problem Details como `SuzanoApiError` e possui iteradores de paginação automática.

A biblioteca 0.6.0 trata URLs e respostas de fontes externas como entrada não confiável: aplica timeout, limite de tamanho, redirects limitados e validados, retry apenas em falhas transitórias conhecidas e rejeita destinos literais locais/privados por padrão.

## Atualização autônoma

Ciclo normal:

```bash
suzano atualizar
```

Expansão pesada do acervo:

```bash
suzano acervo-maximo
```

A automação preserva o snapshot anterior, executa coleta, reindexa, valida o banco e só então publica a nova geração. A falha de uma fonte não apaga resultados válidos vindos das demais.

## Operação por Docker

```bash
docker compose up --build
```

A imagem da API roda sem privilégios de root e usa volume persistente para o banco. Na camada de serviço, o SQLite é aberto em `mode=ro`, `immutable=1`, `query_only=ON` e `trusted_schema=OFF`.

## Confiabilidade e segurança

- nenhum dado ausente é inventado;
- cada registro mantém a fonte pública de origem;
- fingerprints determinísticos registram alterações substantivas de conteúdo;
- metadados operacionais de proveniência não reescrevem artificialmente o histórico;
- crawler respeita `robots.txt` e possui limites de resposta, redirects e retry;
- URLs literais locais e IPs privados não são aceitos pelo cliente público por padrão;
- API pública é somente leitura e impõe limites de paginação;
- erros possuem formato previsível e legível por máquina;
- publicação do snapshot exige integridade do SQLite e checksum;
- CI roda em Python 3.11, 3.12 e 3.13;
- mypy estrito, Ruff, testes, build do pacote, container e CodeQL fazem parte da esteira;
- o portal não depende de analytics de terceiros para funcionar.

Esses controles usam referências públicas de engenharia como NIST, OWASP, RFC 9457, W3C PROV e DCAT. O projeto **não afirma certificação governamental, classificação de segurança ou equivalência a sistemas sigilosos**.

## Acessibilidade

O portal tem como meta WCAG 2.2 AA e inclui navegação por teclado, foco visível, link de salto, semântica HTML, contraste alto, layout responsivo, suporte a zoom e respeito a `prefers-reduced-motion`.

Acessibilidade é tratada como trabalho contínuo, não como consequência automática de um framework.

## Estrutura

```text
suzano-aberta/
├── src/suzano_aberta/     biblioteca, coleta, busca, proveniência e API
├── web/                    portal estático / GitHub Pages
├── brand/                  identidade visual canônica
├── scripts/                build e validação de dados do portal
├── tests/                  testes determinísticos
├── tests_live/             verificações separadas contra fontes reais
├── docs/                   arquitetura, contratos e políticas
└── .github/workflows/      CI, CodeQL, coleta e publicação
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

## Princípios do projeto

**Fonte antes da interpretação.** O registro deve poder ser conferido.

**Falhar sem destruir.** Uma coleta quebrada não deve substituir uma versão válida.

**Interface simples, engenharia profunda.** O cidadão não precisa conhecer SQLite, crawler ou FTS5 para pesquisar.

**Separação de responsabilidades.** O portal não controla o crawler; a API não escreve no acervo; a coleta não decide o que é politicamente verdadeiro.

**Entrada externa é não confiável até ser validada.** Uma API oficial também pode falhar, mudar contrato ou devolver conteúdo inesperado.

**Compatibilidade é parte do produto.** Adicionar metadados não deve fazer toda a história parecer alterada, e consumidores não devem precisar adivinhar quando o contrato mudou.

## Documentação

- [Arquitetura](docs/arquitetura.md)
- [Autonomia e busca](docs/autonomia-e-busca.md)
- [API pública](docs/api.md)
- [Interfaces Python](docs/python-client.md)
- [Contrato da API](docs/API-CONTRACT.md)
- [Governança da API](docs/api-governance.md)
- [Fronteiras de segurança](docs/SECURITY-BOUNDARIES.md)
- [Política de fontes upstream](docs/UPSTREAM-SOURCES.md)
- [Fontes](docs/fontes.md)
- [Metodologia](docs/metodologia.md)
- [Modelo de dados](docs/modelo-de-dados.md)
- [Integridade](docs/integridade.md)
- [Limitações](docs/limitacoes.md)
- [Portal web](docs/portal-web.md)
- [Identidade visual](brand/README.md)
- [Roteiro institucional](docs/demo-institucional.md)

## Licença

Código sob [Apache License 2.0](LICENSE). Dados e documentos acessados permanecem sujeitos às regras, licenças e condições das fontes originais.