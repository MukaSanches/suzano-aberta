# Limitações conhecidas

O Suzano Aberta prioriza rastreabilidade e comportamento observável. Algumas limitações são técnicas; outras são escolhas deliberadas para evitar transformar lacunas ou correlações em afirmações maiores do que os dados sustentam.

## Cobertura

A cobertura depende do que cada fonte publica, da estrutura exposta e da disponibilidade observada. Um portal temporariamente indisponível, uma paginação incompleta ou uma mudança de HTML podem reduzir a coleta daquela execução.

O projeto não afirma possuir uma cópia completa de toda informação pública relacionada a Suzano.

## Fontes com autenticação ou bloqueio

Serviços que exigem autenticação, sessão privada ou acesso não documentado não são silenciosamente contornados para serem tratados como APIs públicas. A descoberta histórica pode utilizar índices públicos independentes quando isso é compatível com a metodologia documentada.

## Documentos

Arquivos textuais suportados podem ter conteúdo extraído para pesquisa. PDFs digitalizados sem camada de texto não passam por OCR automático no núcleo atual. Arquivos muito grandes podem ser catalogados sem extração integral quando ultrapassam limites de segurança.

## Interpretação

O projeto indexa e relaciona evidências publicadas; ele não fornece parecer jurídico, não determina legalidade, não atribui intenção e não classifica automaticamente conduta política ou administrativa.

Um CNPJ observado em um registro significa que o identificador aparece naquela evidência. Isso, sozinho, não prova pagamento, propriedade, responsabilidade, sociedade ou irregularidade.

## Ausência não é revogação

Se um registro deixa de aparecer temporariamente em uma página, o sistema não presume automaticamente que ele foi cancelado, revogado, excluído ou retirado de forma intencional. Falhas de fonte e mudanças de paginação existem.

## Busca

FTS5 é adequado ao objetivo local-first e permite pesquisa rápida sem infraestrutura externa. Ele não pretende reproduzir todas as capacidades linguísticas ou de ranking de um mecanismo distribuído especializado. Quando FTS5 não está disponível, existe um fallback com menos recursos.

## Relações

A resolução de entidades é conservadora. Identificadores fortes têm precedência; similaridade vaga de nomes não é tratada automaticamente como identidade. Novas regras relacionais precisam preservar a evidência que sustenta cada associação.

## Snapshot

O snapshot rolling representa o acervo validado publicado naquele momento. Ele pode evoluir sem alterar a versão da API. Para trabalhos reproduzíveis, registre a versão do pacote e a geração/data do dataset utilizada.

## Segurança

CI, CodeQL, limites de rede, validação de snapshot e outros controles reduzem risco, mas não constituem certificação formal. Uma implantação pública continua dependendo de controles da infraestrutura, como TLS, rate limiting, logs, backups e política de rede.

## Série 0.x

A biblioteca ainda está na série `0.x`. Interfaces podem evoluir, desde que mudanças relevantes sejam documentadas, testadas e registradas no `CHANGELOG.md`.

Esses limites não são escondidos pelo produto: a intenção é deixar claro o que foi observado, de onde veio e até onde a evidência permite concluir.
