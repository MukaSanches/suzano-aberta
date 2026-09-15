# Integridade de fontes

Uma fonte pode responder HTTP 200 e ainda assim ter mudado de estrutura, passar a apontar para destinos externos inesperados ou deixar de publicar determinado material. O Suzano Aberta evita resumir situações diferentes em um único rótulo de “saúde”.

## Três perguntas diferentes

1. **a instalação local está funcional?** — `suzano diagnostico`;
2. **as fontes catalogadas estão acessíveis agora?** — `suzano doctor`;
3. **uma regra específica encontrou um sinal que precisa de revisão?** — `suzano integridade`.

Essa separação reduz falsos diagnósticos. Uma máquina sem FTS5 não significa que o site oficial caiu; um HTTP 500 não significa que houve alteração de integridade; e um link externo inesperado não prova comprometimento.

## Regra de integridade implementada

A verificação atual cobre uma fonte municipal selecionada e procura domínios externos que não estejam no conjunto conhecido pelo projeto.

O processo é determinístico:

1. a página pública é obtida pelo mesmo cliente HTTP controlado usado pelos coletores;
2. links são transformados em URLs absolutas;
3. domínios municipais esperados são aceitos;
4. serviços externos conhecidos e documentados permanecem em uma allowlist curta;
5. os demais destinos são retornados como `dominio_externo_nao_reconhecido`.

A allowlist não é uma declaração geral de confiança em um terceiro. Ela registra apenas que aquele destino é esperado pela regra atual. Um novo domínio deve ser revisado antes de ser incorporado.

## O que um achado significa

Um achado significa que a página observada continha uma referência externa que a regra atual não reconheceu como esperada.

Ele **não** prova invasão, comprometimento, fraude, autoria, irregularidade administrativa, intenção maliciosa ou responsabilidade de qualquer pessoa.

O software registra o fato observável — URL, domínio e evidência disponível — e deixa conclusões de segurança ou jurídicas para investigação apropriada.

## Uso humano

```bash
suzano integridade
```

## Saída estruturada

```bash
suzano integridade --json
```

## Uso em pipeline

```bash
suzano integridade --falhar-se-encontrar
```

Nesse modo, o comando retorna código `3` quando há pelo menos um item para revisão. Esse código significa “a regra encontrou algo”, não “um incidente foi confirmado”.

## Saúde local

Para verificar o ambiente sem fazer chamadas à internet:

```bash
suzano diagnostico
suzano diagnostico --json
```

O diagnóstico local cobre Python, diretório de dados, espaço livre, SQLite, FTS5, JSON1 e `PRAGMA quick_check` no modo profundo.

## Saúde das fontes

```bash
suzano doctor
suzano doctor --json
```

`doctor` executa verificações básicas de acessibilidade das fontes catalogadas e informa status/tempo observado. Uma falha representa indisponibilidade ou erro naquela verificação; não é evidência de intenção ou irregularidade.

## Regras futuras

Novas verificações podem acompanhar mudança inesperada de domínio, MIME type, certificado, hash de documento, estrutura de páginas críticas ou desaparecimento persistente de recursos. Cada regra deve possuir definição clara, evidência preservada, teste determinístico e linguagem proporcional ao que realmente foi observado.
