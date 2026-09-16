# Suzano Aberta — Automação segura do Instagram

Este documento define o que pode e o que não pode ser automatizado no perfil `@suzanoaberta` sem colocar a conta em risco desnecessário.

## Princípio

Preferir sempre integrações oficiais (Meta/Instagram API, Metricool e ferramentas autorizadas). Automação que exige senha do Instagram, cookies persistentes ou robôs que imitam cliques em produção não deve ser incorporada ao backend do Suzano Aberta.

## Matriz de automação

| Ação | Automação recomendada | Canal |
| --- | --- | --- |
| Publicar carrossel/feed | Sim | Metricool / Instagram API oficial |
| Agendar posts | Sim | Metricool |
| Publicar Stories | Sim, quando a conta/recurso permitir | Metricool / Instagram API oficial |
| Publicar Reels | Sim | Metricool / Instagram API oficial |
| Ler métricas | Sim | Metricool / API oficial |
| Responder comentários | Sim, conforme permissões | API oficial / ferramenta autorizada |
| Alterar bio | Não há endpoint público de escrita; usar interface do Instagram | Instagram Web/app ou sessão assistida por navegador |
| Alterar campo Nome | Interface do Instagram | Instagram Web/app ou sessão assistida por navegador |
| Alterar links do perfil | Interface do Instagram | Instagram Web/app; alguns links podem exigir app/mobile |
| Criar/editar Destaques | Interface do Instagram | Instagram Web/app |
| Alterar capa de Destaque | Interface do Instagram | Instagram Web/app |
| Alterar foto de perfil | Interface do Instagram | Instagram Web/app |

## Arquitetura operacional

### Camada A — 100% automatizável

Fluxo preferencial:

1. pesquisa e confirmação de fontes;
2. geração de copy e arte;
3. revisão editorial;
4. publicação/agendamento por Metricool;
5. coleta de métricas;
6. atualização da estratégia com dados reais.

### Camada B — perfil e Destaques

Essas ações não devem ser executadas por bot permanente de senha/cookie. O processo recomendado é uma sessão controlada na interface oficial do Instagram:

1. abrir `instagram.com` em uma sessão autenticada;
2. acessar **Editar perfil**;
3. aplicar os campos do `profile.json`;
4. salvar;
5. criar/editar Destaques com Stories previamente publicados;
6. aplicar as capas oficiais;
7. validar o perfil em desktop e celular.

Uma sessão de navegador assistida pode executar essa sequência como uma operação pontual. Ela não deve virar um scraper ou robô de crescimento.

## Configuração-alvo

- Username: `@suzanoaberta`
- Nome: `Suzano Aberta | Informação Pública`
- Bio:

```text
Informação pública de Suzano, organizada e rastreável.
Notícias, dados e fontes para entender a cidade.
Independente e apartidário.
↓ Acesse o portal
```

- Link principal: `https://mukasanches.github.io/suzano-aberta/`
- Categoria preferencial: categoria neutra de mídia/informação, se disponível.

## Destaques-alvo

Ordem:

1. `COMECE AQUI`
2. `NOTÍCIAS`
3. `CÂMARA`
4. `PREFEITURA`
5. `CONTRATOS`
6. `SERVIÇOS`
7. `FONTES`
8. `SOBRE`

Antes de criar os Destaques, publicar os Stories-base. Depois, adicionar cada Story ao Destaque correspondente e aplicar a capa oficial.

## Automação parcial dos Destaques

O conteúdo dos Destaques pode ser automatizado quase todo:

1. gerar os cards em 1080×1920;
2. publicar/agendar como Stories via Metricool;
3. aguardar publicação;
4. usar a interface oficial apenas para agrupá-los em Destaques e trocar as capas.

Isso reduz a parte manual a poucos cliques por Destaque sem depender de API não oficial.

## O que não implementar

Não adicionar ao projeto:

- bot que armazena usuário/senha do Instagram;
- automação de login com credenciais em texto;
- scraping de endpoints privados do app;
- bibliotecas que reproduzem APIs privadas do Instagram;
- auto-follow/unfollow;
- auto-like;
- comentários em massa;
- DMs frias em massa;
- compra ou fabricação de engajamento.

## Auditoria do perfil

Após qualquer alteração estrutural, conferir:

- bio cabe e não foi truncada;
- link abre corretamente;
- avatar continua legível no círculo pequeno;
- os primeiros Destaques aparecem na ordem esperada;
- capas estão centralizadas no recorte circular;
- três posts fixados cumprem apresentação, método e utilidade;
- o perfil deixa explícito que o projeto é independente;
- nenhum elemento visual sugere vínculo oficial com Prefeitura, Câmara, partido ou candidatura.

## Relação com a skill

A skill `skills/suzano-aberta-instagram/SKILL.md` deve respeitar este arquivo. Para publicação, usar integrações oficiais. Para alterações estruturais de perfil, produzir o estado-alvo e executar pela interface oficial em sessão controlada.