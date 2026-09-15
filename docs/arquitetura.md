# Arquitetura

Suzano Aberta é uma infraestrutura local-first de dados públicos. Coleta, normalização, persistência, resolução de entidades, serviço HTTP e apresentação são camadas separadas para que mudanças em uma fonte não exijam reescrever o sistema inteiro.

## Fluxo atual

```text
fontes municipais / nacionais / históricas
                  |
                  v
       HTTP seguro + adaptadores
                  |
                  v
       PublicRecord + SourceRef
                  |
          +-------+-------+
          |               |
          v               v
   SQLite + histórico   documentos
          |
          v
       FTS5 / busca
          |
    +-----+--------------------+
    |              |           |
    v              v           v
proveniência   entidades    qualidade
    |              |           |
    +--------------+-----------+
                   |
          +--------+--------+
          |        |        |
          v        v        v
        API      Python    portal/CLI
```

## Transporte e fronteiras externas

`PoliteHttpClient` centraliza timeout, redirects, limites de resposta, identificação do cliente, retry transitório e validação de destinos. Adaptadores não devem criar políticas de rede incompatíveis entre si.

Conteúdo remoto é entrada não confiável, mesmo quando a origem é oficial. Uma resposta inesperada deve falhar de forma explícita em vez de ser reinterpretada silenciosamente.

## Adaptadores de fonte

Adaptadores em `src/suzano_aberta/sources/` conhecem formatos upstream e convertem material para o modelo comum. Uma falha em um adaptador não deve invalidar registros válidos obtidos por outras fontes.

## Modelo normalizado

`PublicRecord` é a unidade principal. Campos compartilhados são tipados; detalhes próprios da fonte permanecem em `attributes`. `SourceRef` preserva o caminho de volta à publicação de origem.

## Persistência e histórico

A coleta usa SQLite local. Fingerprints determinísticos detectam alterações substantivas. O snapshot distribuído é validado antes de substituir uma geração local válida.

A API abre o snapshot em modo somente leitura e não oferece endpoints de coleta ou mutação.

## Busca

FTS5 é o caminho principal para pesquisa textual. Filtros, ordenação e paginação são compartilhados pela API e por `SuzanoIndex`, reduzindo divergência entre consulta HTTP e local.

## Proveniência

A proveniência acompanha o registro e pode ser exposta separadamente. Ela informa de onde o dado veio e como foi observado; não transforma a publicação em uma conclusão produzida pelo projeto.

## Entidades — 0.7

`entities.py` adiciona uma camada derivada sobre `PublicRecord`. IDs canônicos são determinísticos. Menções preservam registro, fonte e URL que sustentam a associação.

A primeira geração reconhece relações de alta confiança: órgão de origem e CNPJ explicitamente publicado. Regras futuras devem manter o mesmo princípio de evidência auditável.

## Qualidade — 0.7

`quality.py` calcula métricas técnicas reproduzíveis sobre conjuntos de registros. Qualidade de dados é separada de integridade política ou administrativa: a biblioteca mede propriedades como completude de campos selecionados e unicidade de IDs, não desempenho de governo.

## Interfaces

- `Suzano`: coleta e operações locais;
- `SuzanoIndex`: consulta tipada diretamente no snapshot;
- `SuzanoClient`: consumo HTTP tipado;
- API FastAPI/OpenAPI: serviço somente leitura;
- CLI: operação e pesquisa;
- portal: interface pública com fallback estático.

## Princípios de engenharia

1. Fonte antes da interpretação.
2. Falha explícita é melhor que dado inventado.
3. Uma fonte quebrada não destrói o último acervo válido.
4. IDs fortes e estáveis têm precedência sobre heurísticas.
5. Relações precisam preservar evidência.
6. Métricas precisam de definição reproduzível.
7. Operação local é o padrão; servidor é opcional.
8. API pública permanece somente leitura.
9. Mudanças de parser e resolução exigem testes de regressão.
10. O projeto não produz juízo político nem atribui irregularidade a partir de correlação de dados.
