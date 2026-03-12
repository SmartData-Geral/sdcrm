from datetime import datetime

from pydantic import BaseModel, Field


class ProdutoBase(BaseModel):
    proNome: str = Field(..., max_length=200)
    proCor: str | None = Field(default=None, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$")


class ProdutoCreate(ProdutoBase):
    pass


class ProdutoUpdate(BaseModel):
    proNome: str | None = Field(default=None, max_length=200)
    proCor: str | None = Field(default=None, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$")
    proAtivo: bool | None = None


class ProdutoInDBBase(ProdutoBase):
    proId: int
    proEmpId: int
    proAtivo: bool
    proDataCriacao: datetime
    proDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class ProdutoResponse(ProdutoInDBBase):
    pass


class ProdutoListResponse(BaseModel):
    items: list[ProdutoResponse]
    total: int
    page: int
    page_size: int
