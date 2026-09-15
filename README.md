<p align="center">
  <img src="brand/logo-horizontal.svg" width="520" alt="Suzano Aberta — informação pública, rastreável e aberta">
</p>

<p align="center">
  <strong>Infraestrutura aberta para descobrir, preservar e pesquisar informações públicas sobre Suzano, SP.</strong>
</p>

<p align="center">
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/MukaSanches/suzano-aberta/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="Licença Apache 2.0" src="https://img.shields.io/badge/licen%C3%A7a-Apache--2.0-102A43"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-0B6E4F">
</p>

> **Projeto cívico independente.** O Suzano Aberta não é um portal oficial da Prefeitura Municipal de Suzano nem da Câmara Municipal de Suzano. Em caso de divergência, prevalece a publicação da fonte responsável.

## O que é, em linguagem simples

Informações públicas não costumam morar em um só lugar. Um contrato pode estar em uma página; um edital em PDF; uma lei em outro sistema; uma publicação antiga pode ter mudado de endereço.

O **Suzano Aberta** constrói uma camada de pesquisa sobre esse material. Ele coleta e organiza registros públicos, preserva a origem, indexa conteúdo pesquisável e distribui o mesmo acervo por diferentes caminhos:

```text
fontes públicas
      ↓
coleta + documentos + histórico
      ↓
SQLite + FTS5 + proveniência
      ↓
validação + checksum + snapshot
      ↓
┌─────────┬─────────┬────────┬────────┐
│ portal  │ API v1  │ Python │  CLI   │
└─────────┴─────────┴────────┴────────┘
```

O objetivo não é dizer ao cidadão no que acreditar. É permitir que ele **encontre e confira a fonte**.

## Portal público

O repositório inclui um portal estático preparado para GitHub Pages em `web/`. A interface foi desenhada com princípios de serviços públicos digitais: linguagem direta, acessibilidade, navegação previsível, foco em tarefas e transparência sobre a origem dos dados.

A pesquisa segue uma estratégia de resiliência:

1. se uma URL da API estiver configurada, o portal consulta a **API v1 + FTS5**;
2. se a API estiver indisponível, ele recua para um **índice estático derivado do snapshot**;
3. o portal continua mostrando a última versão publicada do acervo mesmo que a coleta do dia falhe.

O dataset web é gerado automaticamente a partir do snapshot SQLite validado. Não há contador fictício nem conteúdo de demonstração misturado ao acervo real.

## Busca e acervo

A pesquisa principal usa SQLite FTS5 com tokenização Unicode, remoção de diacríticos, prefixos e ranking BM25. O banco preserva registros atuais, documentos e referências históricas encontradas em fontes públicas.

O motor de coleta trabalha, entre outros, com:

- Câmara, sessões, proposições, contratos, comissões e presença parlamentar;
- licitações, secretarias, contas públicas e orçamento;
- Imprensa Oficial, leis, decretos e notícias institucionais;
- PDF, DOCX, XLSX, CSV, XML, TXT e formatos relacionados;
- descoberta web por páginas, links, `robots.txt` e sitemaps;
- referências históricas em Common Crawl, Wayback Machine e Internet Archive.

Bloqueios de portais atuais não são contornados. Quando uma fonte não permite determinada automação, a cobertura pode ser ampliada por índices públicos independentes de preservação.

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

## API própria

A API é uma camada HTTP **somente leitura** sobre o índice validado. Coleta e mutação não ficam expostas à internet.

```bash
suzano-api
```

Por padrão:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

Principais rotas:

```text
GET /v1/search?q=educacao
GET /v1/records
GET /v1/records/{id}
GET /v1/stats
GET /v1/changes
GET /v1/snapshot
GET /health/live
GET /health/ready
```

A API inclui paginação limitada, filtros, ETag, cache HTTP, GZip, CORS configurável, Trusted Hosts, request ID e health checks.

## Grandes volumes: use o snapshot

A API não deve ser usada para baixar o acervo inteiro página por página. Para jornalismo de dados, pesquisa acadêmica ou processamento em massa, use a release rolling `data-latest`:

```text
suzano-aberta.sqlite3.gz
suzano-aberta.sqlite3.gz.sha256
data-latest.json
```

A sincronização verifica SHA-256, cabeçalho SQLite e `PRAGMA quick_check` antes da instalação.

## Atualização autônoma

Ciclo normal:

```bash
suzano atualizar
```

Expansão pesada do acervo:

```bash
suzano acervo-maximo
```

A automação preserva o snapshot anterior, executa coleta, reindexa, valida o banco e só então publica a nova geração.

## Uso como biblioteca Python

```python
from suzano_aberta import Suzano

with Suzano(database="suzano.sqlite3") as suzano:
    resultados = suzano.search("mobilidade")

for item in resultados[:5]:
    print(item.title)
    print(item.source.url)
```

## Operação por Docker

```bash
docker compose up --build
```

A imagem da API roda sem privilégios de root e usa volume persistente para o banco.

## Confiabilidade e segurança

- nenhum dado ausente é inventado;
- cada registro mantém a fonte pública de origem;
- fingerprints determinísticos registram alterações de conteúdo;
- crawler respeita `robots.txt` e limita hosts autorizados;
- API abre o SQLite em modo read-only;
- publicação do snapshot exige integridade do SQLite e checksum;
- CI roda em Python 3.11, 3.12 e 3.13;
- mypy estrito, Ruff, testes, build do pacote e CodeQL fazem parte da esteira;
- o portal não usa anúncios nem scripts de rastreamento de terceiros.

## Acessibilidade

O portal tem como meta WCAG 2.2 AA e inclui navegação por teclado, foco visível, link de salto, semântica HTML, contraste alto, layout responsivo, suporte a zoom e respeito a `prefers-reduced-motion`.

Acessibilidade é tratada como trabalho contínuo, não como consequência automática de um framework.

## Estrutura

```text
suzano-aberta/
├── src/suzano_aberta/     biblioteca, coleta, busca e API
├── web/                    portal estático / GitHub Pages
├── brand/                  identidade visual canônica
├── scripts/                build e validação de dados do portal
├── tests/                  testes determinísticos
├── tests_live/             verificações separadas contra fontes reais
├── docs/                   arquitetura, metodologia e políticas
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

## Documentação

- [Arquitetura](docs/arquitetura.md)
- [Autonomia e busca](docs/autonomia-e-busca.md)
- [API pública](docs/api.md)
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
