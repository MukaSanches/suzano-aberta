# Metodologia de coleta

## Objetivo

O objetivo da coleta é transformar publicações públicas de Suzano em registros pesquisáveis e reproduzíveis sem alterar o significado do material de origem.

## Hierarquia de fontes

A ordem de preferência é:

1. dados estruturados publicados pelo próprio órgão, como CSV;
2. páginas institucionais oficiais;
3. documentos oficiais vinculados por essas páginas;
4. índices oficiais de publicações.

Fontes secundárias podem ser usadas para pesquisa do projeto, mas não entram como evidência de um registro da v0.1 quando existe uma fonte oficial equivalente.

## Requisições

A biblioteca usa um `User-Agent` identificável, timeout explícito, redirecionamentos controlados, intervalo mínimo entre chamadas e poucas tentativas. Não há coleta agressiva nem paralelismo irrestrito.

## Normalização

O parser remove apenas ruído de apresentação, como espaços repetidos. Datas brasileiras são convertidas para ISO (`AAAA-MM-DD`) quando puderem ser reconhecidas de forma determinística. Valores que não podem ser interpretados com segurança permanecem no formato publicado.

## Identificadores

Quando a fonte oferece número estável, ele compõe o ID interno. Quando não oferece, o projeto usa hash determinístico derivado de campos ou URL estáveis. O hash não é usado para atribuir autenticidade jurídica ao documento.

## Mudanças

Cada registro possui fingerprint calculado sobre o conteúdo normalizado, ignorando metadados voláteis de coleta. Uma nova observação com fingerprint diferente gera evento `alterado`. A ausência temporária de um item não é tratada automaticamente como exclusão na v0.1, pois páginas públicas podem falhar ou paginar de maneira incompleta.

## Falhas

Um coletor pode falhar sem impedir os demais. O relatório de coleta registra a fonte que falhou e a exceção observada. O comportamento esperado diante de HTML inesperado é produzir menos dados ou uma falha observável, nunca preencher campos por suposição.

## Validação

A validação ocorre em três níveis:

- testes unitários com fixtures pequenas e controladas;
- CI em múltiplas versões suportadas de Python;
- smoke tests periódicos contra fontes públicas reais, executados separadamente do CI determinístico.

## Reprodutibilidade

O banco local pode ser removido e reconstruído. Para trabalhos acadêmicos, jornalísticos ou de auditoria, recomenda-se guardar também o arquivo exportado e registrar a versão da biblioteca usada na coleta.
