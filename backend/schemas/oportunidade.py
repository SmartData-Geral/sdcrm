from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class OportunidadeBase(BaseModel):
    opoTitulo: str = Field(..., max_length=300)
    opoNomeContato: str | None = Field(default=None, max_length=200)
    opoEmpresaContato: str | None = Field(default=None, max_length=200)
    opoEmail: EmailStr | None = None
    opoTelefone: str | None = Field(default=None, max_length=50)
    opoSolucao: str | None = Field(default=None, max_length=500)
    opoProId: int | None = None
    opoEtkId: int | None = None
    opoUsuResponsavelId: int | None = None
    opoCcoId: int | None = None
    opoMcaId: int | None = None
    opoLeadScore: int | None = None
    opoTemperatura: str | None = Field(default=None, max_length=20)
    opoReuniaoConfirmada: bool = False
    opoPropostaEnviada: bool = False
    opoDataRecebimento: date | None = None
    opoValorOportunidade: float | None = None
    opoDataUltimoContato: date | None = None
    opoDataFechamento: date | None = None
    opoFechadoRecorrencia: int | None = Field(
        default=None, description="0 = recorrência, 1 = projeto"
    )
    opoValorFechado: float | None = None
    opoStatusFechamento: str | None = Field(default=None, max_length=20)
    opoDoresMotivadores: str | None = None
    opoComentarios: str | None = None


class OportunidadeCreate(OportunidadeBase):
    pass


class OportunidadeUpdate(BaseModel):
    opoTitulo: str | None = Field(default=None, max_length=300)
    opoNomeContato: str | None = Field(default=None, max_length=200)
    opoEmpresaContato: str | None = Field(default=None, max_length=200)
    opoEmail: EmailStr | None = None
    opoTelefone: str | None = Field(default=None, max_length=50)
    opoSolucao: str | None = Field(default=None, max_length=500)
    opoProId: int | None = None
    opoEtkId: int | None = None
    opoUsuResponsavelId: int | None = None
    opoCcoId: int | None = None
    opoMcaId: int | None = None
    opoLeadScore: int | None = None
    opoTemperatura: str | None = Field(default=None, max_length=20)
    opoReuniaoConfirmada: bool | None = None
    opoPropostaEnviada: bool | None = None
    opoDataRecebimento: date | None = None
    opoValorOportunidade: float | None = None
    opoDataUltimoContato: date | None = None
    opoDataFechamento: date | None = None
    opoFechadoRecorrencia: int | None = Field(
        default=None, description="0 = recorrência, 1 = projeto"
    )
    opoValorFechado: float | None = None
    opoStatusFechamento: str | None = Field(default=None, max_length=20)
    opoDoresMotivadores: str | None = None
    opoComentarios: str | None = None
    opoAtivo: bool | None = None


class OportunidadeInDBBase(OportunidadeBase):
    opoId: int
    opoEmpId: int
    opoAtivo: bool
    opoDataCriacao: datetime
    opoDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class OportunidadeResponse(OportunidadeInDBBase):
    pass


class OportunidadeListResponse(BaseModel):
    items: list[OportunidadeResponse]
    total: int
    page: int
    page_size: int


class OportunidadeMoverEtapaRequest(BaseModel):
    opoEtkId: int


class OportunidadeLeadScoreRequest(BaseModel):
    opoLeadScore: int


class OportunidadeTemperaturaRequest(BaseModel):
    opoTemperatura: str = Field(..., max_length=20)


class OportunidadeStandByRequest(BaseModel):
    opoDataUltimoContato: date


class OportunidadeGanharRequest(BaseModel):
    opoDataFechamento: date
    opoFechadoRecorrencia: int = Field(
        default=0, description="0 = recorrência, 1 = projeto"
    )
    opoValorFechado: float
