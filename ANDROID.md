# Suzano Aberta para Android

[**Baixar o APK mais recente**](https://github.com/MukaSanches/suzano-aberta/releases/latest/download/suzano-aberta-android.apk)

O Suzano Aberta para Android é distribuído diretamente pelo GitHub Releases para que qualquer pessoa possa baixar e instalar o aplicativo sem precisar compilar o projeto.

## Requisitos

- Android 8.0 ou superior;
- arquitetura suportada pelo Android/WebView do aparelho;
- conexão com a internet para receber a versão mais recente da interface e dos dados;
- o APK também leva uma shell local como fallback para indisponibilidade de rede.

## Instalação

1. Abra a página de [Releases](https://github.com/MukaSanches/suzano-aberta/releases/latest).
2. Baixe `suzano-aberta-android.apk`.
3. Abra o arquivo no celular.
4. Se o Android pedir autorização para instalar aplicativos vindos do navegador ou do gerenciador de arquivos, autorize somente essa fonte.
5. Toque em **Instalar**.
6. Depois da instalação, a autorização de “fontes desconhecidas” pode ser desativada novamente.

O Android pode exibir um aviso porque o aplicativo é instalado fora da Play Store. Não é necessário desativar o Google Play Protect.

## Como conferir o arquivo

Cada release publica três arquivos:

- `suzano-aberta-android.apk` — aplicativo instalável;
- `suzano-aberta-android.sha256` — hash SHA-256 do APK;
- `suzano-aberta-android-signature.txt` — certificado detectado pelo `apksigner` durante a build.

No Windows, o SHA-256 pode ser conferido com:

```powershell
Get-FileHash .\suzano-aberta-android.apk -Algorithm SHA256
```

No Linux/macOS:

```bash
sha256sum suzano-aberta-android.apk
```

O valor precisa coincidir com `suzano-aberta-android.sha256` do mesmo release.

## Atualizações

O wrapper Android é **remote-first**. A maior parte das mudanças de interface e conteúdo chega pela versão publicada em GitHub Pages, portanto normalmente não exige reinstalar o APK.

Uma nova versão nativa é publicada quando `versionName` e `versionCode` do projeto Android são incrementados. O workflow impede sobrescrever silenciosamente um release nativo já publicado com a mesma versão.

## Assinatura do APK

O pipeline já aceita assinatura de produção por GitHub Actions Secrets:

```text
ANDROID_KEYSTORE_BASE64
ANDROID_KEYSTORE_PASSWORD
ANDROID_KEY_ALIAS
ANDROID_KEY_PASSWORD
```

Se esses secrets não estiverem configurados, a build pública usa a assinatura de desenvolvimento do Android para produzir um APK instalável. Isso é suficiente para instalação direta, mas não deve ser confundido com a chave definitiva de produção da Play Store. Até uma chave de release estável ser configurada, uma futura mudança nativa de assinatura pode exigir desinstalar a versão anterior antes de instalar a nova.

A chave privada de produção nunca deve ser versionada no repositório.

## Build automatizada

O workflow [`.github/workflows/android-app.yml`](.github/workflows/android-app.yml):

1. valida JavaScript e testes da interface móvel;
2. sincroniza a shell offline empacotada;
3. executa Android Lint para a variant Release;
4. compila o APK Release otimizado;
5. verifica a assinatura com `apksigner`;
6. gera SHA-256;
7. mantém um artifact de CI por 90 dias;
8. publica o APK e os arquivos de verificação em GitHub Releases quando a build parte da `main`.

## Código Android

O projeto nativo fica em [`mobile/android/`](mobile/android/).

Parâmetros atuais:

```text
applicationId: br.com.suzanoaberta.app
minSdk: 26
targetSdk: 36
compileSdk: 36
versionName: 1.0.0
versionCode: 1
JDK: 17
Gradle: 9.6
AGP: 9.4
```

## Segurança

O aplicativo bloqueia HTTP em claro, mixed content e cookies de terceiros na WebView. Links externos são abertos no navegador do sistema. O código de distribuição é público e cada APK publicado pode ser conferido por hash e certificado.

O Suzano Aberta é um projeto cívico independente e não é um aplicativo oficial da Prefeitura de Suzano, da Câmara Municipal de Suzano ou da CPTM.
