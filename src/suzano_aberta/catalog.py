from __future__ import annotations

from .sources.base import SourceDefinition
from .sources.camara import (
    CAMARA,
    COMISSOES_URL,
    CONTRATOS_DADOS_URL,
    DIARIO_URL,
    LICITACOES_URL as CAMARA_LICITACOES_URL,
    SESSOES_URL,
    VEREADORES_URL,
)
from .sources.prefeitura import (
    CONCURSOS_URL,
    CONTAS_URL,
    IMPRENSA_URL,
    LEIS_DECRETOS_URL,
    LICITACOES_URL,
    NOTICIAS_URL,
    ORCAMENTO_URL,
    PARCERIAS_URL,
    PREFEITURA,
    SECRETARIAS_URL,
    TRANSFERENCIAS_URL,
)


SOURCES: tuple[SourceDefinition, ...] = (
    SourceDefinition("camara-home", "Câmara Municipal", CAMARA, "Câmara Municipal de Suzano", "institucional", "Página principal do Legislativo."),
    SourceDefinition("camara-vereadores", "Vereadores da 19ª Legislatura", VEREADORES_URL, "Câmara Municipal de Suzano", "legislativo", "Relação oficial da legislatura atual."),
    SourceDefinition("camara-sessoes", "Sessões ordinárias", SESSOES_URL, "Câmara Municipal de Suzano", "legislativo", "Sessões, identificadores e links de consulta."),
    SourceDefinition("camara-contratos", "Dados estruturados de contratos", CONTRATOS_DADOS_URL, "Câmara Municipal de Suzano", "contratos", "Índice oficial com dados estruturados e relatórios de contratos."),
    SourceDefinition("camara-licitacoes", "Licitações da Câmara", CAMARA_LICITACOES_URL, "Câmara Municipal de Suzano", "compras-publicas", "Licitações publicadas pelo Legislativo."),
    SourceDefinition("camara-comissoes", "Comissões permanentes", COMISSOES_URL, "Câmara Municipal de Suzano", "legislativo", "Pautas das reuniões das comissões."),
    SourceDefinition("camara-diario", "Diário Oficial do Legislativo", DIARIO_URL, "Câmara Municipal de Suzano", "diario", "Índice das edições oficiais do Legislativo."),
    SourceDefinition("prefeitura-home", "Prefeitura Municipal", PREFEITURA, "Prefeitura Municipal de Suzano", "institucional", "Página principal do Executivo."),
    SourceDefinition("prefeitura-licitacoes", "Editais e licitações", LICITACOES_URL, "Prefeitura Municipal de Suzano", "compras-publicas", "Publicações de editais e licitações."),
    SourceDefinition("prefeitura-secretarias", "Secretarias", SECRETARIAS_URL, "Prefeitura Municipal de Suzano", "estrutura", "Estrutura administrativa e páginas das secretarias."),
    SourceDefinition("prefeitura-contas", "Contas públicas", CONTAS_URL, "Prefeitura Municipal de Suzano", "fiscal", "Relatórios fiscais e demonstrativos."),
    SourceDefinition("prefeitura-orcamento", "Leis orçamentárias", ORCAMENTO_URL, "Prefeitura Municipal de Suzano", "orcamento", "PPA, LDO, LOA e anexos."),
    SourceDefinition("prefeitura-imprensa", "Imprensa Oficial", IMPRENSA_URL, "Prefeitura Municipal de Suzano", "diario", "Edições da Imprensa Oficial do Executivo."),
    SourceDefinition("prefeitura-leis", "Leis e decretos", LEIS_DECRETOS_URL, "Prefeitura Municipal de Suzano", "legislacao", "Documentos da área oficial de legislação."),
    SourceDefinition("prefeitura-concursos", "Concursos públicos", CONCURSOS_URL, "Prefeitura Municipal de Suzano", "rh", "Editais, resultados e convocações de concursos públicos."),
    SourceDefinition("prefeitura-transferencias", "Transferências especiais", TRANSFERENCIAS_URL, "Prefeitura Municipal de Suzano", "fiscal", "Documentos sobre transferências especiais e emendas."),
    SourceDefinition("prefeitura-parcerias", "Parcerias e convênios", PARCERIAS_URL, "Prefeitura Municipal de Suzano", "terceiro-setor", "Parcerias e convênios publicados pelo Executivo."),
    SourceDefinition("prefeitura-noticias", "Notícias institucionais", NOTICIAS_URL, "Prefeitura Municipal de Suzano", "noticias", "Publicações institucionais recentes."),
)
