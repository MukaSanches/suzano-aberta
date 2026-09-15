# Windows e CMD

A experiência Windows do Suzano Aberta foi desenhada para funcionar como um produto de terminal, não como uma sequência de comandos Python. Depois da instalação, uma pessoa pode abrir `suzano.cmd`, pesquisar por linguagem natural curta, navegar pelos resultados numerados e voltar à fonte pública original.

## Requisitos

- Windows 10 ou 11;
- Python 3.11, 3.12 ou 3.13 disponível pelo launcher `py` ou no `PATH`;
- internet apenas para instalar dependências, sincronizar o snapshot ou executar operações que consultam fontes públicas.

## Instalação verificada

Na pasta do projeto:

```cmd
instalar-windows.cmd
```

O instalador executa uma preparação em sete etapas: detecta uma versão compatível do Python, cria o `.venv`, atualiza o instalador de pacotes, instala o projeto, executa `pip check`, compila o código para detectar erros de sintaxe e roda smoke tests do CLI, console e diagnóstico local.

O processo para na primeira falha e devolve código diferente de zero. Uma preparação incompleta nunca é apresentada como sucesso.

## Abrir

```cmd
suzano.cmd
```

A tela inicial mostra um retrato local do acervo: quantidade de registros, estado do FTS5, tamanho do banco e versão da biblioteca. O prompt interativo é:

```text
suzano›
```

Se o banco ainda não existir, a própria tela explica que `sincronizar` instala o snapshot público.

## Pesquisa sem decorar sintaxe

Você pode usar o comando explícito:

```text
suzano› buscar transporte escolar
```

ou simplesmente digitar o assunto:

```text
suzano› transporte escolar
```

Os resultados recebem números temporários:

```text
#  Tipo         Título
1  proposicao   ...
2  contrato     ...
3  noticia      ...
```

Depois disso, basta digitar:

```text
suzano› 1
```

para abrir o primeiro registro. O ID técnico continua disponível e pode ser usado normalmente.

## Fonte e navegador

Depois de uma busca:

```text
suzano› fonte 1
```

mostra o nome e a URL da publicação de origem. Para abrir explicitamente a mesma fonte no navegador padrão:

```text
suzano› abrir 1
```

A abertura do navegador só ocorre quando o usuário pede; consultar o acervo não dispara navegação externa.

## Comandos interativos

```text
ajuda
status
diagnostico
sobre
fontes
sincronizar
recentes 20
buscar educação
educação
1
ver 1
fonte 1
abrir 1
panorama
mudancas 20
reindexar
limpar
sair
```

Atalhos disponíveis:

```text
b = buscar
v = ver
r = recentes
p = panorama
m = mudancas
f = fontes
diag = diagnostico
q = sair
```

## Diagnóstico local

O console possui uma inspeção sem chamada de rede:

```text
suzano› diagnostico
```

Ela verifica versão do Python, diretório de dados, espaço livre, abertura do SQLite, presença do FTS5, `PRAGMA quick_check` e disponibilidade do JSON1. O diagnóstico não reindexa nem altera o acervo.

A mesma função está disponível no CLI:

```cmd
suzano.cmd diagnostico
suzano.cmd diagnostico --json
```

## Publicações recentes

```text
suzano› recentes
suzano› recentes 50
```

O comando usa a mesma camada somente leitura do `SuzanoIndex` e deixa os itens numerados para navegação imediata.

## Comandos diretos

`suzano.cmd` continua sendo um wrapper do CLI tradicional:

```cmd
suzano.cmd --help
suzano.cmd inicio
suzano.cmd diagnostico
suzano.cmd diagnostico --json
suzano.cmd recentes --limite 20
suzano.cmd console
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

## Reparar o ambiente sem apagar dados

Se o ambiente virtual estiver corrompido:

```cmd
suzano.cmd reparar
```

ou:

```cmd
instalar-windows.cmd --repair
```

O reparo remove e recria somente `.venv`. O banco `suzano-aberta.sqlite3` permanece separado.

## UTF-8 no Windows

O launcher configura a sessão para UTF-8 antes de iniciar o Python. Isso reduz problemas de acentuação e permite que a interface Rich seja apresentada de forma consistente no CMD e no Windows Terminal.

## Entry points instalados

Depois da instalação:

```cmd
suzano
suzano-aberta
suzano-console
suzano-api
```

`suzano-console` inicia diretamente a experiência interativa. Para scripts e automações, prefira `suzano`/`suzano.cmd` com comandos explícitos.

## Banco local

O padrão é:

```text
suzano-aberta.sqlite3
```

O arquivo fica fora do Git. O console, CLI, `SuzanoIndex` e API usam o mesmo modelo de dados; não existe um banco paralelo específico para Windows.

## Primeiro uso recomendado

```text
suzano› sincronizar
suzano› diagnostico
suzano› recentes
suzano› educação
suzano› 1
```

Isso demonstra instalação do snapshot, saúde local, cronologia, busca e rastreabilidade da fonte em poucos comandos.

## Automação

`suzano.cmd` preserva o código de saída do CLI. Assim, pode ser chamado por scripts `.cmd`, PowerShell, Agendador de Tarefas ou pipelines. `diagnostico --json`, `panorama --json`, `integridade --json` e outras superfícies estruturadas são preferíveis quando outro programa precisa interpretar a saída.
