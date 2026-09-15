# Suzano Aberta

[![CI](https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml/badge.svg)](https://github.com/MukaSanches/suzano-aberta/actions/workflows/ci.yml)

Infraestrutura aberta para coletar, organizar e rastrear dados públicos do município de Suzano, em São Paulo.

O projeto transforma informações espalhadas entre páginas, tabelas, arquivos CSV e documentos oficiais em registros pesquisáveis, sem perder o vínculo com a fonte original.

Suzano Aberta é independente e não possui vínculo institucional com a Prefeitura Municipal de Suzano ou com a Câmara Municipal de Suzano.

## Em termos simples

Hoje, uma pessoa que queira acompanhar uma sessão da Câmara, localizar uma licitação, consultar um contrato ou encontrar um documento orçamentário precisa navegar por páginas diferentes e lidar com formatos diferentes.

Suzano Aberta cria uma camada comum para esse material.

```text
Fontes oficiais
      │
      ├── Câmara Municipal
      ├── Prefeitura
      ├── Diário Oficial
      ├── Licitações
      ├── Contratos
      ├── Contas públicas
      └── Orçamento
             │
             ▼
        Suzano Aberta
             │
      ┌──────┼─────────┐
      ▼      ▼         ▼
   busca  histórico  exportação
```

A fonte oficial continua sendo a referência. A biblioteca existe para tornar a consulta, a comparação e o reuso mais simples.

## O que a versão 0.1 entrega

A primeira versão inclui coleta real e rastreável de fontes públicas oficiais, armazenamento local e ferramentas de inspeção.

| Área | O que é coletado |
| --- | --- |
| Câmara | vereadores da legislatura atual e sessões ordinárias |
| Produção legislativa | proposições publicadas nas sessões disponíveis |
| Contratos da Câmara | CSV oficial quando publicado, com fallback para tabela pública |
| Comissões | pautas das reuniões das comissões permanentes |
| Presenças | consolidação de presença, ausência e licença por vereador |
| Diário Legislativo | índice de edições oficiais em PDF |
| Licitações da Prefeitura | publicações do índice oficial de editais e licitações |
| Estrutura administrativa | secretarias e dados publicados no portal municipal |
| Contas públicas | documentos fiscais e relatórios disponibilizados pela Prefeitura |
| Orçamento | PPA, LDO, LOA e documentos relacionados publicados no portal |
| Imprensa Oficial | edições públicas do Diário Oficial do Executivo |
| Leis e decretos | documentos publicados na área oficial de legislação do Executivo |
| Notícias institucionais | publicações recentes do portal municipal |

A biblioteca também mantém um histórico local das mudanças observadas entre coletas. Ela não interpreta uma alteração como irregularidade; registra apenas que o conteúdo público observado mudou.

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

## Primeiros comandos

Verifique se as fontes oficiais estão acessíveis:

```bash
suzano doctor
```

Colete o ano corrente:

```bash
suzano coletar --ano 2026
```

Veja o que foi armazenado:

```bash
suzano panorama
```

Pesquise um tema:

```bash
suzano buscar "educação"
```

Veja o que mudou entre coletas:

```bash
suzano mudancas
```

Exporte o acervo local normalizado:

```bash
suzano exportar dados-suzano.json
```

## Uso como biblioteca Python

```python
from suzano_aberta import Suzano

with Suzano(database="suzano.sqlite3") as suzano:
    relatorio = suzano.collect(year=2026)
    resultados = suzano.search("mobilidade")

print(relatorio.records)
for item in resultados[:5]:
    print(item.title)
    print(item.source.url)
```

Também é possível consultar adaptadores diretamente:

```python
from suzano_aberta import Suzano

with Suzano() as suzano:
    sessoes = suzano.camara.sessions(year=2026)
    contratos = suzano.camara.contracts(year=2026)
    licitacoes = suzano.prefeitura.tenders(year=2026)
    secretarias = suzano.prefeitura.secretariats()
```

## Rastreabilidade

Todo registro normalizado conserva pelo menos:

- um identificador interno estável;
- a natureza do registro;
- o título publicado;
- os campos específicos extraídos da fonte;
- a URL oficial de origem;
- o instante UTC da coleta.

O histórico local usa um fingerprint determinístico do conteúdo normalizado. Quando o mesmo registro aparece depois com conteúdo diferente, a mudança é registrada.

Isso permite responder duas perguntas importantes:

1. **de onde veio este dado?**
2. **ele mudou desde a última coleta?**

## Banco local

Por padrão, os dados ficam em:

```text
suzano-aberta.sqlite3
```

Não é necessário PostgreSQL, servidor web ou serviço externo. O arquivo pode ser apagado e reconstruído a partir das fontes públicas.

O projeto não envia telemetria.

## Confiabilidade

A v0.1 segue regras conservadoras:

- prioriza fontes institucionais de primeira parte;
- prefere CSV e dados estruturados quando o órgão os fornece;
- não inventa informação ausente;
- limita a frequência de requisições;
- usa timeout e número de tentativas explícitos;
- separa parsers por órgão;
- possui testes para normalização, persistência e parsers críticos;
- mantém um comando de diagnóstico das fontes;
- executa CI em Python 3.11, 3.12 e 3.13;
- executa smoke tests separados contra fontes públicas reais.

As páginas dos órgãos públicos podem mudar sem aviso. Quando isso acontecer, o comportamento desejado é uma falha observável e corrigível, não a criação silenciosa de dados incorretos.

## Fontes

O inventário completo está em [`docs/fontes.md`](docs/fontes.md). Entre as fontes principais estão:

- Câmara Municipal de Suzano: https://www.camarasuzano.sp.gov.br/
- Sessões ordinárias: https://www.camarasuzano.sp.gov.br/ordinarias/sessoes_ordinarias.php
- Dados estruturados de contratos: https://www.camarasuzano.sp.gov.br/dados-estruturados/
- Diário Oficial do Legislativo: https://www.camarasuzano.sp.gov.br/doel/
- Prefeitura Municipal de Suzano: https://suzano.sp.gov.br/
- Editais e licitações: https://suzano.sp.gov.br/editais-licitacoes/
- Contas públicas: https://suzano.sp.gov.br/transparencia/contas-publicas/
- Leis orçamentárias: https://suzano.sp.gov.br/transparencia/leis-orcamentarias/
- Imprensa Oficial: https://suzano.sp.gov.br/imprensa-oficial/

## Documentação técnica

- [Arquitetura](docs/arquitetura.md)
- [Fontes oficiais](docs/fontes.md)
- [Metodologia de coleta](docs/metodologia.md)
- [Modelo de dados](docs/modelo-de-dados.md)
- [Limitações conhecidas](docs/limitacoes.md)
- [Roteiro de demonstração institucional](docs/demo-institucional.md)

## Desenvolvimento

Instale as dependências de desenvolvimento:

```bash
python -m pip install -e ".[dev]"
```

Execute a verificação local:

```bash
ruff check .
mypy src/suzano_aberta
pytest
python -m build
```

Testes determinísticos ficam em `tests/`. Verificações que acessam sites públicos reais ficam em `tests_live/` e são executadas em workflow separado para não tornar o CI principal dependente da disponibilidade momentânea dos portais.

## Escopo e responsabilidade

Suzano Aberta organiza informações públicas. O projeto não atribui nota a agentes públicos, não classifica automaticamente condutas como regulares ou irregulares e não substitui documentos oficiais, pareceres técnicos ou análise jurídica.

Quando houver divergência, prevalece a publicação do órgão responsável.

## Licença

Código disponibilizado sob a licença Apache 2.0. Os dados e documentos acessados permanecem sujeitos às regras, licenças e condições de suas fontes originais.
