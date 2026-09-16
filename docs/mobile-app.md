# Suzano Aberta App

O Suzano Aberta App é a interface móvel do projeto cívico independente Suzano Aberta. Ele não cria uma segunda base de dados: reutiliza a mesma infraestrutura pública, rastreável e verificável do portal.

## Arquitetura

```text
fontes públicas
      ↓
Suzano Aberta Engine
      ↓
snapshot / datasets / API
      ↓
GitHub Pages /app
      ↓
Android WebView endurecida
      ↓
fallback local empacotado no APK
```

A interface remota permite receber melhorias compatíveis e conteúdo novo sem reinstalar o APK. Se a página remota não puder ser aberta, o aplicativo mantém uma shell local empacotada como último recurso.

A operação normal não depende do ChatGPT. Atualização de conteúdo, validação de dados, publicação do portal e compilação são automatizadas por código e GitHub Actions.

## Resiliência

- sincronização ao abrir, voltar ao primeiro plano, recuperar conexão e periodicamente enquanto o app está visível;
- service worker para a interface e dados consultados;
- API consultiva quando configurada;
- fallback para o índice estático publicado quando a API falha;
- shell local embutida no APK para falha total de rede;
- favoritos e pesquisas salvas exclusivamente no armazenamento local;
- nenhuma conta obrigatória, publicidade ou cookie de terceiros.

## Segurança

O wrapper Android bloqueia tráfego HTTP em claro, mixed content e cookies de terceiros. Domínios externos são enviados ao navegador do sistema em vez de permanecerem dentro da WebView. Dependências de GitHub Actions são fixadas por commit para reduzir risco de supply chain.

## Compatibilidade Android

A versão 1.0 compila e mira Android 16 (API 36), atendendo ao requisito vigente para novos aplicativos enviados ao Google Play desde 31 de agosto de 2026. O projeto usa AGP 9.4, Gradle 9.6 e JDK 17.

## Build Android

O workflow `Android App` valida a shell, executa os testes, sincroniza o fallback local, roda Android Lint e compila um APK debug instalável como artifact do GitHub Actions.

Para publicação futura na Play Store, a mesma base pode produzir um Android App Bundle assinado; a chave de assinatura deve ser guardada fora do repositório.
