from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

TipoProposta = Literal["projeto", "planos", "hibrida"]
StatusProposta = Literal["rascunho", "publicada", "enviada", "visualizada", "aceita", "recusada", "arquivada"]
TipoEventoProposta = Literal["abertura_link", "visualizacao", "clique_whatsapp", "aceite", "recusa", "copia_link"]


class PropostaBase(BaseModel):
    prpOpoId: int
    prpTplId: int | None = None
    prpTitulo: str = Field(..., max_length=300)
    prpTipo: TipoProposta
    prpUsuResponsavelId: int | None = None
    prpNomeContato: str | None = Field(default=None, max_length=200)
    prpEmailContato: EmailStr | None = None
    prpWhatsappContato: str | None = Field(default=None, max_length=50)
    prpObservacaoInterna: str | None = None
    prpJsonConfiguracao: dict | None = None

    @field_validator("prpEmailContato", mode="before")
    @classmethod
    def normalize_empty_email(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class PropostaCreate(PropostaBase):
    pass


class PropostaUpdate(BaseModel):
    prpTplId: int | None = None
    prpTitulo: str | None = Field(default=None, max_length=300)
    prpTipo: TipoProposta | None = None
    prpStatus: StatusProposta | None = None
    prpUsuEditorId: int | None = None
    prpUsuResponsavelId: int | None = None
    prpNomeContato: str | None = Field(default=None, max_length=200)
    prpEmailContato: EmailStr | None = None
    prpWhatsappContato: str | None = Field(default=None, max_length=50)
    prpObservacaoInterna: str | None = None
    prpJsonConfiguracao: dict | None = None

    @field_validator("prpEmailContato", mode="before")
    @classmethod
    def normalize_empty_email(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class PropostaPublicarRequest(BaseModel):
    forcar_nova_versao: bool = True


class PropostaInDBBase(BaseModel):
    prpId: int
    prpEmpId: int
    prpOpoId: int
    prpTplId: int | None
    prpTitulo: str
    prpTipo: TipoProposta
    prpStatus: str
    prpTokenPublico: str
    prpVersaoAtual: int | None
    prpUsuCriadorId: int | None
    prpUsuEditorId: int | None
    prpUsuResponsavelId: int | None
    prpNomeContato: str | None
    prpEmailContato: str | None
    prpWhatsappContato: str | None
    prpObservacaoInterna: str | None
    prpJsonConfiguracao: dict | None
    prpHtmlRenderizado: str | None
    prpPublicadaEm: datetime | None
    prpAceitaEm: datetime | None
    prpAtivo: bool
    prpDataCriacao: datetime
    prpDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class PropostaResponse(PropostaInDBBase):
    pass


class PropostaListResponse(BaseModel):
    items: list[PropostaResponse]
    total: int
    page: int
    page_size: int


class PropostaVersaoBase(BaseModel):
    prvTitulo: str | None = None
    prvJsonSnapshot: dict | None = None
    prvHtmlSnapshot: str | None = None
    prvPublicada: bool = False


class PropostaVersaoCreate(PropostaVersaoBase):
    pass


class PropostaVersaoResponse(PropostaVersaoBase):
    prvId: int
    prvEmpId: int
    prvPrpId: int
    prvNumero: int
    prvUsuId: int | None
    prvDataPublicacao: datetime | None
    prvAtivo: bool
    prvDataCriacao: datetime
    prvDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class PropostaVersaoListResponse(BaseModel):
    items: list[PropostaVersaoResponse]
    total: int
    page: int
    page_size: int


class PropostaTemplateBase(BaseModel):
    ptlNome: str = Field(..., max_length=200)
    ptlTipoSolucao: str | None = Field(default=None, max_length=120)
    ptlTipoProposta: TipoProposta
    ptlAtivo: bool = True
    ptlPadrao: bool = False
    ptlSchemaJson: dict | None = None
    ptlConfigJson: dict | None = None
    ptlPrpOrigemId: int | None = None


class PropostaTemplateCreate(PropostaTemplateBase):
    pass


class PropostaTemplateUpdate(BaseModel):
    ptlNome: str | None = Field(default=None, max_length=200)
    ptlTipoSolucao: str | None = Field(default=None, max_length=120)
    ptlTipoProposta: TipoProposta | None = None
    ptlAtivo: bool | None = None
    ptlPadrao: bool | None = None
    ptlSchemaJson: dict | None = None
    ptlConfigJson: dict | None = None
    ptlPrpOrigemId: int | None = None


class PropostaTemplateResponse(PropostaTemplateBase):
    ptlId: int
    ptlEmpId: int
    ptlDataCriacao: datetime
    ptlDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class PropostaSalvarComoTemplateRequest(BaseModel):
    ptlNome: str = Field(..., max_length=200)
    ptlTipoSolucao: str | None = Field(default=None, max_length=120)
    ptlTipoProposta: TipoProposta
    ptlAtivo: bool = True
    ptlPadrao: bool = False


class PropostaTemplateListResponse(BaseModel):
    items: list[PropostaTemplateResponse]
    total: int
    page: int
    page_size: int


class PropostaBlocoBase(BaseModel):
    pblTipo: str = Field(..., max_length=60)
    pblTitulo: str | None = Field(default=None, max_length=200)
    pblSubtitulo: str | None = Field(default=None, max_length=300)
    pblOrdem: int = 0
    pblVisivel: bool = True
    pblDadosJson: dict | None = None


class PropostaBlocoCreate(PropostaBlocoBase):
    pass


class PropostaBlocoUpdate(BaseModel):
    pblTipo: str | None = Field(default=None, max_length=60)
    pblTitulo: str | None = Field(default=None, max_length=200)
    pblSubtitulo: str | None = Field(default=None, max_length=300)
    pblOrdem: int | None = None
    pblVisivel: bool | None = None
    pblDadosJson: dict | None = None
    pblAtivo: bool | None = None


class PropostaBlocoReordenarRequest(BaseModel):
    pblOrdem: int


class PropostaBlocoVisibilidadeRequest(BaseModel):
    pblVisivel: bool


class PropostaBlocoResponse(PropostaBlocoBase):
    pblId: int
    pblEmpId: int
    pblPrpId: int
    pblAtivo: bool
    pblDataCriacao: datetime
    pblDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class PropostaBlocoListResponse(BaseModel):
    items: list[PropostaBlocoResponse]
    total: int
    page: int
    page_size: int


class PropostaEventoPublicoRequest(BaseModel):
    dados: dict | None = None


class PropostaEventoResponse(BaseModel):
    pevId: int
    pevEmpId: int
    pevPrpId: int
    pevPrvId: int | None
    pevTipo: str
    pevIp: str | None
    pevUserAgent: str | None
    pevDadosJson: dict | None
    pevDataEvento: datetime
    pevAtivo: bool
    pevDataCriacao: datetime
    pevDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class PropostaEventoListResponse(BaseModel):
    items: list[PropostaEventoResponse]
    total: int
    page: int
    page_size: int


class PropostaPublicaResumoResponse(BaseModel):
    prpId: int
    prpTitulo: str
    prpTipo: TipoProposta
    prpStatus: str
    prpPublicadaEm: datetime | None
    prpAceitaEm: datetime | None
    prpWhatsappContato: str | None
    prpHtmlRenderizado: str | None
    prpJsonConfiguracao: dict | None


