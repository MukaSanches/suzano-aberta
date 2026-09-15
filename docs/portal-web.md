# Portal web

O portal do Suzano Aberta é uma camada pública de leitura. Ele não executa coletores e não modifica o acervo.

## Decisões de arquitetura

A interface foi desenhada a partir de princípios recorrentes em sistemas públicos digitais maduros: foco em necessidades reais, linguagem simples, componentes previsíveis, acessibilidade, consistência e confiança. A implementação é própria e não copia identidade visual ou código de nenhum governo.

### API primeiro, fallback estático

1. Quando `web/config.json` contém `api_base`, as consultas usam a API v1 e o FTS5 completo.
2. Se a API falha ou não está configurada, um Web Worker usa o índice estático derivado do snapshot.
3. O índice estático é dividido em 32 shards de postings compactados por gzip; a consulta baixa apenas os shards associados aos termos pesquisados.
4. Metadados e léxico ficam em arquivos separados para reduzir trabalho repetido.

Essa separação permite que o portal continue útil mesmo durante indisponibilidade da API.

## Publicação

O workflow `Portal público` baixa o snapshot rolling, confere SHA-256, descompacta o SQLite, executa `PRAGMA quick_check`, recusa banco vazio, gera o índice web e só então prepara o artefato do GitHub Pages.

A publicação diária ocorre depois do ciclo principal de atualização do acervo. Pushes que alteram o portal também disparam uma nova build.

## Acessibilidade

A meta é WCAG 2.2 AA. A interface inclui link de salto, foco visível, ordem semântica, rótulos explícitos, layout responsivo, suporte a zoom, regiões vivas para status e respeito a `prefers-reduced-motion`.

`python scripts/check_web.py` faz verificações determinísticas mínimas, mas não substitui testes manuais com teclado, leitores de tela e diferentes níveis de zoom.

## Privacidade

O portal não inclui analytics, pixel de anúncios, fontes remotas ou scripts de rastreamento. Recursos essenciais são servidos pelo próprio GitHub Pages. Links para fontes originais deixam o portal de forma explícita.

## Configuração da API

A variável de repositório `SUZANO_API_BASE` pode ser definida quando houver um endereço público estável para a API. O workflow a escreve no `config.json` do artefato. Sem essa variável, a busca estática permanece ativa.

## GitHub Pages

O repositório contém o workflow completo de build e deploy. O GitHub exige que a fonte de publicação do repositório esteja configurada para **GitHub Actions** antes da primeira implantação.
