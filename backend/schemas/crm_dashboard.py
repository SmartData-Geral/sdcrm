from datetime import date

from pydantic import BaseModel, Field


class CrmDashboardFiltroParams(BaseModel):
    data_inicial: date | None = Field(default=None)
    data_final: date | None = Field(default=None)
    responsavel_id: int | None = Field(default=None)
    status: str | None = Field(
        default="todas",
        description="todas|ganhas|perdidas|ativas",
    )
    serie_anos: list[int] | None = Field(
        default=None,
        description="Anos (calendário completo jan–dez) para série mensal e meta x realizado; quando informado, ignora data_inicial/data_final nesses agregados.",
    )


class CrmDashboardOportunidadesFiltroParams(CrmDashboardFiltroParams):
    """Parâmetros do drill-down (filtros globais + recorte analítico)."""

    fonte: str | None = Field(default=None)
    solucao: str | None = Field(default=None)
    motivo_perda: str | None = Field(default=None)
    periodo: str | None = Field(default=None, description="YYYY-MM")
    metrica: str | None = Field(
        default=None,
        description="recebidas|ganhas|perdidas|ativas|mrrIncremental",
    )


class CrmDashboardCards(BaseModel):
    recebidas: int
    recebidas12m: int
    recebidasUltimoMes: int
    recebidasMesCorrente: int
    recebidasUltimos7Dias: int
    ganhas: int
    ganhas12m: int
    ganhasUltimoMes: int
    ganhasMesCorrente: int
    ganhasUltimos7Dias: int
    perdidas: int
    perdidas12m: int
    perdidasUltimoMes: int
    perdidasMesCorrente: int
    perdidasUltimos7Dias: int
    taxaConversao: float
    ativas: int
    valorAtivas: float
    forecastAtivas: float
    mrrIncremental: float
    mrrIncremental12m: float
    mrrIncrementalUltimoMes: float
    mrrIncrementalMesCorrente: float
    mrrIncrementalUltimos7Dias: float


class CrmDashboardGraficoPorMesItem(BaseModel):
    ano: int
    mes: int
    quantidade: int


class CrmDashboardGraficoPorFonteItem(BaseModel):
    fonte: str
    quantidade: int


class CrmDashboardGraficoPorSolucaoItem(BaseModel):
    solucao: str
    quantidade: int


class CrmDashboardGraficoAtivasPorResponsavelItem(BaseModel):
    responsavel: str
    quantidade: int


class CrmDashboardFiltrosResponse(BaseModel):
    responsaveis: list[dict]


class CrmDashboardGraficosResponse(BaseModel):
    porMes: list[CrmDashboardGraficoPorMesItem]
    porFonte: list[CrmDashboardGraficoPorFonteItem]
    porSolucao: list[CrmDashboardGraficoPorSolucaoItem]
    ativasPorResponsavel: list[CrmDashboardGraficoAtivasPorResponsavelItem]


class CrmDashboardResumoMetaLinha(BaseModel):
    meta: float | None = None
    realizado: float
    percentual: float | None = None
    gap: float | None = None


class CrmDashboardResumoMetas(BaseModel):
    recebimento: CrmDashboardResumoMetaLinha
    fechamento: CrmDashboardResumoMetaLinha
    mrrIncremental: CrmDashboardResumoMetaLinha


class CrmDashboardMotivoPerdaItem(BaseModel):
    motivo: str
    quantidade: int
    percentualQuantidade: float
    mrrPerdido: float
    percentualMrr: float


class CrmDashboardSerieMensalItem(BaseModel):
    periodo: str
    label: str
    recebidas: int = 0
    ganhas: int = 0
    perdidas: int = 0
    taxaConversao: float = 0.0
    mrrIncremental: float = 0.0
    mrrMedio: float = 0.0
    forecast: float = 0.0
    metaRecebidas: float | None = None
    metaGanhas: float | None = None
    metaMrr: float | None = None


class CrmDashboardRankingResponsavelItem(BaseModel):
    responsavelId: int | None = None
    responsavel: str
    recebidas: int = 0
    ganhas: int = 0
    perdidas: int = 0
    ativas: int = 0
    taxaConversao: float = 0.0
    mrrIncremental: float = 0.0
    ticketMedio: float = 0.0


class CrmDashboardRankingFonteItem(BaseModel):
    fonte: str
    recebidas: int = 0
    ganhas: int = 0
    perdidas: int = 0
    taxaConversao: float = 0.0
    mrrIncremental: float = 0.0


class CrmDashboardRankingSolucaoItem(BaseModel):
    solucao: str
    recebidas: int = 0
    ganhas: int = 0
    perdidas: int = 0
    taxaConversao: float = 0.0
    mrrIncremental: float = 0.0


class CrmDashboardRankingsResponse(BaseModel):
    responsaveis: list[CrmDashboardRankingResponsavelItem]
    fontes: list[CrmDashboardRankingFonteItem]
    solucoes: list[CrmDashboardRankingSolucaoItem]


class CrmDashboardOportunidadeResumoItem(BaseModel):
    id: int
    nome: str
    cliente: str | None = None
    responsavel: str | None = None
    status: str
    fonte: str | None = None
    solucao: str | None = None
    motivoPerda: str | None = None
    valorMrr: float | None = None
    forecast: float | None = None
    dataCriacao: str | None = None
    dataFechamento: str | None = None
    etapa: str | None = None


class CrmDashboardOportunidadesResumo(BaseModel):
    quantidade: int
    mrrTotal: float
    forecastTotal: float
    ticketMedio: float


class CrmDashboardOportunidadesListResponse(BaseModel):
    itens: list[CrmDashboardOportunidadeResumoItem]
    total: int
    resumo: CrmDashboardOportunidadesResumo


class CrmDashboardResponse(BaseModel):
    cards: CrmDashboardCards
    graficos: CrmDashboardGraficosResponse
    filtros: CrmDashboardFiltrosResponse
    temMeta: bool = False
    resumoMetas: CrmDashboardResumoMetas
    motivosPerda: list[CrmDashboardMotivoPerdaItem] = Field(default_factory=list)
    serieMensal: list[CrmDashboardSerieMensalItem] = Field(default_factory=list)
    rankings: CrmDashboardRankingsResponse

