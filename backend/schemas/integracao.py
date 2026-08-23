"""Schemas da area administrativa de integracoes (chaves de API e log de requisicoes)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class IntegracaoChaveBase(BaseModel):
    ichNome: str = Field(..., min_length=2, max_length=120)
    ichDescricao: Optional[str] = Field(default=None, max_length=300)
    ichUsuResponsavelPadraoId: Optional[int] = None
    ichExpiraEm: Optional[datetime] = None


class IntegracaoChaveCreate(IntegracaoChaveBase):
    escopos: Optional[list[str]] = Field(default=None)


class IntegracaoChaveResponse(BaseModel):
    """Nunca inclui o segredo -- so o prefixo publico, que identifica sem permitir uso."""

    ichId: int
    ichEmpId: int
    ichNome: str
    ichDescricao: Optional[str]
    ichPrefixo: str
    ichEscopos: str
    ichUsuResponsavelPadraoId: Optional[int]
    ichUltimoUsoEm: Optional[datetime]
    ichExpiraEm: Optional[datetime]
    ichRevogadaEm: Optional[datetime]
    ichAtivo: bool
    ichDataCriacao: datetime
    ichDataAtualizacao: Optional[datetime]

    class Config:
        from_attributes = True


class IntegracaoChaveCriadaResponse(BaseModel):
    """
    Resposta da criacao: e a UNICA vez em que a chave em texto puro existe.
    Ela nao e persistida e so pode ser substituida por revogacao e reemissao.
    """

    chave: IntegracaoChaveResponse
    apiKey: str
    aviso: str = "Guarde esta chave agora. Ela nao sera exibida novamente."


class IntegracaoChaveListResponse(BaseModel):
    items: list[IntegracaoChaveResponse]
    total: int
    page: int
    page_size: int


class IntegracaoLogResponse(BaseModel):
    irlId: int
    irlEmpId: Optional[int]
    irlIchId: Optional[int]
    irlPrefixoInformado: Optional[str]
    irlRota: str
    irlMetodo: str
    irlOrigemSistema: Optional[str]
    irlExternalId: Optional[str]
    irlStatusHttp: int
    irlResultado: str
    irlOpoId: Optional[int]
    irlPayloadJson: Optional[Any]
    irlErroJson: Optional[Any]
    irlIp: Optional[str]
    irlUserAgent: Optional[str]
    irlDuracaoMs: Optional[int]
    irlDataCriacao: datetime

    class Config:
        from_attributes = True


class IntegracaoLogListResponse(BaseModel):
    items: list[IntegracaoLogResponse]
    total: int
    page: int
    page_size: int


class EscopoCatalogoResponse(BaseModel):
    escopos: list[str]
