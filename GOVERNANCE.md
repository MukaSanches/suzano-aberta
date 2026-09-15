# Governança

Suzano Aberta é um projeto independente de infraestrutura cívica. O objetivo desta política é deixar claro como decisões técnicas, alterações de fontes e versões públicas são tratadas.

## Manutenção

O mantenedor atual é `@MukaSanches`.

O mantenedor é responsável por revisar mudanças de arquitetura, aceitar ou rejeitar contribuições, organizar versões e preservar o escopo apartidário do projeto.

## Princípios de decisão

As decisões seguem, nesta ordem, quatro critérios:

1. **correção** — um dado incorreto é pior do que um dado ausente;
2. **rastreabilidade** — registros devem manter o caminho até a publicação que os originou;
3. **reprodutibilidade** — comportamento importante deve ser coberto por testes determinísticos;
4. **simplicidade operacional** — a biblioteca deve continuar utilizável localmente sem infraestrutura desnecessária.

Novas funcionalidades não são aceitas apenas por aumentarem a quantidade de dados. Elas precisam ter fonte identificável, modelo compreensível e comportamento de falha observável.

## Alterações em coletores

Mudanças em parsers ou fontes devem informar:

- a URL oficial afetada;
- o que mudou na publicação original;
- como o novo comportamento foi validado;
- qual teste impede a mesma regressão no futuro.

Quando a estrutura da fonte for ambígua, o projeto prefere não preencher um campo a inferir um valor sem evidência suficiente.

## Mudanças de segurança e integridade

Relatos de vulnerabilidade seguem [`SECURITY.md`](SECURITY.md).

Regras de integridade devem ser determinísticas, documentadas e cuidadosas com linguagem. Um sinal técnico não deve ser apresentado como prova de irregularidade, comprometimento ou autoria.

## Pull requests

Alterações relevantes entram pela `main` por pull request sempre que possível. Antes do merge, o CI deve estar verde para as versões de Python suportadas e o pacote deve ser construído com sucesso.

Mudanças em workflows, coletores, metodologia ou integridade são áreas de revisão explícita definidas em `.github/CODEOWNERS`.

## Versões

A série `0.x` ainda pode evoluir interfaces. Cada versão publicada deve:

- atualizar o número do pacote de forma consistente;
- registrar mudanças relevantes no `CHANGELOG.md`;
- manter documentação compatível com o comportamento entregue;
- passar pelo conjunto de verificações automatizadas antes de chegar à `main`.

## Neutralidade institucional

O projeto não representa a Prefeitura, a Câmara, partidos, mandatos ou candidaturas. Dados públicos podem envolver agentes políticos, mas o software não deve produzir julgamento partidário ou atribuição automática de culpa.

Contribuições são avaliadas pela qualidade técnica e documental, independentemente de quem seja beneficiado ou criticado pelos dados observados.
