from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


StatusContrato = Literal["pronto", "assinado"]


class ContratoCreate(BaseModel):
    ctrOpoId: int | None = None
    ctrCtmId: int | None = None

    ctrNome: str | None = Field(default=None, max_length=200)

    ctrRazaoSocial: str = Field(max_length=200)
    ctrCnpj: str = Field(max_length=20)
    ctrEndereco: str = Field(max_length=500)
    ctrResponsavelNome: str = Field(max_length=200)
    ctrResponsavelCpf: str = Field(max_length=20)

    ctrObjetoContrato: str
    ctrValorContrato: float
    ctrDataInicio: date
    ctrPrazoConclusao: str = Field(max_length=200)
    ctrDiasPagamento: int = Field(ge=0, le=3660)
    ctrDiasAntecedenciaRescisao: int = Field(ge=0, le=3660)
    ctrValorManutencao: float = Field(ge=0)
    ctrHorasMelhoriasMensais: int = Field(ge=0, le=744)


class ContratoInDBBase(BaseModel):
    ctrId: int
    ctrEmpId: int
    ctrOpoId: int | None
    ctrCtmId: int

    ctrNome: str
    ctrStatus: StatusContrato | str
    ctrTokenPublico: str | None

    ctrRazaoSocial: str
    ctrCnpj: str
    ctrEndereco: str
    ctrResponsavelNome: str
    ctrResponsavelCpf: str
    ctrObjetoContrato: str
    ctrValorContrato: float
    ctrDataInicio: date
    ctrPrazoConclusao: str
    ctrDiasPagamento: int
    ctrDiasAntecedenciaRescisao: int
    ctrValorManutencao: float
    ctrHorasMelhoriasMensais: int

    ctrHtmlSnapshot: str | None

    ctrAtivo: bool
    ctrDataCriacao: datetime
    ctrDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class ContratoResponse(ContratoInDBBase):
    pass


class ContratoUpdate(BaseModel):
    ctrNome: str | None = Field(default=None, max_length=200)
    ctrRazaoSocial: str | None = Field(default=None, max_length=200)
    ctrCnpj: str | None = Field(default=None, max_length=20)
    ctrEndereco: str | None = Field(default=None, max_length=500)
    ctrResponsavelNome: str | None = Field(default=None, max_length=200)
    ctrResponsavelCpf: str | None = Field(default=None, max_length=20)
    ctrObjetoContrato: str | None = None
    ctrValorContrato: float | None = None
    ctrDataInicio: date | None = None
    ctrPrazoConclusao: str | None = Field(default=None, max_length=200)
    ctrDiasPagamento: int | None = Field(default=None, ge=0, le=3660)
    ctrDiasAntecedenciaRescisao: int | None = Field(default=None, ge=0, le=3660)
    ctrValorManutencao: float | None = Field(default=None, ge=0)
    ctrHorasMelhoriasMensais: int | None = Field(default=None, ge=0, le=744)


class ContratoListResponse(BaseModel):
    items: list[ContratoResponse]
    total: int
    page: int
    page_size: int


class ContratoMacroItem(BaseModel):
    """Macro disponível para uso nos textos do modelo de contrato (sintaxe {{chave}})."""

    key: str
    titulo: str
    descricao: str


class ContratoMacroListResponse(BaseModel):
    items: list[ContratoMacroItem]


class ContratoClausulaVariacaoResponse(BaseModel):
    cmvId: int
    cmvNome: str | None
    cmvTitulo: str | None
    cmvTexto: str
    cmvAtivo: bool

    class Config:
        from_attributes = True


class ContratoClausulaResponse(BaseModel):
    cclId: int
    cclCmcId: int
    cclCmvId: int | None
    cclTitulo: str
    cclTexto: str
    cclUtilizar: bool
    cclOrdemBase: int
    cclOrdemFinal: int
    cclAtivo: bool

    # Valores da versão padrão (base) para o front alternar facilmente.
    cmcTituloPadrao: str
    cmcTextoPadrao: str

    # Variações ativas disponíveis para o usuário escolher.
    variacoes: list[ContratoClausulaVariacaoResponse]

    class Config:
        from_attributes = True


class ContratoClausulaUpdate(BaseModel):
    cclUtilizar: bool | None = None
    cclCmvId: int | None = None

    # Edição do snapshot do contrato (não altera o modelo base).
    cclTitulo: str | None = None
    cclTexto: str | None = None


class ContratoSalvarComoVariacaoRequest(BaseModel):
    cmvNome: str | None = None


# =========================
# Modelo de contrato (cadastros)
# =========================


class ContratoModeloBase(BaseModel):
    ctmNome: str = Field(..., max_length=200)
    ctmDescricao: str | None = Field(default=None)
    ctmAtivo: bool = True


class ContratoModeloCreate(ContratoModeloBase):
    pass


class ContratoModeloUpdate(BaseModel):
    ctmNome: str | None = Field(default=None, max_length=200)
    ctmDescricao: str | None = None
    ctmAtivo: bool | None = None


class ContratoModeloResponse(ContratoModeloBase):
    ctmId: int
    ctmEmpId: int
    ctmDataCriacao: datetime
    ctmDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class ContratoModeloListResponse(BaseModel):
    items: list[ContratoModeloResponse]
    total: int
    page: int
    page_size: int


# =========================
# Cláusulas do modelo
# =========================


class ContratoModeloClausulaCreate(BaseModel):
    cmcTitulo: str = Field(..., max_length=200)
    cmcTextoPadrao: str = Field(..., min_length=1)
    cmcUtilizarPadrao: bool = True
    cmcOrdem: int | None = None
    cmcAtivo: bool = True


class ContratoModeloClausulaUpdate(BaseModel):
    cmcTitulo: str | None = Field(default=None, max_length=200)
    cmcTextoPadrao: str | None = None
    cmcUtilizarPadrao: bool | None = None
    cmcOrdem: int | None = None
    cmcAtivo: bool | None = None


class ContratoModeloClausulaReordenarRequest(BaseModel):
    cmcOrdem: int = Field(..., ge=0)


class ContratoModeloClausulaResponse(BaseModel):
    cmcId: int
    cmcEmpId: int
    cmcCtmId: int
    cmcTitulo: str
    cmcTextoPadrao: str
    cmcUtilizarPadrao: bool
    cmcOrdem: int
    cmcAtivo: bool
    cmcDataCriacao: datetime
    cmcDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


# =========================
# Variações de cláusula (do modelo)
# =========================


class ContratoModeloClausulaVariacaoCreate(BaseModel):
    cmvNome: str | None = Field(default=None, max_length=200)
    cmvTitulo: str | None = Field(default=None, max_length=200)
    cmvTexto: str = Field(..., min_length=1)
    cmvAtivo: bool = True


class ContratoModeloClausulaVariacaoUpdate(BaseModel):
    cmvNome: str | None = Field(default=None, max_length=200)
    cmvTitulo: str | None = Field(default=None, max_length=200)
    cmvTexto: str | None = None
    cmvAtivo: bool | None = None


class ContratoModeloClausulaVariacaoResponse(BaseModel):
    cmvId: int
    cmvEmpId: int
    cmvCmcId: int
    cmvNome: str | None
    cmvTitulo: str | None
    cmvTexto: str
    cmvAtivo: bool
    cmvDataCriacao: datetime
    cmvDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class ContratoModeloClausulaVariacaoListResponse(BaseModel):
    items: list[ContratoModeloClausulaVariacaoResponse]

