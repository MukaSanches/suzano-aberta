# Windows e CMD

O Suzano Aberta possui uma experiência dedicada para Windows. O objetivo é permitir que uma pessoa use o projeto como um programa de terminal sem precisar decorar comandos Python.

## Requisito

- Windows 10 ou 11;
- Python 3.11 ou superior disponível no `PATH` ou pelo launcher `py`;
- conexão com a internet apenas quando for necessário instalar dependências, sincronizar ou coletar dados.

## Instalação em um clique

Na pasta do projeto, execute:

```cmd
instalar-windows.cmd
```

O instalador:

1. procura Python;
2. confirma Python 3.11+;
3. cria `.venv` isolado;
4. atualiza `pip`;
5. instala o projeto e as dependências;
6. executa `pip check`;
7. valida o CLI e o parser do console;
8. abre o console quando tudo termina corretamente.

Se uma etapa falhar, o processo para e retorna código diferente de zero. Ele não apresenta uma instalação incompleta como sucesso.

## Abrir o programa

Depois da instalação:

```cmd
suzano.cmd
```

O terminal entra no modo persistente:

```text
suzano>
```

Você pode então executar várias consultas sem repetir `suzano`.

## Comandos do console

```text
ajuda
status
fontes
sincronizar
buscar educação
buscar "transporte escolar"
panorama
mudancas 20
ver <ID>
reindexar
limpar
sair
```

`buscar` mostra o ID de cada resultado. Copie esse ID para `ver <ID>` e o programa apresenta o registro e a fonte pública original.

## Comandos diretos

`suzano.cmd` também funciona como wrapper do CLI tradicional:

```cmd
suzano.cmd --help
suzano.cmd fontes
suzano.cmd sincronizar
suzano.cmd buscar "educação"
suzano.cmd panorama
suzano.cmd mudancas --limite 20
suzano.cmd atualizar
suzano.cmd acervo-maximo
suzano.cmd doctor
suzano.cmd integridade
suzano.cmd exportar dados.json
```

## Entry point instalado

Depois de instalar o pacote, o modo interativo também pode ser iniciado por:

```cmd
suzano-console
```

Os entrypoints existentes continuam disponíveis:

```cmd
suzano
suzano-aberta
suzano-api
```

## Banco local

O banco padrão é:

```text
suzano-aberta.sqlite3
```

Ele fica fora do Git porque é um artefato local. O console usa o mesmo formato SQLite e o mesmo motor de busca do restante do projeto.

## Primeira pesquisa

A forma mais previsível de começar é:

```text
suzano> sincronizar
suzano> status
suzano> buscar educação
```

A busca tradicional também possui bootstrap automático do snapshot quando necessário. O comando explícito `sincronizar` é útil para deixar claro ao usuário que o índice local está pronto antes da primeira demonstração.

## Problemas comuns

### Python não encontrado

Instale Python 3.11 ou superior e habilite a opção que adiciona Python ao `PATH`. Depois execute novamente `instalar-windows.cmd`.

### Ambiente quebrado

Apague somente a pasta `.venv` e execute `instalar-windows.cmd` novamente. O banco `suzano-aberta.sqlite3` é independente do ambiente virtual.

### Snapshot indisponível

O programa preserva a mensagem de erro. Uma falha de rede ou de publicação não deve ser convertida em dados inventados.

### Busca vazia

Execute `status` e confira a quantidade de registros. Se estiver zero, tente `sincronizar`.

## Automação

Como `suzano.cmd` devolve o código de saída do CLI, ele pode ser usado em scripts `.cmd`, PowerShell, agendadores e pipelines. Para automações estruturadas, prefira os comandos que oferecem `--json` quando disponíveis ou use a API/Python SDK.
