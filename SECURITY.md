# Política de segurança

## Versões suportadas

Enquanto o projeto estiver na série `0.x`, apenas a versão mais recente recebe correções de segurança.

| Série | Suporte |
| --- | --- |
| versão `0.x` mais recente | sim |
| versões anteriores | não |

## Como relatar

Não publique credenciais, tokens, cookies, dados privados ou detalhes exploráveis em uma issue pública. Use o recurso privado de Security Advisories do GitHub quando estiver disponível para o repositório.

Um relato útil informa a versão afetada, impacto esperado, passos mínimos para reprodução, sistema operacional, versão do Python e uma correção sugerida quando houver.

## Modelo de ameaça atual

O Suzano Aberta trabalha com conteúdo público obtido de sistemas externos e com um snapshot SQLite local. Conteúdo remoto continua sendo entrada não confiável mesmo quando a origem é legítima.

Os riscos considerados incluem respostas ou documentos malformados/excessivamente grandes, mudanças de estrutura upstream, redirecionamentos imprevistos, destinos de rede inadequados, dependências vulneráveis, regressões na cadeia de CI, snapshots inválidos, links externos inesperados e exposição indevida de superfícies de escrita em serviços públicos.

O projeto não precisa de credenciais para seu fluxo público normal, não envia telemetria do usuário e não deve ser executado com privilégios administrativos sem necessidade.

## Fronteiras principais

- **Coleta:** acessa conteúdo externo com timeout, limites, validação de redirects e retry restrito.
- **Persistência:** coletores escrevem no banco de trabalho; publicação exige validação antes de promover um snapshot.
- **Consulta local:** `SuzanoIndex` e diagnóstico abrem o snapshot para leitura quando aplicável.
- **API:** a superfície HTTP pública é somente leitura e não expõe crawler, reindexação, shell ou escrita de arquivo.
- **Portal:** serve dados derivados; coleta e atualização continuam fora do navegador.
- **Windows:** instalação usa ambiente virtual local; `reparar` recria apenas `.venv` e não deve apagar o snapshot.

Detalhes adicionais estão em [`docs/SECURITY-BOUNDARIES.md`](docs/SECURITY-BOUNDARIES.md).

## Controles do repositório

A linha atual utiliza controles complementares:

- CI em todas as versões de Python suportadas;
- compilação do pacote antes dos testes;
- `ruff` para erros estáticos essenciais;
- `mypy` em modo estrito sobre o pacote;
- testes determinísticos e build do wheel/sdist em pull requests;
- smoke tests das interfaces públicas depois da instalação do pacote construído;
- build do container da API;
- CodeQL para análise estática de segurança;
- Dependabot para dependências Python e GitHub Actions;
- GitHub Actions fixadas por SHA imutável nos workflows mantidos pelo projeto;
- smoke tests independentes contra fontes públicas reais;
- validação de checksum e integridade dos snapshots publicados;
- `suzano diagnostico` para saúde local;
- `suzano doctor` para disponibilidade das fontes;
- `suzano integridade` para destacar sinais específicos que exigem revisão.

Nenhum controle isolado é tratado como prova de segurança absoluta. A combinação existe para reduzir risco, limitar impacto e tornar falhas observáveis.

## Integridade de fontes públicas

A verificação de integridade documentada em [`docs/integridade.md`](docs/integridade.md) não é um detector de invasão. Ela registra sinais verificáveis — por exemplo, um domínio externo não reconhecido — para revisão humana.

Não abra um incidente público atribuindo fraude, comprometimento, autoria ou irregularidade apenas com base em um achado automático.

## Dependências e cadeia de CI

Dependências do aplicativo permanecem declaradas em `pyproject.toml`. Dependências de GitHub Actions usadas nos workflows oficiais são referenciadas por commit SHA e acompanhadas por comentário de versão para auditoria humana.

Atualizações de dependências e mudanças nas fronteiras de segurança devem passar pelas mesmas verificações automatizadas das demais mudanças.

## Implantação pública

O repositório não substitui controles de infraestrutura. Uma API exposta publicamente continua precisando de TLS, rate limiting de borda, política de rede, logs, backups, atualização de dependências e monitoramento compatíveis com o ambiente em que estiver hospedada.
