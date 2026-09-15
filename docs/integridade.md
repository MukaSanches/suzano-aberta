# Integridade de fontes

A coleta de dados públicos depende da integridade das páginas que apontam para os documentos. Uma página pode continuar respondendo HTTP 200 e, ainda assim, passar a publicar links inesperados.

Por isso, o Suzano Aberta separa duas perguntas:

1. **a fonte está acessível?** — verificada por `suzano doctor`;
2. **a fonte contém referências externas inesperadas?** — verificada por `suzano integridade`.

## Regra atual

Na versão 0.1.1 a verificação cobre o índice de Transparência da Prefeitura de Suzano.

O processo é determinístico:

1. a página oficial é baixada pelo mesmo cliente HTTP controlado usado pelos coletores;
2. cada link é transformado em URL absoluta;
3. domínios do município (`suzano.sp.gov.br` e subdomínios) são aceitos;
4. serviços externos conhecidos e documentados ficam em uma allowlist curta;
5. os demais domínios são retornados como `dominio_externo_nao_reconhecido`.

A allowlist não tenta adivinhar se um site é confiável. Um novo domínio deve ser revisado e documentado antes de ser incluído.

## O que um achado significa

Um achado significa apenas:

> uma fonte oficial contém um link para um domínio externo que não faz parte do conjunto conhecido pelo projeto.

Ele **não** prova invasão, comprometimento, fraude, autoria, irregularidade administrativa ou intenção maliciosa.

Essa distinção é importante porque o software deve registrar fatos observáveis e deixar conclusões de segurança ou jurídicas para investigação apropriada.

## Automação

Saída humana:

```bash
suzano integridade
```

Saída estruturada:

```bash
suzano integridade --json
```

Para pipelines que desejem interromper a execução quando houver itens para revisão:

```bash
suzano integridade --falhar-se-encontrar
```

Nesse modo, o comando retorna código de saída `3` quando houver pelo menos um domínio externo não reconhecido.

## Evolução prevista

Verificações futuras podem incluir alterações inesperadas de domínio, mudança de MIME type, desaparecimento de documentos, alteração de certificados, hashes de documentos e mudanças estruturais em páginas críticas. Cada regra deve permanecer testável, explicável e independente de modelos generativos.
