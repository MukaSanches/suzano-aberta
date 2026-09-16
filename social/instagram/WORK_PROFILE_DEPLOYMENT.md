# Implantação do perfil do Suzano Aberta via navegador

Este arquivo é um roteiro de execução para uma sessão controlada de navegador no Instagram Web. Ele não deve ser transformado em bot persistente.

## Pré-condições

- estar autenticado na conta `@suzanoaberta` pela interface oficial do Instagram;
- ter acesso ao e-mail/2FA se o Instagram solicitar confirmação;
- usar somente a conta correta;
- não alterar username sem instrução explícita.

## Estado-alvo

### Username

Manter: `@suzanoaberta`

### Nome

Definir:

`Suzano Aberta | Informação Pública`

### Bio

Definir exatamente:

```text
Informação pública de Suzano, organizada e rastreável.
Notícias, dados e fontes para entender a cidade.
Independente e apartidário.
↓ Acesse o portal
```

### Link principal

`https://mukasanches.github.io/suzano-aberta/`

### Categoria

Se houver opção apropriada, usar categoria neutra ligada a mídia, notícias, informação ou organização cívica. Não usar categoria governamental, política, partido ou candidato.

### Foto de perfil

Usar o símbolo oficial do Suzano Aberta com alto contraste e enquadramento central. Não usar wordmark pequeno porque ele perde legibilidade no avatar circular.

## Destaques

Criar/organizar nesta ordem:

1. `COMECE AQUI`
2. `NOTÍCIAS`
3. `CÂMARA`
4. `PREFEITURA`
5. `CONTRATOS`
6. `SERVIÇOS`
7. `FONTES`
8. `SOBRE`

Para cada Destaque:

1. abrir/criar o Destaque;
2. selecionar apenas Stories correspondentes ao tema;
3. definir o nome exato;
4. aplicar a capa oficial;
5. confirmar que o ícone está centralizado no recorte circular;
6. salvar.

Se ainda não houver Stories adequados no arquivo, não inventar conteúdo. Deixar o Destaque pendente até a publicação dos Stories-base.

## Posts fixados

Quando os posts existirem no feed, fixar nesta lógica:

1. `COMECE AQUI` — apresentação institucional;
2. `COMO FUNCIONA` — método, fontes e rastreabilidade;
3. `GUIA DE SUZANO` — conteúdo evergreen de alta utilidade.

Não desafixar conteúdo útil sem substituto pronto.

## Validação final

Depois das alterações:

1. recarregar o perfil;
2. conferir bio e link;
3. abrir o link;
4. verificar se o nome não ficou truncado de forma prejudicial;
5. verificar as capas dos Destaques;
6. abrir cada Destaque e checar o conteúdo;
7. confirmar que os três fixados estão corretos;
8. conferir o perfil em largura mobile, se possível;
9. não mexer em senha, segurança, e-mail, telefone, 2FA ou permissões de conta.

## Prompt sugerido para uma sessão Work

> Abra o Instagram oficial e trabalhe somente no perfil `@suzanoaberta`. Aplique o estado-alvo definido em `social/instagram/WORK_PROFILE_DEPLOYMENT.md`: nome, bio, link e, quando houver Stories adequados no arquivo, organize os oito Destaques com suas capas. Não altere username, senha, e-mail, telefone, 2FA ou configurações de segurança. Não use ferramentas externas ou APIs privadas. Ao final, valide cada alteração e me diga o que foi aplicado e o que ficou pendente.
