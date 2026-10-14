from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class MetaAdsContaCreate(BaseModel):
    macNome: str = Field(min_length=1, max_length=150)
    macContaExterna: str = Field(min_length=1, max_length=40)
    token: str = Field(min_length=20, max_length=2000)
    origens: list[int] = Field(default_factory=list)

    @field_validator("token")
    @classmethod
    def _sem_espacos(cls, valor: str) -> str:
        # Token copiado do Business Manager costuma vir com espaco ou quebra de linha.
        return "".join(valor.split())


class MetaAdsContaUpdate(BaseModel):
    macNome: str | None = Field(default=None, min_length=1, max_length=150)
    token: str | None = Field(default=None, min_length=20, max_length=2000)
    origens: list[int] | None = None
    macAtivo: bool | None = None

    @field_validator("token")
    @classmethod
    def _sem_espacos(cls, valor: str | None) -> str | None:
        return "".join(valor.split()) if valor is not None else None


class MetaAdsContaResponse(BaseModel):
    macId: int
    macNome: str
    macContaExterna: str
    macTokenFinal: str
    macMoeda: str | None
    macFuso: str | None
    macStatus: str
    macMensagem: str | None
    macUltimaSync: datetime | None
    macCargaInicialFeita: bool
    macAtivo: bool
    origens: list[int]


class MetaAdsContaListResponse(BaseModel):
    items: list[MetaAdsContaResponse]


class MetaAdsTesteResponse(BaseModel):
    ok: bool
    nome: str | None = None
    moeda: str | None = None
    fuso: str | None = None
    mensagem: str | None = None


class MetaAdsSyncLogResponse(BaseModel):
    mslId: int
    mslInicio: date
    mslFim: date
    mslOrigem: str
    mslStatus: str
    mslLinhas: int
    mslLeadsVinculados: int
    mslErro: str | None
    mslDuracaoMs: int | None
    mslDataExecucao: datetime

    class Config:
        from_attributes = True


class MetaAdsSyncLogListResponse(BaseModel):
    items: list[MetaAdsSyncLogResponse]


class MetaAdsSyncPeriodoRequest(BaseModel):
    data_inicial: date
    data_final: date
    macId: int | None = None

    @model_validator(mode="after")
    def _periodo_valido(self):
        from ..services.meta_ads.sincronizacao import MAX_DIAS_PERIODO

        if self.data_final < self.data_inicial:
            raise ValueError("A data final deve ser igual ou posterior à inicial")
        if (self.data_final - self.data_inicial).days > MAX_DIAS_PERIODO:
            raise ValueError(f"O período pode ter no máximo {MAX_DIAS_PERIODO} dias")
        return self


class MetaAdsSyncIniciadaResponse(BaseModel):
    contas: list[int]
    mensagem: str


class MetaAdsLinha(BaseModel):
    mcgId: int | None
    nome: str
    status: str | None
    macId: int | None
    investimento: float
    impressoes: int
    cliques: int
    leadsMeta: int
    leadsCrm: int
    vendas: int
    mrr: float
    projeto: float
    ctr: float | None
    cpc: float | None
    cpl: float | None
    cac: float | None
    retorno: float | None


class MetaAdsPainelResponse(BaseModel):
    temConta: bool
    total: MetaAdsLinha
    campanhas: list[MetaAdsLinha]
    naoIdentificada: MetaAdsLinha | None


class MetaAdsSerieDia(BaseModel):
    data: date
    investimento: float
    leadsMeta: int
    leadsCrm: int


class MetaAdsLeadItem(BaseModel):
    opoId: int
    opoTitulo: str
    opoNomeContato: str | None
    opoDataRecebimento: date | None
    opoStatusFechamento: str | None
    opoValorFechado: float | None


class MetaAdsCampanhaDetalheResponse(BaseModel):
    campanha: MetaAdsLinha
    serie: list[MetaAdsSerieDia]
    leads: list[MetaAdsLeadItem]


class MetaAdsResumoResponse(BaseModel):
    temConta: bool
    investimento: float
    leadsCrm: int
    vendas: int
    cpl: float | None
    cac: float | None
    retorno: float | None


class MetaAdsCampanhaOpcao(BaseModel):
    mcgId: int
    nome: str
    conta: str
    status: str | None


class MetaAdsCampanhaOpcoesResponse(BaseModel):
    items: list[MetaAdsCampanhaOpcao]


class MetaAdsContaOpcao(BaseModel):
    macId: int
    macNome: str


class MetaAdsContaOpcoesResponse(BaseModel):
    items: list[MetaAdsContaOpcao]


class OportunidadeCampanhaMetaRequest(BaseModel):
    opoMcgId: int | None


class OportunidadeCampanhaMetaResponse(BaseModel):
    opoId: int
    opoMcgId: int | None
    opoMcgManual: bool
