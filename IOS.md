# Suzano Aberta no iPhone e iPad

O Suzano Aberta possui duas formas de uso em dispositivos Apple:

1. **Web App instalável**, disponível publicamente sem taxa de distribuição;
2. **wrapper nativo iOS/iPadOS**, mantido no repositório e validado automaticamente no GitHub Actions.

O projeto continua sendo cívico e independente. O aplicativo não é um canal oficial da Prefeitura de Suzano, Câmara Municipal, CPTM, mandato, partido ou candidatura.

## Instalação pública sem App Store

No iPhone ou iPad:

1. abra o Safari;
2. acesse `https://mukasanches.github.io/suzano-aberta/app/`;
3. toque em **Compartilhar**;
4. escolha **Adicionar à Tela de Início**;
5. confirme a adição.

O Suzano Aberta passa a aparecer na Tela de Início e abre como uma experiência de aplicativo, usando a mesma interface e os mesmos dados publicados pelo projeto.

Essa é a forma recomendada enquanto o projeto não estiver distribuído de forma nativa pela App Store ou TestFlight.

## App nativo

O código está em:

```text
mobile/ios/
```

Arquitetura principal:

```text
SwiftUI
  ↓
WKWebView
  ↓
https://mukasanches.github.io/suzano-aberta/app/
  ↓
mesma infraestrutura pública do portal
```

Se a camada remota falhar, a versão empacotada da shell móvel pode ser usada como fallback local.

Configuração atual:

```text
bundle id: br.com.suzanoaberta.app
deployment target: iOS 16.0
família: iPhone + iPad
projeto: XcodeGen
interface: web/app
```

## Segurança do wrapper

O wrapper nativo:

- usa HTTPS para a origem remota;
- mantém o host `mukasanches.github.io` como origem interna confiável;
- entrega links externos ao sistema;
- não permite JavaScript abrir janelas automaticamente;
- mantém reprodução de mídia sujeita a ação do usuário;
- usa a mesma política de dados e independência do Web App;
- não exige conta do usuário para funcionar.

## Atualização

A maior parte do conteúdo e da interface é atualizada pelo Web App publicado no GitHub Pages. Isso permite que correções compatíveis, dados novos e melhorias da interface cheguem ao iPhone sem exigir uma nova instalação nativa.

Mudanças no próprio wrapper Swift, permissões, recursos nativos ou metadados do pacote continuam exigindo uma nova build nativa.

## Build automatizado

O workflow está em:

```text
.github/workflows/ios-app.yml
```

A automação:

1. valida `web/app/app.js` e `web/app/sw.js`;
2. executa `tests/mobile-app.test.mjs`;
3. instala XcodeGen no runner macOS;
4. gera `SuzanoAberta.xcodeproj`;
5. compila com `xcodebuild` para iOS Simulator;
6. empacota `SuzanoAberta.app` em builds da `main`;
7. publica o pacote como artifact do GitHub Actions.

## Build local no macOS

Requisitos:

- macOS;
- Xcode;
- XcodeGen.

```bash
cd mobile/ios
xcodegen generate
xcodebuild \
  -project SuzanoAberta.xcodeproj \
  -scheme SuzanoAberta \
  -configuration Debug \
  -destination "generic/platform=iOS Simulator" \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  clean build
```

## Por que o artifact do GitHub não instala diretamente em qualquer iPhone?

O artifact gerado pelo workflow atual é compilado para **iOS Simulator**. Ele serve para provar que o projeto gera e compila corretamente em ambiente Apple, mas não é um pacote de distribuição para aparelhos físicos.

Para distribuir o aplicativo nativo em iPhones reais é necessário um fluxo de assinatura e provisionamento Apple. A estratégia futura pode usar:

- Xcode com assinatura para desenvolvimento;
- TestFlight para testes distribuídos;
- App Store para distribuição pública ampla.

Até esse canal existir, a instalação pública recomendada continua sendo o Web App pela Tela de Início.

## Relação com Android e Web

Não existem três produtos independentes. Existe uma infraestrutura comum com diferentes superfícies:

```text
                  ┌─ Portal
Suzano Aberta ────┼─ Web App
                  ├─ Android
                  └─ iOS / iPadOS
```

A interface canônica do aplicativo fica em `web/app/`. Android e iOS acrescentam integração nativa e fallback local sem criar uma segunda base de dados.

## Links

- Portal: https://mukasanches.github.io/suzano-aberta/
- Web App: https://mukasanches.github.io/suzano-aberta/app/
- Repositório: https://github.com/MukaSanches/suzano-aberta
- Documentação móvel: `docs/mobile-app.md`
