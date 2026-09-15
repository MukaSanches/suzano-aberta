from __future__ import annotations

from .sources.base import SourceDefinition
from .sources.camara import CAMARA, COMISSOES_URL, CONTRATOS_DADOS_URL, DIARIO_URL, SESSOES_URL, VEREADORES_URL
from .sources.prefeitura import CONTAS_URL, IMPRENSA_URL, LEIS_DECRETOS_URL, LICITACOES_URL, NOTICIAS_URL, ORCAMENTO_URL, PREFEITURA, SECRETARIAS_URL


SOURCES: tuple[SourceDefinition, ...] = (
    SourceDefinition("camara-home", "Câmara Municipal", CAMARA, "Câmara Municipal de Suzano", "institucional", "Página principal."),
    SourceDefinition("camara-vereadores", "Vereadores da 19ª Legislatura", VEREADORES_URL, "Câmara Municipal de Suzano", "legislativo", "Relação oficial da legislatura atual."),
    SourceDefinition("camara-sessoes", "Sessões ordinárias", SESSOES_URL, "Câmara Municipal de Suzano", "legislativo", "Pautas, presença e identificadores de sessões."),
    SourceDefinition("camara-contratos", "Dados estruturados de contratos", CONTRATOS_DADOS_URL, "Câmara Municipal de Suzano", "contratos", "Índice oficial com CSV de contratos."),
    SourceDefinition("camara-comissoes", "Comissões permanentes", COMISSOES_URL, "Câmara Municipal de Suzano", "legislativo", "Pautas das reuniões das comissões."),
    SourceDefinition("camara-diario", "Diário Oficial do Legislativo", DIARIO_URL, "Câmara Municipal de Suzano", "diario", "Índice das edições oficiais."),
    SourceDefinition("prefeitura-home", "Prefeitura Municipal", PREFEITURA, "Prefeitura Municipal de Suzano", "institucional", "Página principal."),
    SourceDefinition("prefeitura-licitacoes", "Editais e licitações", LICITACOES_URL, "Prefeitura Municipal de Suzano", "compras-publicas", "Índice oficial de editais e licitações."),
    SourceDefinition("prefeitura-secretarias", "Secretarias", SECRETARIAS_URL, "Prefeitura Municipal de Suzano", "estrutura", "Estrutura e contatos das secretarias."),
    SourceDefinition("prefeitura-contas", "Contas públicas", CONTAS_URL, "Prefeitura Municipal de Suzano", "fiscal", "Relatórios fiscais e demonstrativos."),
    SourceDefinition("prefeitura-orcamento", "Leis orçamentárias", ORCAMENTO_URL, "Prefeitura Municipal de Suzano", "orcamento", "PPA, LDO, LOA e anexos."),
    SourceDefinition("prefeitura-imprensa", "Imprensa Oficial", IMPRENSA_URL, "Prefeitura Municipal de Suzano", "diario", "Edições da Imprensa Oficial do Executivo."),
    SourceDefinition("prefeitura-leis", "Leis e decretos", LEIS_DECRETOS_URL, "Prefeitura Municipal de Suzano", "legislacao", "Documentos publicados na área oficial de legislação do Executivo."),
    SourceDefinition("prefeitura-noticias", "Notícias institucionais", NOTICIAS_URL, "Prefeitura Municipal de Suzano", "noticias", "Publicações institucionais recentes."),
)
