# Autopilot do portal

O Autopilot é a camada operacional que mantém o Suzano Aberta renovado sem depender de edição manual ou de um serviço de IA. Ele combina rotinas agendadas, fontes públicas, validação determinística e publicação baseada no último snapshot considerado íntegro.

## Princípio

Automação não substitui proveniência. O sistema pode decidir **quando coletar, como ordenar, como deduplicar e quais recortes exibir**, mas não inventa fatos, não cria conclusões políticas e não transforma ausência de dados em certeza.

A fonte responsável pela publicação continua sendo a referência final.

## Cadências

| Rotina | Frequência | Função |
| --- | --- | --- |
| Portal público | 30 minutos | recompõe busca estática, notícias, briefing e artefato do GitHub Pages |
| Mesa de notícias | 30 minutos | consulta Prefeitura e descoberta web, deduplica, classifica e escolhe cinco manchetes |
| Rolling refresh | 4 horas | atualiza APIs de compras e descoberta incremental, valida e substitui o snapshot rolling |
| Índice completo | diária | refaz documentos, legislação, PNCP, Compras.gov e descoberta profunda |
| Saúde de fontes | 6 horas | executa smoke tests contra integrações externas |

Os horários são UTC no GitHub Actions; a frequência, e não um horário civil específico, é o contrato principal.

## Último estado válido

Uma fonte externa não pode apagar um portal saudável.

O fluxo de dados segue esta regra:

1. baixa o último `data-latest` publicado;
2. confere SHA-256 e `PRAGMA quick_check`;
3. trabalha em uma cópia candidata;
4. executa coleta incremental;
5. verifica integridade, FTS, cobertura mínima e queda anormal de registros;
6. somente então substitui os assets do release;
7. dispara a reconstrução do GitHub Pages.

Se qualquer gate falhar, o snapshot anterior continua sendo servido.

## Mesa automática de notícias

`scripts/build_news_feed.py` não é um gerador de texto. Ele organiza publicações existentes.

O algoritmo:

- consulta notícias da Prefeitura;
- faz descoberta web com consultas temáticas sobre Suzano;
- usa o próprio snapshot como fallback quando a coleta ao vivo está degradada;
- exige referência explícita a Suzano;
- classifica itens por temas como mobilidade, saúde, educação, obras, emprego, segurança, cultura, esporte e meio ambiente;
- elimina títulos muito semelhantes por interseção de tokens;
- limita a quantidade de manchetes por publicador;
- prioriza atualidade, relevância local e disponibilidade de contexto;
- publica exatamente cinco manchetes para manter compatibilidade com o contrato visual existente.

O JSON resultante informa também quantidade de publicadores, temas, itens institucionais e se houve degradação parcial de alguma origem.

## Pulso da cidade

`scripts/build_autopilot_digest.py` lê o snapshot SQLite e produz `web/data/autopilot.json`.

O arquivo contém, entre outros dados:

- quantidade de registros e fontes;
- registros datados nos últimos 7 e 30 dias;
- legislação datada nos últimos 30 dias;
- contratações datadas nos últimos 30 dias;
- itens recentes do acervo;
- radar legislativo;
- radar de contratações;
- fontes e temas mais presentes.

Esses números descrevem o acervo atual. Eles não afirmam que um registro foi criado ou alterado recentemente apenas porque sua data documental é recente.

## Incidentes automáticos

As rotinas `Autonomous rolling refresh` e `Live source smoke tests` possuem mecanismo de incidente:

- uma falha abre um issue técnico, ou adiciona uma atualização ao incidente já aberto;
- o issue informa o run que falhou;
- o último snapshot válido permanece disponível;
- quando a rotina volta a passar, o próprio workflow comenta a recuperação e fecha o incidente.

Isso cria memória operacional sem exigir acompanhamento manual constante.

## Gates de publicação

O portal só é publicado depois de validar, no mínimo:

- checksum e integridade SQLite;
- índice de busca estático;
- coleções de detalhes e relações;
- links oficiais de contratações;
- feed de notícias com cinco itens e diversidade mínima de fontes;
- briefing Autopilot com cobertura, radar legislativo e radar de contratações;
- sintaxe dos JavaScript publicados;
- estrutura HTML e PWA;
- Data API derivada do snapshot.

`tests/test_autonomous_portal.py` cobre as regras determinísticas principais, enquanto `scripts/check_autopilot.py` valida o artefato web efetivamente gerado.

## Transparência

O objetivo visual é entregar a consistência que normalmente exigiria uma equipe dedicada, mas a metodologia não deve fingir trabalho humano que não aconteceu. O portal identifica-se como projeto independente e a documentação deixa explícito onde há automação.
