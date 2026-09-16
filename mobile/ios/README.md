# Suzano Aberta para iPhone e iPad

A versão iOS reutiliza a mesma interface móvel publicada em `web/app`, a mesma infraestrutura de dados e o mesmo modelo de atualização do restante do Suzano Aberta. O wrapper nativo é escrito em SwiftUI + WebKit e não mantém uma segunda cópia da lógica cívica.

## Como funciona

```text
fontes públicas
      ↓
Suzano Aberta Engine / datasets / API
      ↓
GitHub Pages /app
      ↓
WKWebView nativa no iOS
      ↓
fallback local empacotado no app
```

O app abre `https://mukasanches.github.io/suzano-aberta/app/` como origem principal. Links do próprio domínio permanecem no aplicativo; links externos são entregues ao sistema. Se a interface remota não puder ser carregada, o wrapper tenta abrir a cópia da shell web incluída no bundle.

## Instalação pública sem App Store

Qualquer pessoa pode usar a versão instalável da web no iPhone sem conta de desenvolvedor e sem pagar taxa:

1. Abra `https://mukasanches.github.io/suzano-aberta/app/` no Safari.
2. Toque em **Compartilhar**.
3. Toque em **Adicionar à Tela de Início**.
4. Ative **Abrir como App** quando essa opção estiver disponível.
5. Toque em **Adicionar**.

Isso cria o Suzano Aberta na Tela de Início e o abre em modo de aplicativo. É o caminho público gratuito enquanto não houver distribuição nativa assinada pela Apple.

## App nativo

O código nativo está neste diretório. Para gerar o projeto Xcode localmente:

```bash
brew install xcodegen
cd mobile/ios
xcodegen generate
open SuzanoAberta.xcodeproj
```

Para instalar o app nativo em um iPhone pessoal sem assinatura paga do Apple Developer Program, o próprio usuário pode assinar o projeto com sua Apple Account pelo Xcode. A Apple limita o provisionamento gratuito e exige renovação periódica; por isso um `.ipa` não assinado hospedado no GitHub não é instalável universalmente em iPhones comuns.

## Build automatizado

O workflow `iOS App`:

- valida a shell compartilhada;
- executa os testes móveis;
- gera o projeto com XcodeGen;
- compila em um runner macOS para iOS Simulator sem assinatura;
- publica o build de simulador como artifact do GitHub Actions em pushes para `main`.

O build de simulador serve para validação técnica e demonstração em simuladores. Distribuição nativa para aparelhos de terceiros exige uma modalidade de assinatura/distribuição aceita pela Apple.

## Segurança e privacidade

- apenas HTTPS é usado como origem remota;
- navegação externa sai do `WKWebView` para o sistema;
- JavaScript pode executar somente porque a interface móvel do projeto depende dele;
- janelas abertas por script são bloqueadas no WebKit e tratadas pelo delegate;
- nenhum SDK publicitário, rastreador de terceiros ou login obrigatório é adicionado pelo wrapper;
- favoritos e pesquisas salvas continuam sendo mantidos localmente pela interface móvel.
