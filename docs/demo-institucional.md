# Demonstração institucional

Este roteiro foi pensado para uma apresentação curta a um gabinete, conselho, universidade, associação ou órgão público.

## 1. Explique o problema

Informações públicas de Suzano existem, mas estão distribuídas entre portais, páginas, tabelas e documentos. O projeto não substitui esses portais; cria uma camada técnica comum para consulta e preservação local.

## 2. Verifique as fontes

```bash
suzano doctor
```

O comando mostra quais endereços oficiais catalogados estão acessíveis naquele momento.

## 3. Faça uma coleta

```bash
suzano coletar --ano 2026
```

Ao final, mostre quantas fontes concluíram, quantos registros foram observados e se houve falhas.

## 4. Mostre o panorama

```bash
suzano panorama
```

A tabela resume os tipos de dados armazenados localmente.

## 5. Pesquise um tema

```bash
suzano buscar "educação"
```

Escolha um resultado e destaque a URL oficial preservada.

## 6. Mostre rastreabilidade

```bash
suzano ver <id-do-registro>
```

O ponto principal da demonstração é que o dado nunca fica separado de sua fonte.

## 7. Mostre alterações

Execute uma nova coleta em outro momento e use:

```bash
suzano mudancas
```

A biblioteca registra diferenças observadas sem classificá-las automaticamente como problema ou irregularidade.

## Mensagem central

> Suzano Aberta torna publicações oficiais mais fáceis de consultar, comparar e reutilizar, mantendo o caminho de volta à fonte original.
