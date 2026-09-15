# Metodologia de coleta

## Objetivo

O objetivo da coleta é transformar publicações públicas relacionadas a Suzano em registros pesquisáveis e reproduzíveis sem alterar o significado do material de origem e sem esconder de onde cada informação veio.

## Hierarquia de evidência

Sempre que possível, o projeto prefere a fonte mais próxima da publicação original:

1. dados estruturados publicados pelo órgão responsável ou por uma API pública oficial;
2. páginas institucionais oficiais;
3. documentos oficiais vinculados por essas páginas;
4. índices oficiais de publicações;
5. índices públicos de preservação, quando o objetivo é localizar referências históricas e a origem dessa referência permanece explícita.

Fontes secundárias podem apoiar descoberta e pesquisa do projeto, mas não substituem silenciosamente uma fonte primária quando existe uma publicação oficial equivalente.

## Independência das fontes

Coletores são independentes. Uma falha na Prefeitura, Câmara, PNCP, Compras.gov.br ou em qualquer outro upstream não deve apagar registros válidos obtidos de fontes que concluíram com sucesso.

Confirmações independentes podem coexistir. Deduplicação técnica não deve apagar proveniência útil apenas porque dois registros parecem descrever o mesmo evento.

## Requisições

A biblioteca usa um `User-Agent` identificável, timeout explícito, limites de tamanho, redirecionamentos controlados, frequência limitada e retry apenas para falhas transitórias conhecidas. Destinos de rede e redirects são tratados como entrada não confiável.

A descoberta web respeita as fronteiras de host configuradas e `robots.txt` onde aplicável. O objetivo não é maximizar requisições; é ampliar cobertura de forma previsível e auditável.

## Normalização

Parsers removem ruído de apresentação quando isso pode ser feito de forma determinística. Datas brasileiras podem ser convertidas para ISO (`AAAA-MM-DD`) quando reconhecidas com segurança. Valores ambíguos permanecem no formato publicado em vez de serem completados por suposição.

Detalhes específicos de uma fonte ficam em `attributes`; campos compartilhados usam o modelo tipado `PublicRecord`.

## Identificadores

Quando uma fonte oferece um identificador público estável — como número de processo, controle PNCP, CNPJ ou outra chave documentada — ele deve ser preferido para relações determinísticas.

Quando não existe identificador apropriado, IDs internos podem utilizar hashes determinísticos derivados de campos ou URLs estáveis. Um hash interno não atribui autenticidade jurídica ao documento.

## Fingerprints e mudanças

O fingerprint de um registro considera conteúdo canônico e ignora metadados operacionais que mudam a cada coleta. Uma nova observação do mesmo ID com fingerprint diferente pode gerar evento `alterado`.

A ausência temporária de um item não é tratada automaticamente como revogação, exclusão ou cancelamento: páginas públicas podem falhar, bloquear automação, alterar paginação ou responder de forma incompleta.

## Documentos

Arquivos públicos reconhecidos podem ser catalogados e, nos formatos suportados, ter texto extraído para pesquisa local. Limites de tamanho protegem a execução. Um arquivo pode permanecer catalogado mesmo quando a extração integral não é apropriada.

PDFs sem camada de texto não recebem OCR automático no núcleo atual.

## Relações e entidades

A camada de entidades é derivada e deve preservar a evidência que sustenta cada menção. Identificadores fortes têm precedência sobre semelhança textual. O projeto não funde pessoas ou organizações apenas porque nomes se parecem.

## Falhas

Falhas devem ser observáveis. O comportamento esperado diante de HTML inesperado, API indisponível ou documento inválido é registrar a falha e produzir menos dados — nunca inventar campos para manter uma contagem artificial.

Quando um workflow reutiliza um snapshot anterior porque uma fonte está temporariamente indisponível, essa decisão precisa ser explícita na automação e não confundida com uma coleta nova bem-sucedida.

## Validação

A validação é distribuída entre:

- testes determinísticos com fixtures pequenas e controladas;
- compilação e análise estática;
- `mypy` em modo estrito;
- CI em todas as versões de Python suportadas;
- build e instalação do pacote gerado;
- build do container da API;
- CodeQL e atualização automatizada de dependências;
- smoke tests contra fontes públicas reais, executados separadamente dos testes unitários;
- validação de checksum, cabeçalho e integridade SQLite antes da promoção de snapshots.

## Reprodutibilidade

Para uma análise reproduzível, registre no mínimo a versão do pacote, a geração/data do snapshot e os filtros ou consulta utilizados. Em trabalhos de longa duração, guarde também o snapshot ou exportação correspondente, porque o conjunto rolling continua evoluindo.

A publicação original permanece a referência para interpretação do conteúdo; o Suzano Aberta fornece uma camada técnica de acesso, preservação e consulta.
