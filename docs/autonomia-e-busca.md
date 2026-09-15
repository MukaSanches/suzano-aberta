# Índice autônomo e busca rápida

A versão 0.2 transforma a Suzano Aberta em uma infraestrutura de atualização contínua. A ideia central é separar o trabalho caro de descobrir/coletar dados do trabalho barato de pesquisar.

## Como funciona

```text
fontes oficiais + sitemaps + links + menções recentes da web
                         │
                         ▼
               atualização diária
                         │
              normalização + deduplicação
                         │
                         ▼
                SQLite + FTS5
                         │
              validação + checksum
                         │
                         ▼
          snapshot público data-latest
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
      busca local imediata   sincronização rápida
```

## Descoberta automática

O rastreador começa nas fontes oficiais conhecidas, consulta `robots.txt`, aproveita `sitemap.xml` quando disponível e segue links HTML dentro dos mesmos domínios autorizados. O objetivo é descobrir páginas que ainda não possuem um parser dedicado sem transformar o projeto em um crawler agressivo.

Páginas HTML descobertas viram registros `pagina_web`. O texto pesquisável é preservado de forma limitada, junto com URL canônica, origem da descoberta, profundidade, hash do conteúdo e fonte.

A atualização também consulta o feed público de busca do Google News para um conjunto de consultas sobre Suzano. Essas entradas ampliam a cobertura de menções recentes fora dos portais municipais sem copiar o conteúdo integral das matérias: ficam título, publicador, data, consulta que levou à descoberta e link da fonte.

## Busca em milissegundos

A busca usa SQLite FTS5 com tokenização Unicode e remoção de diacríticos. Isso permite consultas como `educacao` encontrarem `Educação`, além de prefixos como `licit` encontrarem `licitação`.

O ranking usa BM25 com peso maior para o título, depois resumo, atributos estruturados e nome da fonte. O `LIKE` antigo continua existindo como fallback caso a instalação do SQLite não tenha FTS5.

O banco usa WAL, `synchronous=NORMAL`, cache de páginas, `mmap` e `PRAGMA optimize` para manter boa latência sem exigir servidor externo.

## Atualização diária

O workflow `Daily autonomous index` roda uma vez por dia e pode ser disparado manualmente. Ele:

1. baixa o snapshot anterior, quando existir;
2. atualiza os três anos mais recentes das fontes estruturadas;
3. executa descoberta por sitemap e links;
4. atualiza menções recentes da web;
5. reconstrói/otimiza o índice FTS quando necessário;
6. roda `PRAGMA quick_check` e recusa banco vazio;
7. gera `data-latest.json` com estatísticas;
8. comprime o SQLite e gera SHA-256;
9. publica os arquivos na release rolling `data-latest`.

O snapshot rolling é propositalmente mutável. Releases de código continuam separadas.

## Uso

Atualização completa local:

```bash
suzano atualizar
```

Aumentar a cobertura do rastreador:

```bash
suzano atualizar --max-paginas 1500 --profundidade 4
```

Baixar o índice público já pronto:

```bash
suzano sincronizar
```

Pesquisar:

```bash
suzano buscar "transporte escolar"
```

Se o banco local ainda não existir, a API tenta instalar automaticamente o snapshot público. Se uma consulta não tiver resultado local, a busca pode fazer uma tentativa rápida no feed público de notícias e guardar os itens encontrados para consultas seguintes. Esse fallback pode ser desativado com `--sem-web`.

## API Python

```python
from suzano_aberta import Suzano

with Suzano() as suzano:
    resultados = suzano.search("educação")

with Suzano(auto_sync=False) as suzano:
    relatorio = suzano.refresh(max_pages=1000, max_depth=3)
```

## Limites deliberados

Nenhuma biblioteca consegue manter uma cópia completa de toda a Internet. A Suzano Aberta busca cobertura crescente e verificável do universo público relevante a Suzano, não uma promessa impossível de indexar cada página existente.

O desenho prioriza:

- fontes públicas e rastreáveis;
- respeito a `robots.txt`;
- frequência baixa de requisições;
- descoberta incremental;
- deduplicação por identificador estável;
- hash para detectar mudanças;
- busca local sem dependência de um serviço proprietário;
- possibilidade de acrescentar novos coletores e novas sementes sem mudar o núcleo da busca.

A fonte original continua sendo a referência final para qualquer informação encontrada.
