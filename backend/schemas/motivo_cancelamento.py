from datetime import datetime

from pydantic import BaseModel, Field


class MotivoCancelamentoBase(BaseModel):
    mcaNome: str = Field(..., max_length=200)


class MotivoCancelamentoCreate(MotivoCancelamentoBase):
    pass


class MotivoCancelamentoUpdate(BaseModel):
    mcaNome: str | None = Field(default=None, max_length=200)
    mcaAtivo: bool | None = None


class MotivoCancelamentoInDBBase(MotivoCancelamentoBase):
    mcaId: int
    mcaEmpId: int
    mcaAtivo: bool
    mcaDataCriacao: datetime
    mcaDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class MotivoCancelamentoResponse(MotivoCancelamentoInDBBase):
    pass


class MotivoCancelamentoListResponse(BaseModel):
    items: list[MotivoCancelamentoResponse]
    total: int
    page: int
    page_size: int
