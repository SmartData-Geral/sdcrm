"""Schemas da administracao de webhooks de saida."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class WebhookAssinaturaCreate(BaseModel):
    whaNome: str = Field(..., min_length=2, max_length=120)
    whaUrl: str = Field(..., min_length=8, max_length=600)
    eventos: Optional[list[str]] = Field(default=None, description='Lista de ids, ou ["*"]')
    whaHeadersJson: Optional[dict] = None


class WebhookAssinaturaUpdate(BaseModel):
    whaNome: Optional[str] = Field(default=None, min_length=2, max_length=120)
    whaUrl: Optional[str] = Field(default=None, min_length=8, max_length=600)
    eventos: Optional[list[str]] = None
    whaAtivo: Optional[bool] = None


class WebhookAssinaturaResponse(BaseModel):
    """Nunca devolve whaSegredo -- ele so aparece na criacao e na rotacao."""

    whaId: int
    whaEmpId: int
    whaNome: str
    whaUrl: str
    whaEventosJson: list
    whaFalhasConsecutivas: int
    whaDesativadaEm: Optional[datetime]
    whaDesativadaMotivo: Optional[str]
    whaUltimaEntregaEm: Optional[datetime]
    whaUltimoStatusHttp: Optional[int]
    whaAtivo: bool
    whaDataCriacao: datetime

    class Config:
        from_attributes = True


class WebhookAssinaturaCriadaResponse(BaseModel):
    assinatura: WebhookAssinaturaResponse
    segredo: str
    aviso: str = "Guarde este segredo agora. Ele nao sera exibido novamente."


class WebhookAssinaturaListResponse(BaseModel):
    items: list[WebhookAssinaturaResponse]
    total: int
    page: int
    page_size: int


class WebhookEntregaResponse(BaseModel):
    wenId: int
    wenWevId: int
    wenWhaId: int
    wenStatus: str
    wenTentativas: int
    wenProximaTentativaEm: Optional[datetime]
    wenUltimaTentativaEm: Optional[datetime]
    wenUltimoStatusHttp: Optional[int]
    wenUltimoErro: Optional[str]
    wenRespostaTrecho: Optional[str]
    wenDuracaoMs: Optional[int]
    wenHistoricoJson: Optional[Any]
    wenDataEntrega: Optional[datetime]
    wenDataCriacao: datetime

    class Config:
        from_attributes = True


class WebhookEntregaListResponse(BaseModel):
    items: list[WebhookEntregaResponse]
    total: int
    page: int
    page_size: int


class EventoCatalogoItem(BaseModel):
    id: str
    prioridade: str
    rotulo: str
    descricao: str
    disponivel: bool
    motivo_indisponivel: Optional[str] = None


class EventoCatalogoResponse(BaseModel):
    items: list[EventoCatalogoItem]
