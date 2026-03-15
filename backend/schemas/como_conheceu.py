from datetime import datetime

from pydantic import BaseModel, Field


class ComoConheceuBase(BaseModel):
    ccoNome: str = Field(..., max_length=200)
    ccoGrupo: str | None = Field(default=None, max_length=100)


class ComoConheceuCreate(ComoConheceuBase):
    pass


class ComoConheceuUpdate(BaseModel):
    ccoNome: str | None = Field(default=None, max_length=200)
    ccoGrupo: str | None = Field(default=None, max_length=100)
    ccoAtivo: bool | None = None


class ComoConheceuInDBBase(ComoConheceuBase):
    ccoId: int
    ccoEmpId: int
    ccoAtivo: bool
    ccoDataCriacao: datetime
    ccoDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class ComoConheceuResponse(ComoConheceuInDBBase):
    pass


class ComoConheceuListResponse(BaseModel):
    items: list[ComoConheceuResponse]
    total: int
    page: int
    page_size: int
