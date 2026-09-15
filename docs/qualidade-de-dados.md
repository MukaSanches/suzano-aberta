# Qualidade de dados

`quality_report()` produz métricas técnicas reproduzíveis sobre uma lista de `PublicRecord`. O relatório descreve propriedades do conjunto analisado; não avalia governo, órgão, agente público, política pública ou legalidade.

## Métricas

| Campo | Definição |
| --- | --- |
| `records` | quantidade de registros recebidos |
| `unique_ids` | quantidade de IDs distintos |
| `duplicate_ids` | ocorrências excedentes de IDs repetidos |
| `with_source_url` | registros com URL de origem não vazia |
| `with_title` | registros com título não vazio |
| `source_count` | nomes de fonte distintos |
| `completeness` | `(with_source_url + with_title) / (2 * records)` |
| `uniqueness` | `unique_ids / records` |
| `generated_at` | instante UTC de geração |

Para conjunto vazio, `completeness` e `uniqueness` são 1.0: não existem violações observadas nessas duas propriedades. Consumidores que precisem exigir volume mínimo devem aplicar esse critério separadamente.

## Exemplo

```python
from suzano_aberta import quality_report

relatorio = quality_report(registros)
print(relatorio.model_dump())
```

## Como interpretar

`completeness=1.0` significa apenas que todos os registros analisados possuem os dois campos atualmente medidos: título e URL de origem. Não significa que todos os campos possíveis da fonte foram coletados.

`uniqueness=1.0` significa que não há IDs repetidos na lista analisada. Não significa que duas fontes diferentes nunca descrevem o mesmo evento real.

## Regras para novas métricas

Uma métrica nova deve possuir definição pública, fórmula ou regra reproduzível, teste determinístico e nome que não sugira uma conclusão maior que aquilo que efetivamente mede. Métricas de cobertura dependentes de universo conhecido devem declarar explicitamente qual é esse universo.
