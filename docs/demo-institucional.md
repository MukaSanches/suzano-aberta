# Demonstração institucional

Este roteiro foi pensado para uma apresentação curta a um gabinete, conselho, universidade, associação ou órgão público. A demonstração funciona no terminal e evita depender de slides para provar que a infraestrutura existe.

## 1. Explique o problema

Informações públicas de Suzano existem, mas estão distribuídas entre portais, páginas, tabelas e documentos. O projeto não substitui esses portais; cria uma camada técnica comum para consulta, rastreabilidade e preservação local.

## 2. Verifique as fontes

```bash
suzano doctor
```

O comando mostra quais endereços oficiais catalogados estão acessíveis naquele momento.

## 3. Revise a integridade dos links

```bash
suzano integridade
```

O comando destaca domínios externos que não fazem parte da lista conhecida pelo projeto. Um achado significa apenas que existe um link para revisão humana; não representa acusação de invasão, fraude ou irregularidade.

## 4. Faça uma coleta

```bash
suzano coletar --ano 2026
```

Ao final, mostre quantas fontes concluíram, quantos registros foram observados e se houve falhas.

## 5. Mostre o panorama

```bash
suzano panorama
```

A tabela resume os tipos de dados armazenados localmente.

## 6. Pesquise um tema

```bash
suzano buscar "educação"
```

Escolha um resultado e destaque a URL oficial preservada.

## 7. Mostre rastreabilidade

```bash
suzano ver <id-do-registro>
```

O ponto principal da demonstração é que o dado nunca fica separado de sua fonte.

## 8. Mostre alterações

Execute uma nova coleta em outro momento e use:

```bash
suzano mudancas
```

A biblioteca registra diferenças observadas sem classificá-las automaticamente como problema ou irregularidade.

## O que vale demonstrar em cinco minutos

Uma apresentação curta pode seguir esta sequência:

```bash
suzano doctor
suzano integridade
suzano coletar --ano 2026
suzano panorama
suzano buscar "educação"
```

Depois, abra um resultado específico com `suzano ver`. Isso mostra, em poucos minutos, disponibilidade das fontes, integridade básica, coleta, organização, busca e rastreabilidade.

## Mensagem central

> Suzano Aberta torna publicações oficiais mais fáceis de consultar, comparar e reutilizar, mantendo o caminho de volta à fonte original.

## Limite da apresentação

Não apresente contagens como se representassem toda a atividade do município quando uma fonte estiver indisponível. O relatório de coleta deve acompanhar qualquer demonstração quantitativa para deixar claro o que foi efetivamente observado naquela execução.
