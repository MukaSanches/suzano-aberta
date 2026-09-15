# Limitações conhecidas da v0.1

Suzano Aberta é uma primeira versão pública e deliberadamente conservadora.

- A cobertura depende do que os órgãos publicam e de como publicam.
- Algumas áreas oficiais usam HTML sem API estável; seus parsers podem precisar de manutenção quando a página mudar.
- PDFs digitalizados sem camada de texto não são submetidos a OCR automaticamente.
- A v0.1 indexa documentos; ela não interpreta juridicamente o conteúdo.
- O projeto não presume que um item desaparecido de uma página tenha sido revogado, excluído ou cancelado.
- O mecanismo de busca do SQLite é simples e não pretende substituir um mecanismo de busca textual dedicado.
- Dados coletados não recebem selo de autenticidade. A fonte oficial permanece soberana.

Essas limitações são escolhas de segurança e escopo. A prioridade da v0.1 é produzir uma fundação verificável antes de adicionar inferências ou automações mais agressivas.
