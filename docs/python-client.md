# Cliente Python oficial

A partir da biblioteca `suzano-aberta` 0.6, o projeto inclui um cliente Python tipado para a Suzano Aberta API. Ele é útil quando você quer consumir a API HTTP sem montar URLs, parâmetros, paginação e tratamento de erros manualmente.

## Começo rápido

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

## Métodos disponíveis

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

## Paginação automática

Para percorrer resultados sem escrever o laço de `offset` manualmente, use `iter_records()` ou `iter_search()`:

```python
from suzano_aberta import SuzanoClient

with SuzanoClient("http://127.0.0.1:8000") as client:
    for registro in client.iter_records(year=2026, page_size=100, max_items=500):
        print(registro.id)
```

O iterador continua respeitando o limite máximo publicado pela API. Para cargas realmente grandes, continue preferindo o snapshot SQLite informado por `client.snapshot()`.

## Filtros

Os métodos de busca e listagem aceitam os mesmos conceitos da API:

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

## Tratamento de erros

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

## Cliente HTTP e segurança

O SDK é somente leitura, assim como a API pública. Ele não possui métodos para iniciar crawlers, reindexar, apagar ou alterar registros.

O cliente segue redirects e usa timeout configurável. Para alterar o timeout:

```python
client = SuzanoClient("https://api.exemplo", timeout=10.0)
```

Para testes determinísticos, o construtor também aceita um `httpx.BaseTransport`, permitindo usar `httpx.MockTransport` sem chamadas reais de rede.
