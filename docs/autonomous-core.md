# Núcleo autônomo — biblioteca, CLI e API

A versão 0.9.0 leva para a biblioteca, o terminal e a API a mesma ideia de operação autônoma usada pelo portal público: **usar sempre o último dataset validado, atualizar sem intervenção humana e nunca trocar um banco saudável por um candidato obviamente degradado**.

## Princípio de arquitetura

A coleta pesada continua centralizada no pipeline público do projeto. Isso evita que cada instalação execute crawlers diferentes, produza resultados divergentes ou sobrecarregue fontes oficiais.

```text
fontes públicas
      ↓
GitHub Autopilot de coleta
      ↓
validação + snapshot rolling
      ↓
release data-latest + checksum
      ↓
┌──────────────┬───────────────┬───────────────┐
│ Biblioteca   │ CLI           │ API           │
│ checa uso    │ auto vigiar   │ checa 15 min │
└──────────────┴───────────────┴───────────────┘
      ↓
SQLite local validado
```

Uma instalação local não baixa o snapshot inteiro a cada verificação. Primeiro consulta o arquivo de checksum remoto, de poucos bytes. Se o checksum não mudou e o SQLite local continua íntegro, nenhuma transferência pesada acontece.

## `AutonomousDataManager`

A biblioteca expõe `AutonomousDataManager` e `AutoUpdatePolicy`:

```python
from suzano_aberta import AutoUpdatePolicy, AutonomousDataManager

manager = AutonomousDataManager(
    "suzano-aberta.sqlite3",
    policy=AutoUpdatePolicy(check_interval_seconds=900),
)

result = manager.ensure_fresh()
print(result.action, result.records)
print(manager.status().to_dict())
```

O manager mantém dois pequenos sidecars ao lado do banco:

- `.autopilot.json`: último sucesso, último erro, falhas consecutivas, quantidade de verificações e atualizações;
- `.autopilot.lock`: impede dois processos de substituírem o mesmo banco simultaneamente.

Locks antigos são considerados abandonados depois do tempo configurado na política.

## Proteções de promoção

O sincronizador de snapshots aplica as seguintes barreiras antes de substituir o banco local:

1. checksum remoto quando disponível;
2. cabeçalho SQLite válido;
3. `PRAGMA quick_check`;
4. existência de registros ativos;
5. consistência do FTS quando a tabela estiver presente;
6. quantidade mínima de registros definida pelo chamador;
7. substituição atômica com `os.replace`.

O `AutonomousDataManager` usa por padrão um piso equivalente a 85% da quantidade de registros do banco atual. Um release que cair abruptamente abaixo desse limite é recusado e o banco anterior permanece intacto.

## Biblioteca principal

`Suzano` continua aceitando `auto_sync=False` para cenários totalmente controlados. Com o padrão `auto_sync=True`, as operações de leitura chamam uma verificação de frescor limitada por intervalo:

```python
from suzano_aberta import Suzano

with Suzano(auto_sync=True, auto_sync_interval_seconds=900) as suzano:
    registros = suzano.search("transporte escolar")
    print(suzano.autopilot_status())
```

A verificação não significa download a cada chamada. O manager lembra a última tentativa e só volta à rede quando o intervalo vencer.

## CLI

O executável principal ganhou um grupo próprio:

```text
suzano auto status
suzano auto agora
suzano auto vigiar
```

`status` mostra frescor, última atualização, falhas e próxima checagem. `agora` força uma checagem imediata. `vigiar` mantém um processo ativo e é adequado para uma máquina que deve conservar o banco atualizado enquanto estiver ligada.

Exemplo:

```bash
suzano auto vigiar --intervalo 900
```

O processo pode ser encerrado com `Ctrl+C`; isso não apaga nem invalida o banco existente.

## API

A API continua somente leitura para clientes HTTP. A manutenção do banco ocorre internamente. O intervalo padrão de sincronização passa a ser 900 segundos e pode ser alterado por:

```text
SUZANO_API_AUTO_SYNC=true
SUZANO_API_SYNC_INTERVAL_SECONDS=900
```

Como a sincronização é checksum-aware, a maior parte dessas execuções é apenas uma verificação curta.

O endpoint abaixo expõe a saúde da automação sem permitir mutações remotas:

```text
GET /v1/autopilot
```

Ele informa quantidade de registros, frescor, lock, último sucesso, último erro, falhas consecutivas, checksum instalado e próxima verificação.

## Falhas e recuperação

Uma falha de rede não apaga o banco. O estado registra a falha e aplica um intervalo de retry menor (`failure_backoff_seconds`). Quando a rede ou o release volta a funcionar, a próxima execução normaliza o estado automaticamente.

A estratégia é deliberadamente "last known good": disponibilidade de dados válidos é preferida a substituir silenciosamente o acervo por um arquivo incompleto.

## O que não acontece

O núcleo autônomo não roda um crawler completo em todo computador e não usa IA para decidir se um snapshot é confiável. As regras de promoção são determinísticas, reproduzíveis e auditáveis.
