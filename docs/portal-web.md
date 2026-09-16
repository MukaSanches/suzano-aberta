# Portal web

O portal do Suzano Aberta é uma camada pública de leitura sobre o mesmo acervo usado pela API, pelas interfaces Python e pelo CLI. Ele não executa coletores no navegador e não modifica o snapshot publicado.

## Objetivo de produto

A interface é orientada à tarefa principal: encontrar uma publicação pública, entendê-la em contexto e conseguir voltar ao registro de origem com o menor número possível de passos. A camada visual não deve esconder proveniência, transformar ausência de dado em certeza nem substituir documentos oficiais por resumos.

O portal usa o próprio acervo como elemento visual principal: a tela inicial mostra estatísticas derivadas do snapshot, estado do índice e o pipeline de publicação em vez de depender de ilustrações decorativas ou números digitados manualmente.

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

## Experiência v4 e refinamentos v5

A camada `portal-v4` fornece a navegação e o design system principal. A camada `portal-v5` corrige e especializa as telas de exploração e contratações sem reimplementar o núcleo.

Entre os comportamentos atuais:

- navegação global consistente e menu móvel operável por teclado;
- pesquisa rápida disponível por `/` ou `Ctrl/Cmd + K`;
- filtros ativos visíveis e ação explícita para limpar a consulta;
- paginação real da busca;
- painel de filtros sem scroll interno artificial: o documento continua responsável pela rolagem;
- faixa de filtros ativos mantida dentro da coluna de resultados, sem alterar a grade principal;
- estados de carregamento, vazio e degradação da API;
- detalhe de contratação com posicionamento previsível abaixo do cabeçalho fixo;
- ação para copiar o endereço permanente do registro;
- metadados em coluna de leitura própria e responsiva;
- página de status que diferencia snapshot, índice estático e API;
- progresso de leitura e retorno ao topo em páginas extensas;
- movimento reduzido quando solicitado pelo sistema operacional;
- contraste reforçado quando o navegador expõe `prefers-contrast: more`;
- PWA com shell versionado e estratégia network-first para dados mutáveis.

Recursos de interação são progressivos: a navegação básica e os links principais continuam presentes no HTML antes da execução do JavaScript.

## Contratações: fonte oficial específica

O objetivo do botão de fonte não é apenas abrir o domínio responsável. Sempre que os identificadores públicos permitem uma rota específica, o portal materializa uma URL canônica para o próprio registro.

Para registros do PNCP, por exemplo, os controles públicos permitem derivar rotas de leitura como:

```text
/app/editais/<cnpj>/<ano>/<sequencialCompra>
/app/contratos/<cnpj>/<ano>/<sequencialContrato>
/app/atas/<cnpj>/<anoCompra>/<sequencialCompra>/<sequencialAta>
```

O script `scripts/enrich_official_links.py` executa essa resolução depois da geração das coleções. Ele grava `attributes.official_url` e `attributes.official_url_quality` nos dados publicados. Quando a rota exata pode ser demonstrada, a qualidade é `exact`; quando faltam componentes suficientes para uma rota específica, a interface pode usar a busca da própria fonte e deixa claro que se trata de localização, não de um deep link exato.

A resolução não inventa sequenciais nem tenta adivinhar relações. Ela usa somente identificadores presentes no registro, como `numero_controle_pncp`, `numero_controle_pncp_compra` e sequenciais publicados.

As coleções especializadas preservam ainda as regras do núcleo:

- proposição não é apresentada automaticamente como lei;
- relações entre registros precisam de identificadores ou referências verificáveis;
- uma contratação pode conservar múltiplas fontes sem ser contada como registros distintos apenas por duplicação de publicação;
- valores, situação, vigência e texto jurídico devem ser confirmados na fonte responsável quando a precisão do uso exigir.

## Publicação

O workflow `Portal público` é uma projeção determinística do snapshot rolling. Coleta de PNCP, Compras.gov, Prefeitura e Câmara pertence ao pipeline de dados; a publicação do site não repete milhares de chamadas externas antes de poder ser validada.

O deploy executa, em ordem:

1. download do snapshot rolling;
2. conferência SHA-256;
3. `PRAGMA quick_check` e recusa de banco vazio;
4. geração do índice estático;
5. geração de detalhes e relações;
6. materialização de links oficiais canônicos;
7. atualização do digest de notícias;
8. geração da configuração de runtime;
9. validação estrutural do portal e da Data API;
10. verificação de sintaxe de todos os JavaScript publicados com `node --check`;
11. preparação e publicação no GitHub Pages.

O workflow também roda em pull requests que alteram o portal, mas o deploy só acontece fora de PRs. A rotina agendada atual é executada a cada 30 minutos.

Essa separação impede que uma indisponibilidade temporária de uma API externa bloqueie a publicação de um snapshot que já passou por checksum e integridade.

## Validação estática

`python scripts/check_web.py` recusa a build quando encontra, entre outros problemas:

- página obrigatória ausente;
- `lang`, viewport, `<main>` ou `<h1>` ausentes;
- IDs HTML duplicados;
- imagem sem atributo `alt`;
- links locais quebrados;
- handlers JavaScript inline ou URLs `javascript:`;
- rastreadores externos conhecidos;
- ausência das camadas obrigatórias do portal;
- PWA ou assets obrigatórios ausentes;
- Data API sem coleções mínimas;
- shards de detalhes/relações incompletos;
- coleção de contratações sem nenhum link oficial direto materializado;
- URL PNCP marcada como exata mas incompatível com as rotas canônicas aceitas.

O workflow também verifica sintaxe de `portal-v5.js` e dos demais JavaScript publicados.

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
