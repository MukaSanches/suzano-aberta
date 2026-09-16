# Linha 11–Coral em tempo real

O módulo de mobilidade do Suzano Aberta acompanha a Linha 11–Coral com foco em **Calmon Viana, Suzano, Jundiapeba e Estudantes**. A regra central é simples: o portal só publica um estado operacional quando uma fonte oficial o expõe de forma identificável. Ausência de dado não é convertida em “operação normal”.

## Fontes oficiais validadas

### CPTM — Situação das Linhas

- Página atual: `https://www.cptm.sp.gov.br/cptm`
- Página oficial legada usada como fallback de compatibilidade: `https://www.cptm.sp.gov.br/Pages/Home.aspx?origem=menu`
- Uso: leitura conservadora do bloco “Situação das Linhas”. O parser exige referência explícita a **CORAL** ou **Linha 11-Coral** e um rótulo operacional conhecido.
- Se a página informar `Atualizado em`, o horário é preservado. Se não informar, o backend registra apenas o horário em que a fonte foi consultada.

### CPTM — Comunicado de Ocorrências

- Endpoint oficial observado para download de um comunicado já identificado: `https://api.cptm.sp.gov.br/AppCPTM/v1/Ocorrencias/Baixar?id=<id>`
- Uso no Suzano Aberta: **documental/histórico somente**.
- Limite: não foi localizada documentação pública oficial de um endpoint de listagem em tempo real que permita descobrir IDs atuais. Por isso o módulo não inventa um endpoint de busca e não usa esse download como feed ao vivo.

### ARTESP — API Trilhos

- Documentação: `https://ccm.artesp.sp.gov.br/metroferroviario/api/docs/`
- Status: `GET https://ccm.artesp.sp.gov.br/metroferroviario/api/status/`
- Ocorrências: `GET https://ccm.artesp.sp.gov.br/metroferroviario/api/ocorrencias/?data_inicio=YYYY-MM-DD&data_fim=YYYY-MM-DD`
- Autenticação: cabeçalho `Authorization: Api-Key <chave>`.
- Limite documentado: 12 requisições por hora por credencial; a própria ARTESP recomenda cache local e polling de no máximo uma chamada a cada cinco minutos.
- Mudança de escopo: desde **03/09/2026**, a documentação declara que a API expõe apenas linhas sob fiscalização e regulação direta da ARTESP. O código, portanto, não presume que a Linha 11 está presente: baixa a coleção oficial e procura `codigo == "11"` ou nome explícito da linha.

### ARTESP — Status público

- Página: `https://ccm.artesp.sp.gov.br/metroferroviario/status-linhas/`
- Uso: fallback sem credencial, somente se a própria página trouxer explicitamente a Linha 11 e um estado reconhecido.

## Ordem de consulta

1. CPTM — Situação das Linhas.
2. ARTESP — fonte autenticada quando `SUZANO_ARTESP_API_KEY` estiver configurada; sem chave, página pública oficial.
3. Último estado válido em cache, marcado como `stale`.
4. Sem dado válido, resposta `availability: "unavailable"` e campos de ocorrência/motivo/trecho ficam nulos.

A ARTESP pode complementar uma alteração encontrada na CPTM com descrição de ocorrência somente quando a própria resposta oficial contiver a Linha 11.

## Cache e proteção das fontes

- Cache público do módulo: 90 segundos por padrão.
- Cache da ARTESP: 600 segundos por padrão, reduzindo risco de exceder o limite oficial.
- Janela de último estado válido: 1800 segundos por padrão; qualquer uso desse dado é marcado como desatualizado.
- Timeout de fonte: 8 segundos por padrão.
- A chave da ARTESP existe somente no backend; nunca é enviada ao navegador.

Variáveis: `SUZANO_ARTESP_API_KEY`, `SUZANO_TRANSIT_CACHE_SECONDS`, `SUZANO_TRANSIT_STALE_SECONDS`, `SUZANO_ARTESP_CACHE_SECONDS` e `SUZANO_TRANSIT_TIMEOUT_SECONDS`.

## Endpoint do Suzano Aberta

`GET /v1/transit/line-11`

A resposta expõe `availability`, `status`, `operation_normal`, `occurrence`, `affected_segment`, `reason`, `source_updated_at`, `checked_at`, `source`, `secondary_source`, `source_errors`, `verified_sources` e `cache`.

O frontend lê `web/config.json` para descobrir `api_base`. Se o backend não estiver configurado naquele ambiente, a interface informa indisponibilidade em vez de consultar endpoints oficiais diretamente e expor credenciais.
