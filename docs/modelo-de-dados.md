# Modelo de dados

## `PublicRecord`

Todos os itens coletados são convertidos para um modelo comum.

| Campo | Significado |
| --- | --- |
| `id` | identificador interno estável |
| `kind` | natureza do registro |
| `title` | título legível |
| `summary` | resumo publicado ou extraído sem inferência |
| `date` | data ISO quando reconhecida |
| `year` | ano de referência quando aplicável |
| `attributes` | campos específicos da fonte |
| `source` | proveniência oficial |

Os tipos atualmente previstos incluem sessão, vereador, proposição, contrato, comissão, presença, diário, licitação, secretaria, documento fiscal, documento orçamentário, ato oficial e notícia.

## `SourceRef`

`SourceRef` mantém a proveniência mínima necessária para retornar ao material oficial:

- nome da fonte;
- URL;
- instante UTC da coleta;
- hash do conteúdo bruto quando disponível.

O hash é um recurso técnico de rastreabilidade e não substitui assinatura digital ou mecanismo jurídico de autenticidade.

## Fingerprint

O fingerprint de `PublicRecord` é SHA-256 de uma representação JSON canônica dos campos estáveis do registro. `collected_at` não participa do cálculo para evitar que uma coleta idêntica apareça como alteração.

## Banco

A tabela `records` guarda a versão mais recente observada de cada ID. A tabela `changes` registra eventos novos e alterados. `first_seen` e `last_seen` ajudam a reconstruir a história de observação local.

## Compatibilidade

Durante a série `0.x`, o formato ainda pode evoluir. Mudanças incompatíveis serão descritas no `CHANGELOG.md`.
