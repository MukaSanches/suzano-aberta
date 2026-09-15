# Modelo de dados

## `PublicRecord`

`PublicRecord` continua sendo a unidade normalizada do acervo. Campos comuns ficam tipados e dados próprios da publicação permanecem em `attributes`.

| Campo | Significado |
| --- | --- |
| `id` | identificador interno estável |
| `kind` | natureza do registro |
| `title` | título legível |
| `summary` | resumo publicado ou extraído sem inferência |
| `date` | data ISO quando reconhecida |
| `year` | ano de referência quando aplicável |
| `attributes` | campos específicos da fonte |
| `source` | referência à origem pública |

## `SourceRef`

Preserva nome da fonte, URL, instante de coleta e hash bruto quando disponível. O hash é um mecanismo técnico de rastreabilidade; não substitui assinatura digital nem autenticidade jurídica.

## Fingerprint e histórico

O fingerprint de `PublicRecord` é SHA-256 de uma representação canônica dos campos estáveis. Metadados operacionais que mudam a cada coleta não devem fazer conteúdo idêntico aparecer como alteração substantiva.

A tabela `records` mantém a versão mais recente observada de cada ID. `changes` registra eventos de observação. `first_seen` e `last_seen` descrevem a história local do índice.

## Camada de entidades — 0.7

A entidade é uma camada derivada e não substitui `PublicRecord`.

### `EntityMention`

Representa a evidência de que uma regra determinística encontrou uma entidade em um registro. Conserva ID da entidade, categoria, nome, identificador opcional, ID do registro, fonte, URL e confiança da regra.

### `Entity`

Agrupa menções que compartilham o mesmo ID canônico. Expõe aliases observados, fontes e quantidade de registros distintos.

### `EntityGraph`

Entrega as entidades agregadas junto das menções que sustentam a agregação. Manter as menções é importante para que o consumidor possa auditar de onde veio cada relação.

## IDs de entidade

O ID canônico usa categoria mais identificador forte quando disponível; na ausência dele, usa nome normalizado. O resultado é determinístico e não depende de banco central de IDs.

Na 0.7, CNPJ explícito é tratado como identificador forte para fornecedores. O nome da fonte é usado para representar o órgão de origem do registro.

## Qualidade

`QualityReport` é um relatório derivado e não altera registros. Ele mede contagem, unicidade de IDs, duplicações, presença de título, presença de URL de origem e diversidade de fontes. As fórmulas estão documentadas em `docs/qualidade-de-dados.md`.

## Compatibilidade

Durante a série `0.x`, o formato pode evoluir. Mudanças incompatíveis devem ser registradas no `CHANGELOG.md`. Novas regras de entidade devem preservar evidência, ser determinísticas quando possível e possuir testes de regressão.
