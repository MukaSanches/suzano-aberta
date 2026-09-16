# Portal v11 — sistema cívico de interface

O Portal v11 reorganiza a experiência pública do Suzano Aberta em torno de tarefas, confiança verificável, acessibilidade, desempenho e funcionamento progressivo. Ele não tenta reproduzir a identidade visual de um governo e não altera a natureza do projeto: o Suzano Aberta continua sendo uma iniciativa cívica independente, sem se apresentar como portal oficial da Prefeitura ou da Câmara de Suzano.

## Referências estudadas

A camada foi desenhada a partir de padrões públicos documentados em design systems governamentais maduros, sem copiar marcas, brasões, tipografia proprietária ou identidade institucional.

- GOV.UK Design System — componentes acessíveis, navegação orientada a serviços, consistência e progressive enhancement: https://design-system.service.gov.uk/
- U.S. Web Design System (USWDS) — abordagem mobile-first, desempenho, componentes testados e experiência consistente entre serviços: https://designsystem.digital.gov/
- Singapore Government Design System (SGDS) — componentes plug-and-play, acessibilidade, padrões responsivos e sinais explícitos de confiança: https://www.designsystem.tech.gov.sg/
- Système de Design de l’État (França) — interfaces públicas simples, acessíveis, reconhecíveis e coerentes: https://www.systeme-de-design.gouv.fr/
- Suomi.fi Design System (Finlândia) — componentes reutilizáveis e requisitos de acessibilidade WCAG 2.2 A/AA: https://designsystem.suomi.fi/

## Decisões incorporadas

### 1. Navegação por tarefa

A página inicial começa pelo que a pessoa quer fazer: consultar uma lei, encontrar uma contratação, localizar um documento, acompanhar registros recentes ou verificar o estado do sistema. O usuário não precisa conhecer previamente a estrutura administrativa ou o nome da base de dados.

### 2. Busca como serviço central

A busca continua preservando a consulta digitada pelo usuário e usa o índice público já existente. Os atalhos de legislação, contratações, documentos e registros recentes reduzem passos sem criar uma segunda lógica de dados.

### 3. Confiança explícita

A faixa de independência permanece acima da navegação. A interface reforça que o Suzano Aberta facilita localização e leitura, enquanto a publicação mantida pelo órgão responsável continua sendo a referência oficial.

### 4. Estado operacional visível

A home exibe o estado da conexão, atalhos para a página de status, momento de geração do índice, contagens derivadas do snapshot e cadência das rotinas automáticas.

### 5. Acessibilidade configurável

A camada v11 adiciona controles locais de tamanho de texto, alto contraste e redução de movimento. As preferências são guardadas somente no navegador. O projeto mantém foco visível, skip link, HTML semântico e suporte a `prefers-reduced-motion`.

### 6. Local-first sem conta

Pesquisas recentes e preferências de leitura usam `localStorage`; não exigem login e não introduzem sincronização com servidor, cookies publicitários ou rastreadores externos.

### 7. PWA mais útil

O manifesto oferece atalhos para pesquisa, legislação, contratações e status. O service worker guarda o shell composto das camadas v4 e v11 e continua oferecendo o último conteúdo disponível em falhas de rede quando já houver cache.

### 8. Compatibilidade progressiva

A implementação preserva a antiga camada `portal-v4-core.css` e aplica `portal-v11` por cima, seguida de um arquivo mínimo de compatibilidade. Isso reduz o risco de regressões nas páginas especializadas que ainda possuem ajustes v5, v6, v7 e v8.

## Arquitetura visual

```text
styles.css
  ↓
portal-v4.css (entrypoint global)
  ├─ portal-v4-core.css   — comportamento visual preservado
  └─ portal-v11.css       — novo sistema cívico compartilhado
       ├─ portal-v11-core.css
       └─ portal-v11-compat.css

index.html
  └─ portal-v11.js        — preferências, histórico local, rede e instalação PWA
```

As páginas especializadas continuam podendo adicionar seus arquivos corretivos depois do entrypoint global.

## Contratos que não podem regredir

- identidade de projeto cívico independente sempre explícita;
- pesquisa sem reescrever silenciosamente o termo do usuário;
- legislação com mais recentes primeiro quando não há consulta textual;
- links de origem preservados;
- exatamente cinco notícias no feed público validado pelo pipeline;
- nenhuma dependência de analytics ou rastreadores para a interface funcionar;
- funcionamento sem JavaScript para conteúdo estrutural e navegação básica sempre que possível;
- controles acessíveis por teclado e movimento opcional.

## Gate automatizado

`tests/test_portal_v11.py` verifica composição das camadas, contratos da home, ausência de rastreadores introduzidos pela v11, atalhos do manifesto e assets obrigatórios do service worker. O validador histórico `scripts/check_web.py` continua sendo executado sem ser substituído.
