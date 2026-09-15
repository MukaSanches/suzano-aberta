# Demonstração institucional

Este roteiro serve para apresentar o Suzano Aberta em poucos minutos a uma universidade, associação, conselho, gabinete, equipe técnica, veículo de imprensa ou órgão público. A proposta é demonstrar o software funcionando, com fonte visível e sem depender de slides para provar que a infraestrutura existe.

## Antes da apresentação

No Windows:

```cmd
suzano.cmd
```

Em outros sistemas:

```bash
suzano console
```

Se o snapshot ainda não estiver instalado:

```text
suzano› sincronizar
```

## A demonstração de cinco minutos

### 1. Mostre que o sistema conhece o próprio estado

```text
suzano› diagnostico
```

Explique que o programa diferencia a saúde da máquina local da disponibilidade das fontes externas. O diagnóstico verifica SQLite, FTS5, JSON1, integridade do banco, Python e espaço em disco sem fazer uma coleta na internet.

### 2. Mostre o acervo sem preparar uma consulta

```text
suzano› recentes
```

A lista vem numerada. Isso demonstra que existe um snapshot local consultável, não apenas um conjunto de links estáticos.

### 3. Pesquise como uma pessoa normal pesquisaria

Digite apenas:

```text
suzano› educação
```

Não é necessário escrever uma expressão SQL, URL ou comando Python. O console trata texto comum como busca.

### 4. Abra um resultado pelo número

```text
suzano› 1
```

Mostre o registro completo, o ID estável e a fonte preservada.

### 5. Volte à evidência original

```text
suzano› fonte 1
```

Se for apropriado abrir o navegador durante a apresentação:

```text
suzano› abrir 1
```

O ponto principal é mostrar que o dado pesquisável não fica separado da publicação de origem.

### 6. Mostre a dimensão do índice

```text
suzano› panorama
```

A tabela separa os registros por tipo. Não interprete a contagem como medida de desempenho de qualquer órgão; ela descreve apenas o que está presente naquele snapshot.

### 7. Mostre que mudanças são observáveis

```text
suzano› mudancas 20
```

O sistema registra observações de itens novos ou alterados sem converter uma diferença técnica em acusação ou conclusão automática.

## Segunda demonstração: operação técnica

Se o público for técnico, saia do console e mostre as superfícies programáticas:

```bash
suzano inicio
suzano diagnostico --json
suzano buscar "transporte escolar" --limite 10
suzano-api
```

Depois abra localmente:

```text
http://127.0.0.1:8000/docs
```

Isso demonstra que o mesmo projeto possui interface humana, CLI para automação, biblioteca Python, snapshot local e API OpenAPI somente leitura.

## Saúde e integridade das fontes

Quando houver internet disponível:

```bash
suzano doctor
suzano integridade
```

`doctor` verifica acessibilidade. `integridade` executa regras específicas de revisão. Um achado de integridade significa apenas que a regra encontrou um sinal documentado; não prova invasão, fraude, autoria ou irregularidade.

## Coleta ao vivo

Uma coleta real pode demorar e depende da disponibilidade de terceiros. Use-a quando fizer sentido demonstrar ingestão:

```bash
suzano coletar --ano 2026
```

ou:

```bash
suzano atualizar --anos 2025,2026
```

Não dependa de uma coleta ao vivo para demonstrar a busca. O desenho por snapshot existe justamente para separar ingestão cara de consulta rápida.

## Mensagem central

> O Suzano Aberta transforma publicações públicas dispersas em um acervo pesquisável e reutilizável sem cortar o caminho de volta à fonte original.

## Cuidados ao apresentar números

Uma contagem descreve o snapshot e as fontes que contribuíram para ele. Se uma fonte estiver indisponível ou uma área ainda não tiver cobertura completa, isso deve ser informado. O software prioriza uma lacuna explícita a um número preenchido por inferência.
