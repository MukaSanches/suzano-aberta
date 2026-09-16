# Portal web

O portal do Suzano Aberta é uma camada pública de leitura sobre o mesmo acervo usado pela API, pelas interfaces Python e pelo CLI. Ele não executa coletores no navegador e não modifica o snapshot publicado.

## Objetivo de produto

A interface é orientada à tarefa principal: encontrar uma publicação pública e conseguir voltar à sua origem. A camada visual não deve esconder proveniência, transformar ausência de dado em certeza nem substituir documentos oficiais por resumos.

O portal v4 trata o próprio acervo como elemento visual principal: a tela inicial mostra estatísticas derivadas do snapshot, estado do índice e o pipeline de publicação em vez de depender de ilustrações decorativas ou números digitados manualmente.

## Decisões de arquitetura

A interface segue princípios recorrentes em serviços digitais públicos maduros: linguagem simples, navegação previsível, acessibilidade, consistência, desempenho e confiança. A implementação e a identidade são próprias.

### API primeiro, fallback estático

1. Quando `web/config.json` contém `api_base`, as consultas tentam a API HTTP v1.2.
2. Se a API falha ou não está configurada, um Web Worker usa o índice estático derivado do snapshot.
3. O índice estático é dividido em 32 shards de postings compactados por gzip; a consulta baixa apenas os shards associados aos termos pesquisados.
4. Metadados e léxico ficam em arquivos separados para reduzir trabalho repetido.
5. A paginação do portal usa 40 itens por página tanto na API quanto no índice estático.
6. Um identificador de sequência impede que uma resposta lenta de uma busca antiga substitua visualmente o resultado de uma busca mais recente.

Essa separação permite que o portal continue útil durante indisponibilidade da API consultiva.

## Experiência v4

A camada `portal-v4` acrescenta recursos progressivos sem alterar o formato do acervo:

- navegação global consistente e menu móvel operável por teclado;
- pesquisa rápida disponível por `/` ou `Ctrl/Cmd + K`;
- filtros ativos visíveis e ação explícita para limpar a consulta;
- paginação real da busca;
- estados de carregamento, vazio e degradação da API;
- página de status que diferencia snapshot, índice estático e API;
- progresso de leitura e retorno ao topo em páginas extensas;
- movimento reduzido quando solicitado pelo sistema operacional;
- contraste reforçado quando o navegador expõe `prefers-contrast: more`;
- PWA com shell versionado e estratégia network-first para dados mutáveis.

Recursos de interação são progressivos: a navegação básica e os links principais continuam presentes no HTML antes da execução do JavaScript.

## Contratações e legislação

As coleções especializadas preservam as mesmas regras do núcleo:

- proposição não é apresentada automaticamente como lei;
- relações entre registros precisam de identificadores ou referências verificáveis;
- uma contratação pode conservar múltiplas fontes sem ser contada como registros distintos apenas por duplicação de publicação;
- valores, situação, vigência e texto jurídico devem ser confirmados na fonte responsável quando a precisão do uso exigir.

## Publicação

O workflow `Portal público` executa, em ordem:

1. download do snapshot rolling;
2. conferência SHA-256;
3. `PRAGMA quick_check` e recusa de banco vazio;
4. atualização das integrações de compras públicas usadas pelo portal;
5. geração do índice estático;
6. geração de detalhes e relações;
7. atualização do digest de notícias;
8. geração da configuração de runtime;
9. validação estrutural do portal e da Data API;
10. verificação de sintaxe de todos os JavaScript publicados com `node --check`;
11. preparação e publicação no GitHub Pages.

O workflow também roda em pull requests que alteram o portal, mas o deploy só acontece fora de PRs. A rotina agendada atual é executada a cada 30 minutos.

## Validação estática

`python scripts/check_web.py` recusa a build quando encontra, entre outros problemas:

- página obrigatória ausente;
- `lang`, viewport, `<main>` ou `<h1>` ausentes;
- IDs HTML duplicados;
- imagem sem atributo `alt`;
- links locais quebrados;
- handlers JavaScript inline ou URLs `javascript:`;
- rastreadores externos conhecidos;
- ausência da camada v4 nas páginas públicas;
- PWA ou assets obrigatórios ausentes;
- Data API sem coleções mínimas;
- shards de detalhes/relações incompletos.

Essas verificações não substituem testes visuais e com tecnologia assistiva, mas impedem regressões estruturais comuns de chegarem à publicação.

## Acessibilidade

A meta é WCAG 2.2 nível AA quando aplicável. O portal inclui link de salto, foco visível, navegação por teclado, rótulos explícitos, layout responsivo, suporte a zoom, regiões vivas para resultados, alvos de interação maiores e respeito a preferências de movimento e contraste.

Acessibilidade não é tratada como selo permanente. Mudanças de conteúdo e navegador exigem testes manuais recorrentes com teclado, zoom e tecnologias assistivas.

## Privacidade

O portal não inclui analytics de terceiros, pixel de anúncios, fontes remotas ou bibliotecas visuais carregadas de CDNs. Os recursos essenciais são servidos pelo próprio GitHub Pages. Links para fontes originais deixam o portal de forma explícita.

## Configuração da API

A variável de repositório `SUZANO_API_BASE` pode ser definida quando houver um endereço público estável para a API. O workflow a escreve no `config.json` do artefato. Sem essa variável, a busca estática permanece ativa.

## GitHub Pages

O repositório contém o workflow completo de build e deploy. A fonte de publicação do repositório deve permanecer configurada para GitHub Actions.
