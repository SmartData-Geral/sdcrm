from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RanStatus = Literal["pendente", "processando", "concluido", "erro"]
TemperaturaSugestao = Literal["frio", "morno", "quente"]


class ReuniaoAnaliseArquivoResumo(BaseModel):
    nome: str
    mime: str | None = None
    extensao: str | None = None
    tamanho_bytes: int = 0
    leitura_sucesso: bool
    mensagem: str | None = None
    conteudo_extraido: str | None = None


class ReuniaoAnaliseBase(BaseModel):
    ranTranscricao: str | None = None
    ranArquivosResumo: list[ReuniaoAnaliseArquivoResumo] | None = None
    ranResumo: str | None = None
    ranFeedbackIa: str | None = None
    ranLeadScoreSugerido: int | None = Field(default=None, ge=0, le=10)
    ranTemperaturaSugerida: TemperaturaSugestao | None = None
    ranDoresOportunidadesSugeridas: str | None = None
    ranObservacoesSugeridas: str | None = None
    ranProximosPassosSugeridos: str | None = None
    ranPromptUtilizado: str | None = None
    ranRespostaJson: dict | None = None
    ranModeloIa: str | None = None
    ranProcessadoEm: datetime | None = None
    ranStatus: RanStatus


class ReuniaoAnaliseCreateRequest(BaseModel):
    ranTranscricao: str | None = None


class ReuniaoAnaliseProcessResult(BaseModel):
    resumo_reuniao: str = ""
    feedback_ia: str = ""
    lead_score_sugerido: int | None = Field(default=None, ge=0, le=10)
    temperatura_sugerida: TemperaturaSugestao | None = None
    dores_oportunidades_sugeridas: str = ""
    observacoes_sugeridas: str = ""
    proximos_passos_sugeridos: str = ""


class ReuniaoAnaliseResponse(ReuniaoAnaliseBase):
    ranId: int
    ranEmpId: int
    ranOpoId: int
    ranUsuId: int | None
    ranAtivo: bool
    ranDataCriacao: datetime
    ranDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class ReuniaoAnaliseListResponse(BaseModel):
    items: list[ReuniaoAnaliseResponse]
    total: int
    page: int
    page_size: int
