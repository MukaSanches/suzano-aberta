# Arquitetura

Suzano Aberta foi desenhado como uma biblioteca local-first. A coleta, a normalização, a persistência e a apresentação ficam separadas para que uma mudança em um site público não obrigue a reescrever o restante do projeto.

## Fluxo

```text
fontes oficiais
    |
    v
adaptadores de fonte
    |
    v
PublicRecord + SourceRef
    |
    v
SQLite / histórico
    |
    +--> busca
    +--> panorama
    +--> mudanças
    +--> exportação
    +--> API Python / CLI
```

## Camadas

### Transporte HTTP

`PoliteHttpClient` centraliza timeout, redirecionamentos, identificação do cliente, intervalo mínimo entre requisições e tentativas limitadas. Os adaptadores não criam clientes HTTP próprios.

### Adaptadores

Cada órgão possui um adaptador isolado em `src/suzano_aberta/sources/`. O adaptador conhece a estrutura publicada pelo órgão e converte o conteúdo encontrado para o modelo comum do projeto.

### Modelo normalizado

`PublicRecord` é a unidade de armazenamento. O projeto evita criar um esquema rígido para cada tipo de documento na v0.1; os campos comuns ficam tipados e os campos próprios da fonte permanecem em `attributes`.

### Proveniência

Todo registro conserva nome e URL da fonte, além do instante de coleta. O dado estruturado nunca deve apagar o caminho de volta ao documento ou página oficial que lhe deu origem.

### Persistência

O banco padrão é SQLite, em modo WAL. Não existe dependência de servidor, conta externa ou telemetria. Um fingerprint determinístico do conteúdo normalizado permite detectar alterações entre coletas.

## Princípios de engenharia

1. Fonte oficial primeiro.
2. Falha explícita é melhor que dado inventado.
3. Coletores independentes: uma fonte indisponível não invalida as demais.
4. IDs estáveis sempre que a fonte oferece identificador.
5. Operação local por padrão.
6. Dependências pequenas e justificadas.
7. Código de coleta separado de interface e análise.
8. Mudanças de parser acompanhadas por testes de regressão.

## O que não está na v0.1

A v0.1 não faz juízo político, não atribui notas a agentes públicos e não usa modelos de linguagem para inferir fatos ausentes. Também não substitui os portais oficiais.
