# Changelog

Todas as mudanças relevantes do Suzano Aberta são registradas aqui. O formato segue a ideia de Keep a Changelog e o versionamento segue SemVer enquanto compatível com a série inicial `0.x`.

## [Unreleased]

Sem mudanças ainda após a preparação da 0.8.0.

## [0.8.0] - 2026-09-15

### Experiência local e Windows

- console interativo transformado em uma interface navegável: texto digitado diretamente vira busca e resultados podem ser abertos por número;
- adicionados `recentes`, `fonte`, `abrir`, `diagnostico`, `sobre` e atalhos de teclado/comando no console;
- tela inicial passa a exibir quantidade de registros, estado do FTS5, tamanho do banco e versão da biblioteca;
- `suzano.cmd` passa a configurar UTF-8, suportar instalação explícita e oferecer `suzano.cmd reparar` sem apagar o banco local;
- instalador Windows refeito como fluxo verificado em sete etapas, incluindo `pip check`, compilação e smoke tests;
- nova API local de diagnóstico, sem rede, para Python, diretório de dados, espaço livre, SQLite, FTS5, JSON1 e `PRAGMA quick_check`;
- novos comandos CLI `inicio`, `diagnostico`, `recentes` e `console`;
- `suzano ver` passa a usar lookup exato de ID em vez de pesquisa textual aproximada;
- busca CLI passa a mostrar o ID do registro e limites explícitos são aplicados a consultas humanas;
- textos externos exibidos no console são renderizados de forma segura sem serem tratados como markup Rich.

### Engenharia e documentação

- versão do pacote elevada para `0.8.0` com validação explícita do wheel instalado no CI;
- CI expandido para testar as novas superfícies de diagnóstico, navegação e CLI em Python 3.11, 3.12 e 3.13;
- novos testes determinísticos para aliases, navegação numerada, diagnóstico de banco ausente e diagnóstico profundo de SQLite;
- `README.md` reescrito como referência de produto e engenharia, com demonstração em 30 segundos e arquitetura completa;
- documentação Windows atualizada para a experiência navegável e autorreparo;
- limitações antigas da v0.1 substituídas por uma descrição atual e explícita do escopo;
- `CITATION.cff` e contrato da API sincronizados com a versão real do pacote.

## [0.7.0] - 2026-09-15

### Entidades e qualidade

- camada determinística de entidades sobre `PublicRecord`;
- IDs canônicos estáveis por categoria e identificador forte quando disponível;
- menções preservam registro, fonte e URL que sustentam a associação;
- reconhecimento conservador de órgão de origem e CNPJ explicitamente publicado;
- `QualityReport` com métricas reproduzíveis de completude, unicidade, duplicações e diversidade de fontes;
- testes e documentação específicos para entidades, relações e qualidade de dados.

## [0.6.0] - 2026-09-15

### Interfaces Python

- `SuzanoClient` para consumo HTTP tipado da API;
- `SuzanoIndex` para consulta direta e somente leitura do snapshot SQLite;
- paginação tipada com offsets anterior/próximo e iteração automática;
- tratamento estruturado de Problem Details por `SuzanoApiError`;
- semântica de filtros, datas e ordenação compartilhada entre API e consulta local;
- smoke tests do pacote construído e documentação dedicada às interfaces Python.

## [0.5.0] - 2026-09-15

### Interoperabilidade e portal

- evolução do contrato HTTP para API 1.2 com separação explícita entre versão do pacote, API, schema e dataset;
- proveniência por registro em JSON-LD e catálogo orientado a interoperabilidade;
- endpoint de capabilities e catálogo de fontes presentes no snapshot;
- fortalecimento da política de consumo de APIs e respostas externas;
- portal público estático em GitHub Pages com estratégia API-first e fallback derivado do snapshot;
- identidade visual vetorial, páginas de projeto/status/acessibilidade e PWA mínima;
- índice estático em Web Worker com dados particionados para evitar download monolítico;
- publicação do portal condicionada à validação do snapshot e seus índices derivados;
- enriquecimento do portal e do checkpoint com fontes estruturadas nacionais de contratações.

## [0.4.0] - 2026-09-15

### API HTTP

- API pública baseada em FastAPI e OpenAPI;
- rotas versionadas em `/v1` para busca, listagem, leitura individual, estatísticas, histórico e descoberta do snapshot;
- documentação automática em `/docs`, `/redoc` e `/openapi.json`;
- camada SQLite exclusivamente em modo leitura para o serviço HTTP;
- filtros por tipo, ano e fonte, paginação limitada e total de resultados;
- `ETag`, cache condicional, request ID e `Server-Timing`;
- health checks separados em liveness e readiness;
- CORS e hosts aceitos configuráveis;
- bootstrap opcional do snapshot e sincronização periódica opcional;
- comando `suzano-api`, Dockerfile sem root e `compose.yaml`;
- testes determinísticos da API e build de container no CI.

### Segurança do serviço

- nenhuma rota pública de escrita, exclusão, coleta ou reindexação;
- consultas e paginação possuem limites explícitos;
- cargas em massa são direcionadas ao snapshot;
- TLS, rate limiting global e proteção de borda permanecem responsabilidades da implantação.

## [0.3.0] - 2026-09-15

### Documentos e arquivo histórico

- catálogo de arquivos públicos descobertos, incluindo PDF, DOCX, XLSX, CSV, XML, TXT e formatos relacionados;
- extração local de texto pesquisável de PDF e formatos Office/OpenDocument baseados em ZIP/XML;
- registros `arquivo` e `arquivo_historico` integrados ao FTS5;
- descoberta histórica por Common Crawl, Wayback Machine e catálogo do Internet Archive;
- sementes adicionais para áreas profundas de transparência e documentos públicos;
- comando `suzano acervo-maximo` e opções de coleta histórica;
- workflow de bootstrap de acervo com validação SQLite/FTS antes da publicação;
- documentos acima do limite seguro permanecem catalogados mesmo sem extração integral.

## [0.2.0] - 2026-09-15

### Busca e atualização autônoma

- SQLite FTS5 com tokenização Unicode, remoção de diacríticos, prefixos e BM25;
- descoberta web a partir de fontes catalogadas, `robots.txt`, sitemaps e links internos;
- reaproveitamento de páginas descobertas como sementes de ciclos futuros;
- comando `suzano atualizar` para coleta, descoberta, deduplicação e otimização;
- comandos `suzano sincronizar` e `suzano reindexar`;
- bootstrap automático do snapshot em buscas sem banco local;
- fallback de descoberta recente quando a consulta ainda não está no índice;
- workflow diário que valida, compacta, calcula SHA-256 e publica o snapshot rolling;
- ajustes SQLite de WAL, cache, `mmap` e `PRAGMA optimize`;
- instalação atômica do snapshot e recusa de bancos vazios ou inválidos.

## [0.1.1] - 2026-09-15

### Integridade de fontes

- comando `suzano integridade`;
- `IntegrityReport` estruturado para scripts e aplicações;
- catálogo explícito do Portal de Transparência da Prefeitura;
- allowlist curta para distinguir serviços conhecidos de domínios externos não reconhecidos;
- linguagem deliberadamente conservadora: um achado é sinal para revisão, não prova de incidente ou irregularidade.

## [0.1.0] - 2026-09-15

### Fundação

- fachada Python `Suzano`;
- CLI em português com `fontes`, `doctor`, `coletar`, `panorama`, `buscar`, `ver`, `mudancas` e `exportar`;
- coleta da Câmara para vereadores, sessões, proposições, contratos, comissões, presenças e Diário Oficial do Legislativo;
- coleta da Prefeitura para licitações, secretarias, contas públicas, leis orçamentárias, imprensa oficial, leis/decretos e notícias;
- armazenamento SQLite local com fingerprints determinísticos e histórico de mudanças;
- exportação JSON;
- cliente HTTP com timeout, retry limitado e controle de frequência;
- testes unitários dos parsers críticos e smoke tests separados contra fontes reais;
- documentação inicial de arquitetura, metodologia, fontes, modelo de dados, limitações e demonstração institucional;
- nenhuma telemetria, nenhuma chave de API obrigatória e nenhuma classificação automática de conduta política ou administrativa.
