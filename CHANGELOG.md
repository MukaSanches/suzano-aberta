# Changelog

Todas as mudanças relevantes do projeto são registradas aqui. O formato segue a ideia de Keep a Changelog e o versionamento segue SemVer enquanto compatível com a fase inicial do projeto.

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
