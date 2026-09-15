# Suzano Aberta

[![CI](https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml/badge.svg)](https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml)

Infraestrutura aberta e autônoma para descobrir, coletar, organizar, indexar e rastrear informações públicas sobre o município de Suzano, em São Paulo.

A Suzano Aberta transforma dados espalhados entre páginas, tabelas, CSVs, documentos oficiais e menções públicas na web em um índice local pesquisável, preservando o vínculo com a fonte original.

O projeto é independente e não possui vínculo institucional com a Prefeitura Municipal de Suzano ou com a Câmara Municipal de Suzano.

## O que mudou na 0.2

A versão 0.2 adiciona uma camada de busca contínua. A biblioteca não depende mais apenas de uma lista fixa de parsers: ela continua coletando fontes estruturadas, mas também descobre páginas novas pelos sites oficiais, `robots.txt`, sitemaps e links internos. As páginas encontradas entram no mesmo índice e passam a servir como sementes dos ciclos seguintes.

```text
fontes oficiais + sitemaps + links + menções públicas da web
                         │
                         ▼
                  atualização diária
                         │
             normalização + deduplicação
                         │
                         ▼
                 SQLite + FTS5
                         │
                validação + SHA-256
                         │
                         ▼
             snapshot público rolling
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
      busca local imediata   sincronização rápida
```

A busca usa SQLite FTS5 com tokenização Unicode, remoção de acentos, prefixos e ranking BM25. Consultas como `educacao`, `licit` ou `transporte escolar` são resolvidas no índice local sem precisar varrer os sites novamente.

Nenhuma biblioteca consegue manter uma cópia literal de toda a Internet. O objetivo aqui é mais útil: ampliar continuamente e de forma rastreável o universo público relacionado a Suzano, mantendo a coleta educada, verificável e reconstruível.

## Cobertura

Os coletores estruturados continuam cobrindo áreas como Câmara, sessões, proposições, contratos, comissões, presenças, Diário Legislativo, licitações, secretarias, contas públicas, orçamento, Imprensa Oficial, leis, decretos e notícias institucionais.

Além disso, o motor de descoberta:

- parte das fontes oficiais catalogadas;
- consulta `robots.txt` antes do rastreamento;
- aproveita `sitemap.xml` e índices de sitemap;
- segue links HTML dentro dos domínios permitidos;
- normaliza URLs e remove parâmetros de rastreamento comuns;
- evita arquivos binários e mídia durante o crawl HTML;
- preserva hash do conteúdo, URL, origem da descoberta e profundidade;
- reutiliza páginas já descobertas como sementes de atualizações futuras;
- consulta menções recentes por feeds públicos de busca de notícias;
- deduplica registros antes de gravar.

A fonte original continua sendo a referência final.

## Instalação

Requer Python 3.11 ou superior.

```bash
git clone https://github.com/MukaSanches/suzano-aberta.git
cd suzano-aberta
python -m venv .venv
```

No Windows:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

No Linux ou macOS:

```bash
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

## Começar rápido

Para baixar o índice público diário já preparado:

```bash
suzano sincronizar
```

Depois, pesquise imediatamente:

```bash
suzano buscar "educação"
suzano buscar "transporte escolar"
suzano buscar "licitação saúde"
```

Se ainda não houver banco local, a API tenta instalar automaticamente o snapshot público mais recente. Caso uma consulta não exista no índice local, a busca também pode fazer uma tentativa rápida no feed público de notícias e guardar os resultados encontrados para consultas seguintes. Use `--sem-web` para desativar esse fallback.

## Atualização autônoma

Para executar localmente o mesmo ciclo de atualização usado pela automação diária:

```bash
suzano atualizar
```

Por padrão, o comando atualiza os três anos mais recentes, executa os coletores oficiais, continua a descoberta web a partir do acervo já conhecido, consulta menções recentes e otimiza o índice.

É possível aumentar o orçamento do crawler:

```bash
suzano atualizar --max-paginas 1500 --profundidade 4
```

Ou limitar aos coletores estruturados:

```bash
suzano atualizar --sem-descoberta
```

O workflow `Daily autonomous index` roda diariamente no GitHub Actions. Ele restaura o snapshot anterior, atualiza o acervo, valida o SQLite com `PRAGMA quick_check`, recusa índices vazios, compacta o banco, gera SHA-256 e publica os assets rolling da tag `data-latest`.

## Outros comandos

Verificar fontes oficiais:

```bash
suzano doctor
```

Reconstruir o índice de busca:

```bash
suzano reindexar
```

Ver o acervo por tipo:

```bash
suzano panorama
suzano panorama --json
```

Ver mudanças observadas:

```bash
suzano mudancas
```

Coletar apenas um ano pelos adaptadores estruturados:

```bash
suzano coletar --ano 2026
```

Revisar links externos inesperados em fontes municipais selecionadas:

```bash
suzano integridade
```

Exportar o acervo normalizado:

```bash
suzano exportar dados-suzano.json
```

## Busca rápida

O armazenamento continua sendo um único arquivo SQLite, mas a busca textual usa FTS5. O índice inclui título, resumo, atributos estruturados e nome da fonte, com peso maior para o título.

O banco também usa WAL, `synchronous=NORMAL`, cache de páginas, `mmap` e `PRAGMA optimize`. Quando FTS5 não estiver disponível na compilação local do SQLite, a biblioteca recua para uma busca compatível baseada em `LIKE` em vez de falhar silenciosamente.

O identificador interno também continua pesquisável, e há acesso direto por ID dentro da camada de persistência.

## Snapshot público diário

O snapshot rolling é distribuído como:

```text
suzano-aberta.sqlite3.gz
data-latest.json
suzano-aberta.sqlite3.gz.sha256
```

A sincronização valida o checksum quando disponível, verifica o cabeçalho SQLite e executa `PRAGMA quick_check` antes da instalação. A troca do banco é atômica e também remove sidecars WAL/SHM antigos para evitar que estado local obsoleto seja aplicado ao snapshot novo.

A tag `data-latest` é propositalmente mutável e representa dados correntes. Releases de código permanecem separadas.

## Uso como biblioteca Python

Pesquisa simples:

```python
from suzano_aberta import Suzano

with Suzano(database="suzano.sqlite3") as suzano:
    resultados = suzano.search("mobilidade")

for item in resultados[:5]:
    print(item.title)
    print(item.source.url)
```

Atualização autônoma:

```python
from suzano_aberta import Suzano

with Suzano(database="suzano.sqlite3", auto_sync=False) as suzano:
    relatorio = suzano.refresh(max_pages=1000, max_depth=3)

print(relatorio.indexed_records)
print(relatorio.new_records)
```

Coletores especializados continuam disponíveis:

```python
from suzano_aberta import Suzano

with Suzano(auto_sync=False) as suzano:
    sessoes = suzano.camara.sessions(year=2026)
    contratos = suzano.camara.contracts(year=2026)
    licitacoes = suzano.prefeitura.tenders(year=2026)
    secretarias = suzano.prefeitura.secretariats()
```

## Rastreabilidade

Todo registro normalizado conserva um identificador estável, natureza do registro, título, campos extraídos, URL da fonte e instante de coleta. Páginas descobertas também registram URL normalizada, origem da descoberta, profundidade e hash SHA-256 do conteúdo observado.

O histórico local usa um fingerprint determinístico. Quando o mesmo registro aparece depois com conteúdo diferente, a mudança é registrada. Isso permite responder tanto “de onde veio este dado?” quanto “ele mudou desde a coleta anterior?”.

## Banco local

Por padrão:

```text
suzano-aberta.sqlite3
```

Não é necessário PostgreSQL, Elasticsearch ou servidor externo para pesquisar. O arquivo pode ser sincronizado pelo snapshot público ou reconstruído a partir das fontes.

O projeto não envia telemetria.

## Confiabilidade

A arquitetura adota regras conservadoras:

- fontes estruturadas de primeira parte continuam prioritárias;
- CSV e formatos estruturados são preferidos quando disponíveis;
- dados ausentes não são inventados;
- requisições possuem intervalo mínimo, timeout e retry limitado;
- `robots.txt` é respeitado pelo crawler;
- rastreamento permanece limitado a hosts autorizados;
- mudanças são registradas sem inferir irregularidade;
- índice diário é validado antes da publicação;
- snapshots podem ser verificados por SHA-256;
- CI roda em Python 3.11, 3.12 e 3.13;
- mypy estrito, Ruff, testes, build do pacote e CodeQL fazem parte da validação.

As páginas públicas podem mudar sem aviso. Quando um parser estruturado quebra, o comportamento desejado é uma falha observável e corrigível, não a geração silenciosa de informação incorreta.

## Integridade de fontes

O comando `suzano integridade` revisa links externos presentes em fontes municipais selecionadas. Um achado não significa invasão, fraude ou irregularidade; significa apenas que uma página oficial referencia um domínio externo ainda não reconhecido pelo projeto.

Para automação:

```bash
suzano integridade --json
suzano integridade --falhar-se-encontrar
```

## Documentação técnica

- [Índice autônomo e busca rápida](docs/autonomia-e-busca.md)
- [Arquitetura](docs/arquitetura.md)
- [Fontes oficiais](docs/fontes.md)
- [Metodologia de coleta](docs/metodologia.md)
- [Modelo de dados](docs/modelo-de-dados.md)
- [Integridade de fontes](docs/integridade.md)
- [Limitações conhecidas](docs/limitacoes.md)
- [Roteiro de demonstração institucional](docs/demo-institucional.md)

## Desenvolvimento

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src/suzano_aberta
pytest
python -m build
```

Testes determinísticos ficam em `tests/`. Verificações contra fontes públicas reais ficam em `tests_live/` e são executadas separadamente para não tornar o CI principal dependente da disponibilidade momentânea dos portais.

## Escopo e responsabilidade

Suzano Aberta organiza informações públicas e amplia continuamente seu índice de descoberta. Ela não atribui nota a agentes públicos, não classifica automaticamente condutas como regulares ou irregulares e não substitui documentos oficiais, pareceres técnicos ou análise jurídica.

Quando houver divergência, prevalece a publicação da fonte responsável.

## Licença

Código disponibilizado sob Apache 2.0. Dados e documentos acessados permanecem sujeitos às regras, licenças e condições de suas fontes originais.
