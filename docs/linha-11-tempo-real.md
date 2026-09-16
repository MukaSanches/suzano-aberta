# Linha 11–Coral — estimativa por notícias

O módulo de mobilidade do Suzano Aberta acompanha a **Linha 11–Coral** com foco em **Calmon Viana, Suzano, Jundiapeba e Estudantes** por meio de notícias recentes. Ele não consulta uma API operacional da CPTM ou da ARTESP e não se apresenta como telemetria em tempo real.

## Objetivo

Transformar notícias recentes em um indicador simples para o cidadão, preservando as manchetes que sustentam a leitura e deixando claro o grau de incerteza.

O indicador usa quatro estados:

- **verde** — não há alerta operacional recente nas manchetes consultadas, ou uma notícia posterior informou retomada/normalização;
- **amarelo** — há alteração recente, ocorrência ainda sem confirmação posterior de normalização ou incerteza temporal;
- **vermelho** — há manchete recente indicando interrupção, falha, pane, suspensão ou problema operacional;
- **cinza** — a busca de notícias falhou ou a estimativa publicada ficou desatualizada.

## Fonte de descoberta

O gerador `scripts/build_line11_news_status.py` usa o feed público do **Google News RSS**, por meio da infraestrutura de descoberta já existente no projeto (`WebDiscovery.discover_news`). As consultas são específicas para:

- Linha 11–Coral / CPTM;
- Linha 11 / Coral / CPTM;
- Linha 11–Coral / Suzano;
- Estação Suzano;
- Calmon Viana;
- Jundiapeba;
- Estudantes + Linha 11.

O feed de descoberta não transforma uma matéria em fonte oficial. Cada evidência preserva título, veículo, data e link encontrado para que o usuário possa conferir a publicação original.

## Regra de decisão

A classificação é feita sobre as manchetes, não sobre inferências escondidas:

1. manchetes de retomada, normalização ou operação normal têm prioridade sobre referências ao problema anterior;
2. uma interrupção noticiada nas últimas 6 horas gera **vermelho**;
3. uma interrupção mais antiga, sem notícia posterior de normalização, gera **amarelo**;
4. manutenção, restrição, velocidade reduzida, maiores intervalos ou alteração geram **amarelo**;
5. se não houver manchete operacional negativa recente, o painel fica **verde**, mas informa confiança baixa quando não existe confirmação positiva de normalização;
6. se a descoberta de notícias falhar, o painel fica **cinza** e não inventa um estado.

Matérias claramente contextuais sobre contrato, concessão, ressarcimento, investimento ou gestão não são tratadas automaticamente como uma falha atual só porque mencionam uma pane passada.

## Atualização e cache

O workflow `Portal público` roda a cada **30 minutos** e gera `web/data/line11-news-status.json`. O navegador lê esse arquivo estático do próprio GitHub Pages, sem depender do backend da API do Suzano Aberta.

O arquivo informa `generated_at` e `stale_after_minutes`. O cliente considera a estimativa desatualizada após 90 minutos sem nova geração e muda a apresentação para estado de cautela.

## Transparência

O JSON público contém:

- estado e cor calculados;
- nível de confiança;
- resumo da evidência mais recente;
- trecho citado, quando identificável;
- motivo provável extraído da manchete;
- lista das notícias usadas;
- veículos encontrados;
- quantidade de registros pesquisados;
- horário de geração;
- aviso metodológico.

## Limitação principal

**Verde não significa “CPTM confirmou operação normal neste minuto”.** Significa que, dentro da janela monitorada, não foi encontrada uma manchete operacional negativa mais recente do que uma normalização, ou que não surgiu alerta recente nas fontes jornalísticas consultadas.

Para decisões de viagem, o usuário deve conferir também os canais oficiais da operadora responsável.
