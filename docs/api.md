# Suzano Aberta API

A API é a camada HTTP pública e somente leitura do Suzano Aberta. Ela existe para que sites, aplicativos, jornalistas, pesquisadores e outros serviços consultem o acervo sem precisar conhecer SQLite, executar coletores ou baixar documentos manualmente.

## Princípios

- somente leitura: a API não expõe rotas para coletar, alterar, reindexar ou apagar dados;
- versionamento explícito em `/v1`;
- busca local sobre o índice SQLite FTS5 já construído pelo projeto;
- todos os resultados preservam a fonte pública de origem;
- limites de paginação evitam consultas sem teto;
- OpenAPI é gerado automaticamente em `/openapi.json`;
- Swagger UI em `/docs` e ReDoc em `/redoc`;
- respostas individuais usam `ETag` para cache condicional;
- respostas de listas usam `Cache-Control` curto;
- erros seguem Problem Details (`application/problem+json`);
- o snapshot completo continua disponível para cargas em massa.

## Executar localmente

Instale o projeto e inicie a API:

```bash
python -m pip install -e .
suzano-api
```

Por padrão, o serviço escuta somente em `127.0.0.1:8000`. Para expor na rede:

```bash
suzano-api --host 0.0.0.0 --port 8000
```

Se o banco local ainda não existir, a API tenta instalar o snapshot público mais recente na inicialização. Para impedir qualquer sincronização automática:

```bash
suzano-api --sem-sync
```

## Rotas principais

### `GET /health/live`

Indica que o processo HTTP está vivo.

### `GET /health/ready`

Indica se existe um índice válido e pesquisável. Retorna HTTP 503 enquanto o banco não estiver disponível.

### `GET /v1/search`

Pesquisa o FTS5. Exemplo:

```text
GET /v1/search?q=educacao&year=2026&limit=30
```

Parâmetros principais:

- `q`: termo ou expressão, obrigatório;
- `kind`: tipo de registro;
- `year`: ano do registro;
- `source`: parte do nome da fonte;
- `date_from` e `date_to`: intervalo de datas no formato ISO;
- `date_mode`: `effective`, `record` ou `observed`;
- `sort`: `date_desc`, `date_asc` ou `relevance`;
- `limit`: de 1 a 100;
- `offset`: paginação, limitada a 100000.

A resposta de paginação informa:

- `total`: quantidade total de registros que atendem aos filtros;
- `limit`: tamanho solicitado da página;
- `offset`: posição inicial;
- `next_offset`: próxima posição ou `null` quando acabou;
- `previous_offset`: posição anterior ou `null` na primeira página;
- `returned`: quantidade lógica de registros da página;
- `has_more`: indica se existe próxima página.

Os campos novos são aditivos: consumidores que já usam `total`, `limit`, `offset` e `next_offset` continuam compatíveis.

### `GET /v1/records`

Lista registros sem exigir uma busca textual. Aceita filtros por tipo, ano, fonte e intervalo de datas, além de ordenação e paginação.

### `GET /v1/documents`

Consulta documentos e arquivos públicos indexados, incluindo leis, decretos, diários e documentos fiscais/orçamentários.

### `GET /v1/legislation`

Consulta leis, decretos e proposições, com os mesmos controles de data, ordenação e paginação.

### `GET /v1/procurements`

Consulta licitações, contratos e atas provenientes das fontes de contratação integradas ao projeto.

### `GET /v1/records/{id}`

Retorna um único registro completo. A resposta contém `ETag`; clientes podem reenviar esse valor em `If-None-Match` e receber HTTP 304 quando o conteúdo não mudou.

### `GET /v1/records/{id}/provenance`

Expõe a proveniência do registro e metadados de armazenamento em JSON-LD.

### `GET /v1/sources`

Lista as fontes presentes no snapshot, com contagem e intervalo observado.

### `GET /v1/catalog`

Expõe o catálogo interoperável em JSON-LD/DCAT.

### `GET /v1/capabilities`

Publica formatos, limites, ordenações, modos de data, tipos de registro e capacidades do serviço para clientes que desejem se adaptar ao contrato automaticamente.

### `GET /v1/stats`

Retorna o tamanho lógico do acervo, estado do FTS5, tamanho do SQLite, versão do SQLite, contagem por tipo e principais fontes.

### `GET /v1/changes`

Expõe a trilha de registros novos ou alterados observados entre coletas.

### `GET /v1/snapshot`

Informa os endereços do banco compactado, checksum SHA-256 e metadados do snapshot rolling. Integrações que precisam consumir o conjunto inteiro devem preferir esse caminho em vez de paginar dezenas de milhares de itens pela API.

## Cliente Python oficial

A biblioteca 0.6 inclui `SuzanoClient`, que transforma as respostas HTTP em modelos tipados e faz o tratamento de Problem Details:

```python
from suzano_aberta import SuzanoClient

with SuzanoClient("http://127.0.0.1:8000") as client:
    pagina = client.search("educação", year=2026)
    for registro in pagina.items:
        print(registro.title)
```

Para paginação automática:

```python
with SuzanoClient() as client:
    for registro in client.iter_search("transporte", page_size=100, max_items=500):
        print(registro.id)
```

Quando o consumidor já possui o snapshot SQLite, `SuzanoIndex` fornece uma interface local tipada sem depender de HTTP. Veja [Interfaces Python](python-client.md).

## Variáveis de ambiente

| Variável | Padrão | Função |
| --- | --- | --- |
| `SUZANO_API_DATABASE` | `suzano-aberta.sqlite3` | Caminho do índice SQLite |
| `SUZANO_API_AUTO_SYNC` | `true` | Permite instalar o snapshot quando o banco não existe |
| `SUZANO_API_SYNC_INTERVAL_SECONDS` | `0` | Intervalo de ressincronização; `0` desativa |
| `SUZANO_API_CORS_ORIGINS` | vazio | Origens CORS separadas por vírgula |
| `SUZANO_API_ALLOWED_HOSTS` | `*` | Hosts HTTP aceitos, separados por vírgula |
| `SUZANO_API_METRICS` | `true` | Habilita a rota Prometheus `/metrics` |

Em produção, prefira declarar explicitamente as origens CORS e os hosts aceitos.

## Docker

```bash
docker build -t suzano-aberta-api .
docker run --rm -p 8000:8000 -v suzano-data:/data suzano-aberta-api
```

A imagem usa usuário não privilegiado e mantém o SQLite em `/data`. No contêiner, a sincronização periódica pode manter um serviço de longa duração alinhado ao snapshot publicado.

## Segurança operacional

A API não possui rotas de escrita. Atualização do acervo continua sendo responsabilidade dos workflows e comandos locais do projeto. Isso reduz a superfície de ataque e evita que uma requisição pública possa iniciar crawlers ou modificar o banco.

Para uma implantação pública, ainda é recomendado colocar a API atrás de um proxy ou plataforma que ofereça TLS, limitação de requisições, logs e proteção contra abuso. A própria API limita o tamanho das consultas e da paginação, mas não tenta substituir um gateway de borda.

## Compatibilidade

A primeira versão HTTP é `v1`. Mudanças incompatíveis de contrato devem entrar em uma nova versão de rota, mantendo `/v1` estável durante o período de migração. Campos aditivos podem evoluir dentro da mesma versão quando não alteram o significado dos campos existentes.
