# Usar o Suzano Aberta pelo CMD do Windows

O Suzano Aberta pode ser usado como um programa de terminal no Windows. Não é necessário conhecer Python para usar os comandos depois da instalação inicial.

## Instalação simples

1. Baixe ou clone o repositório.
2. Abra a pasta do projeto.
3. Execute `instalar-windows.cmd`.
4. O instalador cria `.venv`, instala as dependências, valida o CLI e abre o console interativo.

Requisito: Python 3.11 ou superior instalado no Windows.

## Abrir o programa

Dê dois cliques em `suzano.cmd` ou, no CMD, execute:

```cmd
suzano.cmd
```

O prompt muda para:

```text
suzano>
```

A partir daí você permanece dentro do programa e pode executar várias consultas sem repetir o nome do executável.

## Comandos interativos

```text
ajuda
buscar educação
buscar transporte escolar
buscar Santa Casa
panorama
mudancas 20
fontes
sincronizar
reindexar
ver <ID>
limpar
sair
```

O comando `buscar` mostra também o ID interno do resultado. Esse ID pode ser usado imediatamente com `ver`.

## Comandos diretos pelo CMD

Também é possível ignorar o modo interativo:

```cmd
suzano.cmd buscar "educação"
suzano.cmd buscar "transporte escolar" --limite 10
suzano.cmd panorama
suzano.cmd fontes
suzano.cmd sincronizar
suzano.cmd atualizar
suzano.cmd doctor
suzano.cmd exportar dados.json
```

## CLI instalada

Quando o pacote estiver instalado no ambiente ativo, continuam disponíveis os entrypoints oficiais:

```cmd
suzano --help
suzano console
suzano buscar "educação"
suzano-aberta panorama
suzano-api
```

## Onde os dados ficam

Por padrão, o banco local é `suzano-aberta.sqlite3`, na pasta de execução. O parâmetro `--db` permite escolher outro arquivo nos comandos tradicionais e no console:

```cmd
suzano console --db C:\dados\suzano.sqlite3
```

## Filosofia

O console é uma interface para o mesmo motor usado pela biblioteca e pela API. Ele não cria uma segunda base de dados nem uma implementação paralela de busca. Resultados continuam preservando a fonte pública de origem e devem ser tratados como material para consulta e verificação, não como julgamento automático sobre pessoas, empresas ou órgãos públicos.
