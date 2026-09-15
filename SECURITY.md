# Política de segurança

## Versões suportadas

Enquanto o projeto estiver na série `0.x`, apenas a versão mais recente recebe correções de segurança.

| Série | Suporte |
| --- | --- |
| versão `0.x` mais recente | sim |
| versões anteriores | não |

## Como relatar

Não publique credenciais, tokens, cookies ou detalhes exploráveis em uma issue pública. Use o recurso privado de Security Advisories do GitHub quando disponível para o repositório.

Inclua no relato:

- versão afetada;
- impacto esperado;
- passos mínimos para reprodução;
- sistema operacional e versão do Python;
- correção sugerida, se houver.

Não inclua dados privados que não sejam necessários para reproduzir o problema.

## Modelo de ameaça da série 0.1

Suzano Aberta acessa apenas fontes públicas e grava um banco SQLite local. Não executa JavaScript remoto, não envia telemetria e não requer credenciais.

Os principais riscos considerados são:

- conteúdo remoto malformado;
- documentos ou respostas excessivamente grandes;
- mudanças inesperadas de estrutura nas fontes;
- redirecionamentos imprevistos;
- dependências vulneráveis;
- alterações não intencionais na cadeia de CI;
- links externos inesperados publicados em páginas oficiais.

A biblioteca não deve ser executada com privilégios administrativos sem necessidade.

## Controles do repositório

A linha atual utiliza controles complementares:

- CI em todas as versões de Python suportadas;
- `ruff` para erros estáticos essenciais;
- `mypy` em modo estrito sobre o pacote;
- testes determinísticos e build do pacote em pull requests;
- CodeQL para análise estática de segurança;
- Dependabot para dependências Python e GitHub Actions;
- GitHub Actions fixadas por SHA imutável nos workflows mantidos pelo projeto;
- smoke tests independentes contra fontes públicas reais;
- `suzano integridade` para destacar domínios externos não reconhecidos em fontes selecionadas.

Nenhum desses controles, isoladamente, é tratado como prova de segurança absoluta. Eles existem para reduzir risco e tornar falhas observáveis.

## Integridade de fontes públicas

A verificação de integridade documentada em [`docs/integridade.md`](docs/integridade.md) não é um detector de invasão. Ela registra sinais verificáveis — por exemplo, um domínio externo não reconhecido — para revisão humana.

Não abra um incidente público acusando um órgão ou terceiro apenas com base em um achado automático do programa.

## Dependências e cadeia de CI

Dependências do aplicativo permanecem declaradas em `pyproject.toml`. Dependências de GitHub Actions usadas nos workflows oficiais são referenciadas por commit SHA e acompanhadas por comentário de versão para auditoria humana.

Atualizações de dependências devem passar pelas mesmas verificações automatizadas das demais mudanças.
