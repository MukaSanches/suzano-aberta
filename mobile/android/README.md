# Android — Suzano Aberta

Aplicativo Android do Suzano Aberta.

## Download para usuários

Quem só quer instalar o app **não precisa compilar este diretório**.

- [Baixar o APK mais recente](https://github.com/MukaSanches/suzano-aberta/releases/latest/download/suzano-aberta-android.apk)
- [Ver todos os Releases](https://github.com/MukaSanches/suzano-aberta/releases)
- [Guia completo de instalação](../../ANDROID.md)

## Estrutura

```text
mobile/android/
├─ app/
│  ├─ build.gradle
│  ├─ proguard-rules.pro
│  └─ src/main/
│     ├─ AndroidManifest.xml
│     ├─ java/br/com/suzanoaberta/app/MainActivity.java
│     └─ res/
├─ build.gradle
├─ gradle.properties
└─ settings.gradle
```

## Build local

Requer JDK 17, Android SDK 36, Build Tools 36.0.0 e Gradle 9.6.

```bash
cd mobile/android
gradle :app:lintRelease :app:assembleRelease
```

APK gerado:

```text
app/build/outputs/apk/release/app-release.apk
```

## Distribuição pública

O pipeline em [`../../.github/workflows/android-app.yml`](../../.github/workflows/android-app.yml) produz um APK Release, calcula SHA-256, verifica o certificado e publica a versão em GitHub Releases.

O nome público é sempre:

```text
suzano-aberta-android.apk
```

A tag segue:

```text
android-v<versionName>
```

Exemplo:

```text
android-v1.0.0
```

Para publicar uma nova versão nativa, incremente `versionName` e `versionCode` em `app/build.gradle`. Mudanças remotas na interface e nos dados normalmente não exigem um novo APK.

## Assinatura

O workflow aceita uma chave privada de release fornecida exclusivamente por GitHub Actions Secrets. Se ela não estiver configurada, a build usa a assinatura de desenvolvimento do Android para manter o APK diretamente instalável.

Nunca adicione um keystore privado ao repositório.
