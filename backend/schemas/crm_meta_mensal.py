from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _primeiro_dia_mes(value: date) -> date:
    return date(value.year, value.month, 1)


class CrmMetaMensalCreate(BaseModel):
    cmmMesReferencia: date
    cmmQtdRecebimento: int = Field(..., ge=0)
    cmmTaxaConversao: Decimal = Field(..., ge=0, le=1)
    cmmMrrMedio: Decimal = Field(..., ge=Decimal("0"))

    @field_validator("cmmMesReferencia")
    @classmethod
    def normaliza_mes_referencia(cls, v: date) -> date:
        return _primeiro_dia_mes(v)


class CrmMetaMensalUpdate(BaseModel):
    cmmMesReferencia: date | None = None
    cmmQtdRecebimento: int | None = Field(default=None, ge=0)
    cmmTaxaConversao: Decimal | None = Field(default=None, ge=0, le=1)
    cmmMrrMedio: Decimal | None = Field(default=None, ge=Decimal("0"))

    @field_validator("cmmMesReferencia")
    @classmethod
    def normaliza_mes_referencia(cls, v: date | None) -> date | None:
        return _primeiro_dia_mes(v) if v is not None else None


class CrmMetaMensalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cmmId: int
    cmmEmpId: int
    cmmMesReferencia: date
    cmmQtdRecebimento: int
    cmmTaxaConversao: Decimal
    cmmMrrMedio: Decimal
    cmmQtdFechamento: int
    cmmMrrIncremental: Decimal
    cmmDataCriacao: datetime
    cmmDataAtualizacao: datetime | None


class CrmMetaMensalListResponse(BaseModel):
    items: list[CrmMetaMensalResponse]
    total: int
    page: int
    page_size: int


class CrmMetaMensalResumoResponse(BaseModel):
    items: list[CrmMetaMensalResponse]
    ano: int
