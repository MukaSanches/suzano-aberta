# Interfaces Python oficiais

A partir da biblioteca `suzano-aberta` 0.6, o projeto oferece duas interfaces tipadas de consulta:

- `SuzanoClient` para consumir a Suzano Aberta API por HTTP;
- `SuzanoIndex` para consultar diretamente um snapshot SQLite local, sem subir servidor.

As duas usam os modelos do próprio projeto e compartilham a mesma semântica de busca, filtros e ordenação sempre que possível.

## Via HTTP: SuzanoClient

Use esta opção quando a API já está publicada ou rodando localmente.

```python
from suzano_aberta import SuzanoClient

with SuzanoClient("http://127.0.0.1:8000") as client:
    resultado = client.search("educação", year=2026)

for registro in resultado.items:
    print(registro.title, registro.source.url)
```

O endereço padrão é `http://127.0.0.1:8000`, portanto o exemplo mais curto funciona quando a API está rodando localmente:

```python
from suzano_aberta import SuzanoClient

with SuzanoClient() as client:
    print(client.stats())
```

### Métodos HTTP disponíveis

O cliente cobre as rotas públicas de leitura:

- `service()` — descrição geral do serviço;
- `liveness()` — estado do processo HTTP;
- `readiness()` — disponibilidade real do índice;
- `capabilities()` — recursos e limites publicados pela API;
- `stats()` — estatísticas do acervo;
- `sources()` — fontes presentes no índice;
- `snapshot()` — URLs do snapshot completo e checksum;
- `record(id)` — leitura de um registro pelo identificador;
- `search(...)` — busca textual com filtros;
- `records(...)` — listagem estruturada;
- `documents(...)` — documentos e arquivos públicos;
- `legislation(...)` — leis, decretos e proposições;
- `procurements(...)` — licitações, contratos e atas;
- `changes(...)` — histórico de registros novos ou alterados.

As respostas são convertidas em modelos Pydantic do próprio projeto. Registros são instâncias de `PublicRecord`, portanto não é necessário trabalhar com dicionários sem tipo.

## Sem servidor: SuzanoIndex

Se o seu programa já possui `suzano-aberta.sqlite3`, consulte o índice diretamente:

```python
from suzano_aberta import SuzanoIndex

with SuzanoIndex("suzano-aberta.sqlite3") as index:
    resultado = index.search("transporte escolar", year=2026, limit=25)

for registro in resultado.items:
    print(registro.id, registro.title)
```

O arquivo é aberto pela mesma camada SQLite somente leitura utilizada pela API. Isso evita duplicar regras de filtros e ordenação no SDK.

`SuzanoIndex` oferece `record()`, `records()`, `search()`, `documents()`, `legislation()`, `procurements()`, `changes()`, `stats()` e `iter_records()`.

Exemplo de análise local sem servidor HTTP:

```python
from suzano_aberta import SuzanoIndex

with SuzanoIndex("suzano-aberta.sqlite3") as index:
    contratos = index.procurements(
        "transporte",
        year=2026,
        date_from="2026-01-01",
        date_to="2026-12-31",
        sort="date_desc",
    )
    print(contratos.total)
```

## Paginação automática

Para percorrer resultados HTTP sem escrever o laço de `offset` manualmente, use `iter_records()` ou `iter_search()`:

```python
from suzano_aberta import SuzanoClient

with SuzanoClient("http://127.0.0.1:8000") as client:
    for registro in client.iter_records(year=2026, page_size=100, max_items=500):
        print(registro.id)
```

No modo local, `SuzanoIndex.iter_records()` oferece a mesma ideia:

```python
from suzano_aberta import SuzanoIndex

with SuzanoIndex("suzano-aberta.sqlite3") as index:
    for registro in index.iter_records(year=2026, page_size=100, max_items=500):
        print(registro.id)
```

Para cargas realmente grandes, prefira trabalhar diretamente com o snapshot em vez de transportar todo o acervo pela API HTTP.

## Filtros

Os métodos de busca e listagem aceitam os mesmos conceitos principais:

```python
resultado = client.search(
    "transporte escolar",
    kind="proposicao",
    year=2026,
    source="Câmara",
    date_from="2026-01-01",
    date_to="2026-12-31",
    date_mode="effective",
    sort="date_desc",
    limit=50,
)
```

Datas também podem ser objetos `datetime.date`.

## Tratamento de erros HTTP

Erros HTTP compatíveis com Problem Details são convertidos em `SuzanoApiError`:

```python
from suzano_aberta import SuzanoApiError, SuzanoClient

with SuzanoClient() as client:
    try:
        client.record("registro-inexistente")
    except SuzanoApiError as exc:
        print(exc.status_code)
        print(exc.request_id)
        print(exc)
```

Quando a API retorna `application/problem+json`, o objeto completo fica disponível em `exc.problem`.

A exceção também representa falhas de rede. Nesse caso, `status_code` pode ser `None`, porque nenhuma resposta HTTP chegou a ser recebida.

## Readiness degradado

`readiness()` é uma exceção intencional à regra de lançar erro em HTTP 503. O estado degradado é um resultado operacional legítimo e pode ser consultado diretamente:

```python
estado = client.readiness()
if not estado.ready:
    print("Índice ainda não está pronto")
```

## Segurança e testes

As duas interfaces são somente leitura. Nenhuma delas possui métodos para iniciar crawlers, reindexar, apagar ou alterar registros.

O cliente HTTP segue redirects e usa timeout configurável:

```python
client = SuzanoClient("https://api.exemplo", timeout=10.0)
```

Para testes determinísticos, o construtor também aceita um `httpx.BaseTransport`, permitindo usar `httpx.MockTransport` sem chamadas reais de rede.
