# Entidades e relações

A biblioteca 0.7 introduz uma camada determinística para reconhecer entidades mencionadas em `PublicRecord` e agrupá-las sem apagar a evidência que originou cada associação.

## Por que existe

Um registro isolado responde "o que esta fonte publicou?". Uma entidade permite responder "quais registros do conjunto apontam para o mesmo identificador verificável?". Essa separação é necessária para construir navegação relacional sem transformar coincidências de texto em fatos.

## Modelo

`EntityMention` é uma ocorrência de uma entidade em um registro. Ela conserva `record_id`, fonte, URL e confiança da regra que produziu a menção.

`Entity` é a agregação das menções com o mesmo ID canônico. Ela contém categoria, nome apresentado, identificador quando disponível, aliases observados, fontes e número de registros distintos.

`EntityGraph` contém as entidades agregadas e todas as menções que sustentam o resultado.

## IDs canônicos

`canonical_entity_id(kind, name, identifier)` gera um ID determinístico por SHA-256 truncado. Quando existe identificador forte, ele tem precedência sobre o nome normalizado.

Consequência: duas grafias de um nome podem convergir quando compartilham o mesmo identificador forte; nomes apenas parecidos não são automaticamente fundidos.

## Regras implementadas na 0.7

### Órgão de origem

Todo registro com `source.name` válido produz uma menção de categoria `orgao`. A confiança é 1 porque a associação representa a origem declarada do próprio registro, não uma inferência sobre autoria material de todos os fatos contidos nele.

### Fornecedor identificado por CNPJ

O extrator percorre campos textuais do registro e reconhece CNPJ explicitamente publicado. Pontuação é removida e o identificador canônico usa os 14 dígitos.

A presença de um CNPJ significa somente que o identificador aparece naquele registro. Aplicações consumidoras não devem reinterpretar a menção, sozinha, como prova de pagamento, propriedade, irregularidade, vínculo societário ou responsabilidade.

## O que deliberadamente não é feito

A 0.7 não funde pessoas por nome, não cria parentesco, não deduz sociedade empresarial, não atribui intenção, não classifica regularidade de contratos e não cria conexões políticas. Essas relações exigiriam fontes e regras específicas.

## Exemplo

```python
from suzano_aberta import build_entity_graph

grafo = build_entity_graph(registros)
for entidade in grafo.entities:
    print(entidade.id, entidade.kind, entidade.identifier)
```

## Evolução compatível

A camada foi desenhada para permitir novas regras explícitas de resolução, persistência no snapshot e endpoints relacionais. Novas regras devem ser testáveis, documentadas e preservar a evidência que sustenta cada menção.
