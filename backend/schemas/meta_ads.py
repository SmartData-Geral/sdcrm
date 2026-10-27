from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class MetaAdsContaCreate(BaseModel):
    macNome: str = Field(min_length=1, max_length=150)
    macContaExterna: str = Field(min_length=1, max_length=40)
    token: str = Field(min_length=20, max_length=2000)
    origens: list[int] = Field(default_factory=list)
    # "Contar so leads com rastreio da Meta" (desligado por padrao).
    macExigirRastreio: bool = False

    @field_validator("macNome")
    @classmethod
    def _nome_sem_espacos(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("Informe o nome da conta")
        return valor

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
    macExigirRastreio: bool | None = None

    @field_validator("macNome")
    @classmethod
    def _nome_sem_espacos(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor = valor.strip()
        if not valor:
            raise ValueError("Informe o nome da conta")
        return valor

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
    macExigirRastreio: bool
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


NivelLinha = Literal["campanha", "conjunto", "anuncio", "nao_identificada", "total"]


class MetaAdsLinha(BaseModel):
    """
    Linha do painel. `id` e o mcgId/mcjId/manId conforme o `nivel`; `mcgId` e sempre a campanha
    (tambem nas linhas de conjunto e anuncio). `cpl` = investimento / leads Meta; os custos do
    funil (lead CRM, MQL, oportunidade, `cac` por contrato) usam as contagens do CRM.
    `vendas` = contratos no periodo.
    """

    nivel: NivelLinha
    id: int | None
    mcgId: int | None
    nome: str
    status: str | None
    macId: int | None
    investimento: float
    impressoes: int
    cliques: int
    leadsMeta: int
    leadsCrm: int
    mqls: int
    oportunidades: int
    vendas: int
    mrr: float
    projeto: float
    ctr: float | None
    cpc: float | None
    cpl: float | None
    custoLeadCrm: float | None
    custoMql: float | None
    custoOportunidade: float | None
    cac: float | None
    retorno: float | None
    horasPrimeiroContato: float | None
    filhos: list["MetaAdsLinha"] = Field(default_factory=list)


MetaAdsLinha.model_rebuild()


class MetaAdsRevisaoItem(BaseModel):
    """Lead com origem mapeada como Meta e sem nenhum sinal da Meta (para corrigir a origem)."""

    opoId: int
    opoTitulo: str
    opoNomeContato: str | None
    opoDataRecebimento: date | None


class MetaAdsPainelResponse(BaseModel):
    temConta: bool
    total: MetaAdsLinha
    campanhas: list[MetaAdsLinha]
    naoIdentificada: MetaAdsLinha | None
    # % dos leads Meta recebidos no periodo com opoMetaAnuncioId; None sem leads.
    cobertura: float | None = None
    revisaoOrigem: list[MetaAdsRevisaoItem] = Field(default_factory=list)


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


ALERTAS_MONITOR = ("cpl", "gasto", "frequencia", "ctr", "parado", "semContato")


class MetaAdsMonitorConfigResponse(BaseModel):
    etapaMqlId: int | None
    etapaOportunidadeId: int | None
    cplFator: float
    gastoSemLead: float
    frequenciaMax: float
    quedaCtrPct: int
    horasSemContato: int
    gastoMinRanking: float
    metaCpl: float
    metaTaxaMql: float
    horaResumo: int
    alertas: dict[str, bool]


class MetaAdsMonitorConfigUpdate(BaseModel):
    """Campos omitidos nao mudam; as etapas aceitam null explicito para limpar."""

    etapaMqlId: int | None = None
    etapaOportunidadeId: int | None = None
    cplFator: float | None = Field(default=None, gt=0, le=999)
    gastoSemLead: float | None = Field(default=None, gt=0, le=1_000_000)
    frequenciaMax: float | None = Field(default=None, gt=0, le=999)
    quedaCtrPct: int | None = Field(default=None, gt=0, le=100)
    horasSemContato: int | None = Field(default=None, gt=0, le=720)
    gastoMinRanking: float | None = Field(default=None, ge=0, le=1_000_000)
    metaCpl: float | None = Field(default=None, gt=0, le=1_000_000)
    metaTaxaMql: float | None = Field(default=None, ge=0.1, le=100)
    horaResumo: int | None = Field(default=None, ge=0, le=23)
    alertas: dict[str, bool] | None = None

    @field_validator("alertas")
    @classmethod
    def _chaves_validas(cls, valor):
        if valor is not None:
            invalidas = set(valor) - set(ALERTAS_MONITOR)
            if invalidas:
                raise ValueError(f"Alerta desconhecido: {', '.join(sorted(invalidas))}")
        return valor


STATUS_ALERTA = ("aberto", "ciente", "resolvido")


class MetaAdsAlertaResponse(BaseModel):
    malId: int
    malTipo: str
    malChave: str
    malStatus: str
    malMensagem: str
    malDados: dict | None
    malPrimeiroEm: datetime
    malUltimoEm: datetime
    malResolvidoEm: datetime | None
    # Nome do anuncio/campanha/conta do alvo (None para lead: o nome ja esta na mensagem).
    alvoNome: str | None = None


class MetaAdsAlertaListResponse(BaseModel):
    items: list[MetaAdsAlertaResponse]


class MetaAdsResumoDiarioResponse(BaseModel):
    mrsId: int
    mrsData: date
    mrsInicio: date
    mrsFim: date
    # Só ids, nomes de campanha/anúncio e números agregados.
    mrsDados: dict
    mrsLeitura: str | None
    mrsAviso: str | None
    mrsGeradoEm: datetime


class MetaAdsResumoDiarioItem(BaseModel):
    mrsData: date
    mrsGeradoEm: datetime


class MetaAdsResumoDiarioListResponse(BaseModel):
    items: list[MetaAdsResumoDiarioItem]


# ---- Cockpit de campanhas ----
SeloCockpit = Literal["bom", "atencao", "ruim", "sem_dados"]
QuadranteCockpit = Literal["escalar", "otimizar_custo", "rever_publico", "pausar", "aguardar_dados"]
EtapaFunilCockpit = Literal["impressoes", "cliques", "leads", "crm", "mql", "oportunidade", "contrato"]


class MetaAdsCockpitMetas(BaseModel):
    cpl: float
    taxaMql: float
    custoMqlImplicito: float
    cplFator: float


class MetaAdsCockpitSelos(BaseModel):
    cpl: SeloCockpit
    taxaMql: SeloCockpit
    custoMql: SeloCockpit
    saude: SeloCockpit


class MetaAdsCockpitEtapa(BaseModel):
    """Degrau do funil. `taxa` e contra a etapa anterior (None na primeira); `custo` e o custo de chegar ali."""

    chave: EtapaFunilCockpit
    quantidade: int
    taxa: float | None
    custo: float | None
    gargalo: bool


class MetaAdsCockpitPonto(BaseModel):
    inicio: date
    fim: date
    rotulo: str
    investimento: float
    impressoes: int
    cliques: int
    leadsMeta: int
    leadsCrm: int
    mqls: int
    cpl: float | None


class MetaAdsCockpitCriativo(BaseModel):
    id: int | None
    mcgId: int | None
    nome: str
    campanha: str
    status: str | None
    ativo: bool
    investimento: float
    leadsMeta: int
    leadsCrm: int
    mqls: int
    cpl: float | None
    taxaMql: float | None
    quadrante: QuadranteCockpit
    motivo: Literal["sem_lead", "sem_crm"] | None
    amostraPequena: bool
    recomendacao: str
    porque: str


class MetaAdsCockpitOperacao(BaseModel):
    cobertura: float | None
    horasPrimeiroContato: float | None
    alertasAbertos: int
    origemRevisar: int


class MetaAdsCockpitResponse(BaseModel):
    temConta: bool
    inicio: date
    fim: date
    metas: MetaAdsCockpitMetas
    total: MetaAdsLinha
    taxaMql: float | None
    anterior: MetaAdsLinha
    anteriorInicio: date
    anteriorFim: date
    anteriorTemDados: bool
    selos: MetaAdsCockpitSelos
    funil: list[MetaAdsCockpitEtapa]
    gargalo: Literal["mql", "oportunidade", "contrato"] | None
    fraseGargalo: str | None
    intervalo: Literal["mes", "semana"]
    serie: list[MetaAdsCockpitPonto]
    criativos: list[MetaAdsCockpitCriativo]
    operacao: MetaAdsCockpitOperacao


class MetaAdsCockpitLeituraTexto(BaseModel):
    manchete: str
    funciona: str
    problema: str
    olharAgora: str


class MetaAdsCockpitLeituraResponse(BaseModel):
    """Leitura guardada do recorte. `texto` leva a resposta crua quando a IA nao devolveu o JSON esperado."""

    leitura: MetaAdsCockpitLeituraTexto | None
    texto: str | None
    geradoEm: datetime | None
    desatualizada: bool
    aviso: str | None
    iaDisponivel: bool


class MetaAdsPerguntaMensagem(BaseModel):
    papel: str = Field(max_length=20)
    texto: str = Field(max_length=20_000)


class MetaAdsPerguntaRequest(BaseModel):
    dataInicial: date
    dataFinal: date
    macId: int | None = None
    somenteAtivas: bool = False
    pergunta: str = Field(min_length=1, max_length=500)
    historico: list[MetaAdsPerguntaMensagem] = Field(default_factory=list, max_length=50)

    @field_validator("pergunta", mode="before")
    @classmethod
    def _pergunta_sem_espacos(cls, valor):
        return valor.strip() if isinstance(valor, str) else valor


class MetaAdsPerguntaResponse(BaseModel):
    resposta: str
    restantesHoje: int
