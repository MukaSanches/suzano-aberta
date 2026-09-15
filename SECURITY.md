# Política de segurança

## Versões suportadas

Enquanto o projeto estiver na série `0.x`, apenas a versão mais recente recebe correções de segurança.

## Como relatar

Não publique credenciais, tokens, cookies ou detalhes exploráveis em uma issue pública. Use o recurso privado de Security Advisories do GitHub quando disponível para o repositório.

Inclua no relato:

- versão afetada;
- impacto esperado;
- passos mínimos para reprodução;
- sistema operacional e versão do Python;
- correção sugerida, se houver.

## Modelo de ameaça da v0.1

Suzano Aberta acessa apenas fontes públicas e grava um banco SQLite local. Não executa JavaScript remoto, não envia telemetria e não requer credenciais.

Os principais riscos considerados são conteúdo remoto malformado, arquivos excessivamente grandes, mudanças inesperadas de estrutura, redirecionamentos e dependências vulneráveis.

A biblioteca não deve ser executada com privilégios administrativos sem necessidade.
