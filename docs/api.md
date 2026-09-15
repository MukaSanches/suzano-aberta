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

Parâmetros:

- `q`: termo ou expressão, obrigatório;
- `kind`: tipo de registro;
- `year`: ano do registro;
- `source`: parte do nome da fonte;
- `limit`: de 1 a 100;
- `offset`: paginação, limitada a 100000.

A resposta informa `total`, `limit`, `offset` e `next_offset`.

### `GET /v1/records`

Lista registros sem exigir uma busca textual. Aceita os filtros `kind`, `year`, `source`, `limit` e `offset`.

### `GET /v1/records/{id}`

Retorna um único registro completo. A resposta contém `ETag`; clientes podem reenviar esse valor em `If-None-Match` e receber HTTP 304 quando o conteúdo não mudou.

### `GET /v1/stats`

Retorna o tamanho lógico do acervo, estado do FTS5, tamanho do SQLite, versão do SQLite, contagem por tipo e principais fontes.

### `GET /v1/changes`

Expõe a trilha de registros novos ou alterados observados entre coletas.

### `GET /v1/snapshot`

Informa os endereços do banco compactado, checksum SHA-256 e metadados do snapshot rolling. Integrações que precisam consumir o conjunto inteiro devem preferir esse caminho em vez de paginar dezenas de milhares de itens pela API.

## Variáveis de ambiente

| Variável | Padrão | Função |
| --- | --- | --- |
| `SUZANO_API_DATABASE` | `suzano-aberta.sqlite3` | Caminho do índice SQLite |
| `SUZANO_API_AUTO_SYNC` | `true` | Permite instalar o snapshot quando o banco não existe |
| `SUZANO_API_SYNC_INTERVAL_SECONDS` | `0` | Intervalo de ressincronização; `0` desativa |
| `SUZANO_API_CORS_ORIGINS` | vazio | Origens CORS separadas por vírgula |
| `SUZANO_API_ALLOWED_HOSTS` | `*` | Hosts HTTP aceitos, separados por vírgula |

Em produção, prefira declarar explicitamente as origens CORS e os hosts aceitos.

## Docker

```bash
docker build -t suzano-aberta-api .
docker run --rm -p 8000:8000 -v suzano-data:/data suzano-aberta-api
```

A imagem usa usuário não privilegiado e mantém o SQLite em `/data`. No contêiner, a sincronização periódica é habilitada a cada hora para que um serviço de longa duração possa instalar snapshots mais recentes.

## Segurança operacional

A API não possui rotas de escrita. Atualização do acervo continua sendo responsabilidade dos workflows e comandos locais do projeto. Isso reduz a superfície de ataque e evita que uma requisição pública possa iniciar crawlers ou modificar o banco.

Para uma implantação pública, ainda é recomendado colocar a API atrás de um proxy ou plataforma que ofereça TLS, limitação de requisições, logs e proteção contra abuso. A própria API limita o tamanho das consultas e da paginação, mas não tenta substituir um gateway de borda.

## Compatibilidade

A primeira versão HTTP é `v1`. Mudanças incompatíveis de contrato devem entrar em uma nova versão de rota, mantendo `/v1` estável durante o período de migração.
