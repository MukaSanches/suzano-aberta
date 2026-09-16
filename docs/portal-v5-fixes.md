# Portal v5 — correções de regressão

Esta revisão surgiu de testes reais do portal publicado em desktop.

## Explorar

O painel de filtros possuía dois problemas combinados:

1. a camada v2 limitava a altura do formulário e criava uma barra de rolagem interna;
2. a camada v4 inseria a faixa de filtros ativos como um terceiro filho da grade `results-shell`, embora a grade tenha sido projetada para duas colunas.

A v5 remove o scroll interno artificial e mantém a faixa de filtros ativos dentro da coluna de resultados. Em telas menores, filtros e resultados voltam naturalmente para uma coluna.

## Detalhes de contratações

A página de detalhes passa a respeitar explicitamente o offset do cabeçalho fixo, possui breadcrumb, ação de copiar link permanente, coluna de metadados e hierarquia tipográfica mais estável.

## Fonte oficial

O portal deixa de tratar a home de uma fonte como equivalente ao registro específico. O build materializa `official_url` e `official_url_quality` em contratações sempre que os identificadores públicos permitem uma rota demonstrável.

No PNCP são aceitas rotas canônicas de edital, contrato e ata. Quando componentes suficientes para uma rota específica não existem, o portal usa uma pesquisa na própria fonte e informa isso ao usuário.

O caso `pncp:ata:4c4df136eac04341d99c`, reportado durante teste manual, é coberto por teste de regressão e resolve para a ata identificada por `46523056000121-1-000049/2026-000001`.

## Gates de publicação

O workflow do Portal público passa a:

- materializar URLs oficiais depois de gerar as coleções;
- validar a sintaxe de `portal-v5.js`;
- exigir deep links oficiais quando os dados permitem;
- validar o shell PWA v5;
- manter CI e CodeQL como gates independentes antes de merge.
