# Changelog

Todas as mudanças relevantes do projeto são registradas aqui. O formato segue a ideia de Keep a Changelog e o versionamento segue SemVer enquanto compatível com a fase inicial do projeto.

## [0.2.0] - 2026-09-15

### Adicionado

- índice textual SQLite FTS5 com tokenização Unicode, remoção de diacríticos, prefixos e ranking BM25;
- motor autônomo de descoberta web a partir das fontes catalogadas, `robots.txt`, sitemaps e links internos;
- reaproveitamento de páginas previamente descobertas como sementes de atualizações futuras;
- descoberta de menções recentes por feed público de busca de notícias;
- comando `suzano atualizar` para executar coleta estruturada, descoberta, deduplicação e otimização em um único ciclo;
- comando `suzano sincronizar` para instalar o snapshot público diário já indexado;
- comando `suzano reindexar` para reconstruir e otimizar FTS5;
- bootstrap automático do snapshot quando a busca inicia sem banco local;
- fallback de descoberta recente quando uma consulta ainda não existe no índice local;
- workflow diário que preserva o acervo anterior, atualiza as fontes, valida o SQLite, compacta, gera SHA-256 e publica a release rolling `data-latest`;
- metadados `data-latest.json` com total de registros, linhas FTS, contagens por tipo e versão do schema;
- documentação dedicada à arquitetura autônoma e à busca rápida;
- testes determinísticos de descoberta, sitemap, normalização de URL, busca sem acentos, busca por prefixo, ID exato e sementes persistentes.

### Desempenho

- banco configurado com WAL, `synchronous=NORMAL`, cache de páginas, `mmap` e `PRAGMA optimize`;
- busca deixa de depender de `LIKE` como caminho principal e usa índice invertido local;
- `LIKE` permanece como fallback para ambientes sem FTS5 ou consultas que não produzem resultado FTS;
- snapshots são pesquisáveis imediatamente após sincronização, sem recrawl local.

### Segurança e confiabilidade

- crawler limitado a hosts autorizados e condicionado a `robots.txt`;
- arquivos binários e mídia são excluídos do rastreamento HTML;
- URLs são normalizadas e parâmetros de tracking comuns são removidos;
- snapshot remoto é validado por SHA-256 quando disponível, cabeçalho SQLite e `PRAGMA quick_check`;
- snapshots vazios são recusados;
- instalação do snapshot é atômica e remove sidecars WAL/SHM obsoletos;
- cada página descoberta mantém URL e hash do conteúdo observado para rastreabilidade;
- o projeto não afirma indexar literalmente toda a Internet: a cobertura cresce continuamente dentro do universo público relevante a Suzano.

## [0.1.1] - 2026-09-15

### Adicionado

- comando `suzano integridade` para revisar domínios externos inesperados em fontes municipais selecionadas;
- relatório estruturado `IntegrityReport` para uso por scripts e aplicações;
- catálogo explícito do Portal de Transparência da Prefeitura;
- teste de regressão para diferenciar serviços externos conhecidos de domínios não reconhecidos.

### Segurança e confiabilidade

- a verificação de integridade é determinística e baseada em allowlist curta;
- um achado significa apenas que há um link externo não reconhecido e exige revisão humana;
- o sistema não infere invasão, fraude, autoria ou irregularidade a partir de um achado.

## [0.1.0] - 2026-09-15

### Adicionado

- fachada Python `Suzano`;
- CLI em português com `fontes`, `doctor`, `coletar`, `panorama`, `buscar`, `ver`, `mudancas` e `exportar`;
- coleta da Câmara para vereadores, sessões, proposições, contratos, comissões, presenças e Diário Oficial do Legislativo;
- coleta da Prefeitura para licitações, secretarias, contas públicas, leis orçamentárias, Imprensa Oficial, leis e decretos e notícias;
- armazenamento local SQLite em WAL;
- fingerprints determinísticos e histórico de registros novos ou alterados;
- exportação JSON;
- cliente HTTP com timeout, retry limitado e controle de frequência;
- testes unitários dos parsers críticos;
- documentação de arquitetura, metodologia, fontes, modelo de dados, limitações e demonstração institucional;
- integração contínua e smoke tests independentes para fontes reais.

### Segurança e escopo

- nenhuma telemetria;
- nenhuma chave de API obrigatória;
- nenhuma classificação automática de conduta política ou administrativa;
- fontes oficiais preservadas em cada registro normalizado.
