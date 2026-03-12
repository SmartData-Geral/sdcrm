from datetime import datetime

from pydantic import BaseModel, Field


class EmpresaBase(BaseModel):
    empNome: str = Field(..., max_length=200)


class EmpresaCreate(EmpresaBase):
    pass


class EmpresaUpdate(BaseModel):
    empNome: str | None = Field(default=None, max_length=200)
    empAtivo: bool | None = None


class EmpresaResponse(BaseModel):
    empId: int
    empNome: str
    empAtivo: bool
    empDataCriacao: datetime | None = None
    empDataAtualizacao: datetime | None = None

    class Config:
        from_attributes = True


class EmpresaListResponse(BaseModel):
    items: list[EmpresaResponse]


class EmpresaListGestaoResponse(BaseModel):
    items: list[EmpresaResponse]
    total: int
    page: int
    page_size: int
