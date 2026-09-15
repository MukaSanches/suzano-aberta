from __future__ import annotations

from .integrity import TRANSPARENCIA_URL
from .sources.base import SourceDefinition
from .sources.camara import CAMARA, COMISSOES_URL, CONTRATOS_DADOS_URL, DIARIO_URL, SESSOES_URL, VEREADORES_URL
from .sources.camara_v2 import DISPENSAS_YEAR_URL, LICITACOES_ABERTAS_URL
from .sources.legislacao import ROOT as LEGISLACAO_CAMARA_URL
from .sources.prefeitura import CONTAS_URL, IMPRENSA_URL, LEIS_DECRETOS_URL, LICITACOES_URL, ORCAMENTO_URL, PREFEITURA, SECRETARIAS_URL
from .sources.prefeitura_v2 import NOTICIAS_URL_V2


SOURCES: tuple[SourceDefinition, ...] = (
    SourceDefinition("camara-home", "Câmara Municipal", CAMARA, "Câmara Municipal de Suzano", "institucional", "Página principal."),
    SourceDefinition("camara-legislacao", "Legislação Municipal Consolidada", LEGISLACAO_CAMARA_URL, "Câmara Municipal de Suzano", "legislacao", "Sistema oficial com leis municipais, leis complementares e páginas individuais das normas."),
    SourceDefinition("camara-vereadores", "Vereadores da 19ª Legislatura", VEREADORES_URL, "Câmara Municipal de Suzano", "legislativo", "Relação oficial da legislatura atual."),
    SourceDefinition("camara-sessoes", "Sessões ordinárias", SESSOES_URL, "Câmara Municipal de Suzano", "legislativo", "Pautas, presença e identificadores de sessões."),
    SourceDefinition("camara-contratos", "Dados estruturados de contratos", CONTRATOS_DADOS_URL, "Câmara Municipal de Suzano", "contratos", "Índice oficial com CSV de contratos."),
    SourceDefinition("camara-licitacoes", "Licitações abertas", LICITACOES_ABERTAS_URL, "Câmara Municipal de Suzano", "compras-publicas", "Certames, editais e arquivos da Câmara."),
    SourceDefinition("camara-dispensas", "Dispensas de licitação", DISPENSAS_YEAR_URL.format(year=2026), "Câmara Municipal de Suzano", "compras-publicas", "Índice anual de dispensas, com situação e páginas de detalhe."),
    SourceDefinition("camara-comissoes", "Comissões permanentes", COMISSOES_URL, "Câmara Municipal de Suzano", "legislativo", "Pautas das reuniões das comissões."),
    SourceDefinition("camara-diario", "Diário Oficial do Legislativo", DIARIO_URL, "Câmara Municipal de Suzano", "diario", "Índice das edições oficiais."),
    SourceDefinition("prefeitura-home", "Prefeitura Municipal", PREFEITURA, "Prefeitura Municipal de Suzano", "institucional", "Página principal."),
    SourceDefinition("prefeitura-transparencia", "Portal de Transparência", TRANSPARENCIA_URL, "Prefeitura Municipal de Suzano", "transparencia", "Índice municipal de transparência e ponto de verificação de integridade de links."),
    SourceDefinition("prefeitura-licitacoes", "Editais e licitações", LICITACOES_URL, "Prefeitura Municipal de Suzano", "compras-publicas", "Índice oficial de editais e licitações, com leitura das páginas de detalhe."),
    SourceDefinition("prefeitura-secretarias", "Secretarias", SECRETARIAS_URL, "Prefeitura Municipal de Suzano", "estrutura", "Estrutura e contatos das secretarias."),
    SourceDefinition("prefeitura-contas", "Contas públicas", CONTAS_URL, "Prefeitura Municipal de Suzano", "fiscal", "Relatórios fiscais e demonstrativos."),
    SourceDefinition("prefeitura-orcamento", "Leis orçamentárias", ORCAMENTO_URL, "Prefeitura Municipal de Suzano", "orcamento", "PPA, LDO, LOA e anexos."),
    SourceDefinition("prefeitura-imprensa", "Imprensa Oficial", IMPRENSA_URL, "Prefeitura Municipal de Suzano", "diario", "Edições da Imprensa Oficial do Executivo."),
    SourceDefinition("prefeitura-leis", "Leis e decretos", LEIS_DECRETOS_URL, "Prefeitura Municipal de Suzano", "legislacao", "Documentos publicados na área oficial de legislação do Executivo."),
    SourceDefinition("prefeitura-noticias", "Notícias institucionais", NOTICIAS_URL_V2, "Prefeitura Municipal de Suzano", "noticias", "Publicações institucionais recentes."),
)


# Entradas adicionais usadas pelo rastreador para aprofundar o acervo. Elas não
# entram no `doctor`, porque parte do portal municipal aplica proteção automatizada
# e pode responder 403 a runners públicos mesmo quando a página existe no navegador.
EXPANSION_SEEDS: tuple[str, ...] = (
    "https://suzano.sp.gov.br/transparencia/concursos-publicos/",
    "https://suzano.sp.gov.br/transparencia/rh-e-processo-seletivo/",
    "https://suzano.sp.gov.br/transparencia/terceiro-setor/",
    "https://suzano.sp.gov.br/transparencia/leis-orcamentarias/parecer-previo-das-contas-anuais/",
    "https://suzano.sp.gov.br/transparencia/contratos-de-financiamento/",
    "https://suzano.sp.gov.br/transparencia/lei-aldir-blanc/",
    "https://suzano.sp.gov.br/transparencia/transferencias-especiais/",
    "https://suzano.sp.gov.br/transparencia/renuncia-de-receita/",
    "https://suzano.sp.gov.br/transparencia/terceiro-setor/subvencoes-terceiro-setor/",
    "https://suzano.sp.gov.br/transparencia/terceiro-setor/subvencoes-terceiro-setor/relatorio/",
    "https://suzano.sp.gov.br/transparencia/terceiro-setor/convenios-terceiro-setor/",
    "https://suzano.sp.gov.br/transparencia/terceiro-setor/ajustes/",
    "https://suzano.sp.gov.br/transparencia/siafic/",
    "https://suzano.sp.gov.br/transparencia/irmandade-da-santa-casa-de-misericordia-de-suzano/",
    "https://suzano.sp.gov.br/transparencia/editais-e-licitacoes-covid-19/",
    "https://suzano.sp.gov.br/assuntos-juridicos/parcerias-e-convenios/",
    "https://suzano.sp.gov.br/wp-content/uploads/2026/05/PLANO-ESTRATEGICO-INSTITUCIONAL-2025-2028.pdf",
    "https://suzano.sp.gov.br/wp-content/uploads/2026/05/SIGILO-LAI.pdf",
    "https://www.camarasuzano.sp.gov.br/",
    "https://www.camarasuzano.sp.gov.br/transparencia/",
    "https://www.camarasuzano.sp.gov.br/category/acesso-a-informacao/",
    "https://www.camarasuzano.sp.gov.br/category/licitacoes/licitacoes-2/",
    "https://www.camarasuzano.sp.gov.br/category/dispensas/abertas/",
    "https://www.camarasuzano.sp.gov.br/doel/",
    "https://leis.camarasuzano.sp.gov.br/szn/legislacao/",
)
