"""
Contrato externo da API de entrada de leads.

Campos em inglês e rota versionada de propósito: isto é consumido por Zapier e, no
futuro, por Meta Lead Ads e pelo formulário do site. As rotas internas do CRM seguem
em português, conforme docs/API_GUIDELINES.md.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from ..services.lead_normalizacao import normalizar_email, normalizar_telefone


class LeadIntakeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    # Obrigatório: o critério de aceite exige origem preenchida em 100% dos leads
    # criados, e a única forma de garantir isso é recusar o payload sem ela.
    source: str = Field(
        ..., min_length=2, max_length=60, validation_alias=AliasChoices("source", "origem")
    )
    external_id: Optional[str] = Field(default=None, max_length=120)
    name: Optional[str] = Field(
        default=None, max_length=200, validation_alias=AliasChoices("name", "nome")
    )
    company: Optional[str] = Field(
        default=None, max_length=200, validation_alias=AliasChoices("company", "empresa")
    )
    # Deliberadamente `str` e não `EmailStr`: um e-mail torto acompanhado de telefone
    # válido não é payload inválido, e recusar tudo perderia um lead pago. A validação
    # real acontece no validador abaixo.
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(
        default=None, max_length=50, validation_alias=AliasChoices("phone", "telefone")
    )
    utm_source: Optional[str] = Field(default=None, max_length=100)
    utm_medium: Optional[str] = Field(default=None, max_length=100)
    utm_campaign: Optional[str] = Field(default=None, max_length=150)
    utm_content: Optional[str] = Field(default=None, max_length=150)
    utm_term: Optional[str] = Field(default=None, max_length=150)
    notes: Optional[str] = Field(
        default=None, max_length=4000, validation_alias=AliasChoices("notes", "observacoes")
    )
    owner_email: Optional[str] = Field(default=None, max_length=255)
    # Ids da Meta (Lead Ads). Chegam crus, com prefixos como "ag:"; limpos em meta_ads/rastreio.
    meta_lead_id: Optional[str] = Field(default=None, max_length=60)
    campaign_id: Optional[str] = Field(default=None, max_length=60)
    adset_id: Optional[str] = Field(default=None, max_length=60)
    ad_id: Optional[str] = Field(default=None, max_length=60)
    value: Optional[float] = Field(default=None, ge=0)

    @model_validator(mode="before")
    @classmethod
    def _vazio_vira_nulo(cls, data):
        # Planilhas mandam "" e não null. Mesmo tratamento que schemas/oportunidade.py
        # já faz para o e-mail da oportunidade.
        if isinstance(data, dict):
            return {k: (None if isinstance(v, str) and not v.strip() else v) for k, v in data.items()}
        return data

    @model_validator(mode="after")
    def _exige_contato_utilizavel(self):
        if normalizar_email(self.email) is None and normalizar_telefone(self.phone) is None:
            raise ValueError(
                "Informe um e-mail válido ou um telefone com DDD. "
                "Recebido: email=%r, phone=%r" % (self.email, self.phone)
            )
        return self


class LeadIntakeResponse(BaseModel):
    """
    `lead_id` mantém o formato do contrato do quadro ("ld_193"). Como ele exige que
    o consumidor tire o prefixo para ter o id real, devolvemos `opportunity_id`
    também -- é o identificador de verdade dentro do CRM.
    """

    lead_id: str
    status: Literal["created", "updated"]
    opportunity_id: int
    deduped_by: Optional[Literal["external_id", "email", "phone"]] = None
    previous_cycle_lead_id: Optional[str] = None
    url: Optional[str] = None


class PingResponse(BaseModel):
    ok: bool = True
    company_id: int
    integration: str
    scopes: list[str]


class RastreioMetaItem(BaseModel):
    """Uma linha da planilha de formularios da Meta, usada so para ligar lead ja existente ao anuncio."""

    model_config = ConfigDict(str_strip_whitespace=True)

    meta_lead_id: str = Field(..., min_length=1, max_length=60)
    created_time: datetime
    campaign_id: Optional[str] = Field(default=None, max_length=60)
    adset_id: Optional[str] = Field(default=None, max_length=60)
    ad_id: Optional[str] = Field(default=None, max_length=60)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def _vazio_vira_nulo(cls, data):
        if isinstance(data, dict):
            return {k: (None if isinstance(v, str) and not v.strip() else v) for k, v in data.items()}
        return data


class RastreioMetaRequest(BaseModel):
    itens: list[RastreioMetaItem] = Field(..., max_length=500)


class RastreioMetaResponse(BaseModel):
    casados: int = 0
    nao_casados: int = 0
    ambiguos: int = 0
    ja_atribuidos: int = 0
