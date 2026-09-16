# Suzano Aberta App

O Suzano Aberta App é a interface móvel do projeto cívico independente Suzano Aberta. Ele não cria uma segunda base de dados: reutiliza a mesma infraestrutura pública, rastreável e verificável do portal.

## Download Android

A distribuição pública para Android fica em **GitHub Releases**.

- APK direto: https://github.com/MukaSanches/suzano-aberta/releases/latest/download/suzano-aberta-android.apk
- Releases: https://github.com/MukaSanches/suzano-aberta/releases
- Guia de instalação: [`ANDROID.md`](../ANDROID.md)

O usuário final não precisa abrir o GitHub Actions nem compilar o projeto.

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

Cada release público inclui o APK, um SHA-256 e o certificado reportado pelo `apksigner` durante a build.

## Compatibilidade Android

A versão 1.0 compila e mira Android 16 (API 36), atendendo ao requisito vigente para novos aplicativos enviados ao Google Play desde 31 de agosto de 2026. O projeto usa AGP 9.4, Gradle 9.6 e JDK 17. O mínimo suportado é Android 8.0 / API 26.

## Build e publicação

O workflow `Android App`:

1. valida a shell e executa os testes;
2. sincroniza o fallback local;
3. executa Android Lint na variant Release;
4. compila um APK Release otimizado;
5. verifica a assinatura com `apksigner`;
6. gera SHA-256;
7. mantém artifact de CI;
8. publica a versão em GitHub Releases quando a build vem da `main`.

A tag de distribuição segue `android-v<versionName>`. Um release já publicado não é silenciosamente substituído por outro commit com a mesma versão; para uma nova versão nativa, `versionName` e `versionCode` devem ser incrementados.

## Assinatura

O pipeline está preparado para uma chave de produção armazenada fora do repositório por GitHub Actions Secrets:

```text
ANDROID_KEYSTORE_BASE64
ANDROID_KEYSTORE_PASSWORD
ANDROID_KEY_ALIAS
ANDROID_KEY_PASSWORD
```

Sem esses secrets, a build direta usa a assinatura de desenvolvimento do Android para produzir um APK instalável. Para distribuição definitiva em loja e atualizações nativas garantidas no mesmo pacote, deve ser usada uma chave de release estável e privada.
