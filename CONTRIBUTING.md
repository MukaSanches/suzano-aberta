# Contribuindo

Obrigado por considerar uma contribuição ao Suzano Aberta.

O projeto trabalha com dados públicos e, por isso, correção e rastreabilidade têm prioridade sobre quantidade de funcionalidades.

## Ambiente

```bash
git clone https://github.com/MukaSanches/suzano-aberta.git
cd suzano-aberta
python -m venv .venv
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

## Antes de abrir um pull request

Execute:

```bash
ruff check .
mypy src/suzano_aberta
pytest
python -m build
```

Não faça os testes unitários dependerem da internet. Testes contra fontes reais ficam em `tests_live/` e são executados separadamente.

## Alterando um parser

Uma mudança de parser deve:

1. identificar a fonte oficial afetada;
2. explicar a mudança observada na página ou arquivo;
3. preservar a URL de origem;
4. adicionar ou atualizar um teste de regressão;
5. evitar heurística quando um campo não puder ser extraído com segurança.

Fixtures devem ser mínimas: inclua apenas o HTML ou CSV necessário para reproduzir o caso.

## Commits

Prefira commits pequenos e descritivos. O repositório usa mensagens no estilo Conventional Commits quando isso ajuda a leitura, por exemplo:

- `fix(camara): adapt session parser to new markup`
- `test(prefeitura): cover retified budget document`
- `docs: document source provenance rules`

## Dados pessoais e segredos

Não envie tokens, cookies, credenciais, dumps de sessão ou dados privados. Este projeto deve funcionar apenas com informações acessíveis publicamente.

## Escopo político

Contribuições devem permanecer factuais e apartidárias. O projeto não aceita funcionalidades cujo objetivo seja produzir nota ideológica, inferir culpa ou rotular agentes públicos sem base documental explícita.
