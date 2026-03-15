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


class CrmDashboardCards(BaseModel):
    recebidas: int
    recebidas12m: int
    recebidasUltimoMes: int
    recebidasMesCorrente: int
    ganhas: int
    ganhas12m: int
    ganhasUltimoMes: int
    ganhasMesCorrente: int
    perdidas: int
    perdidas12m: int
    perdidasUltimoMes: int
    perdidasMesCorrente: int
    taxaConversao: float
    ativas: int
    valorAtivas: float
    mrrIncremental: float
    mrrIncremental12m: float
    mrrIncrementalUltimoMes: float
    mrrIncrementalMesCorrente: float


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


class CrmDashboardResponse(BaseModel):
    cards: CrmDashboardCards
    graficos: CrmDashboardGraficosResponse
    filtros: CrmDashboardFiltrosResponse

