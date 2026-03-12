from datetime import datetime

from pydantic import BaseModel, Field


class OportunidadeHistoricoBase(BaseModel):
    ophConteudo: str | None = None


class OportunidadeHistoricoCreate(OportunidadeHistoricoBase):
    pass


class OportunidadeHistoricoUpdate(BaseModel):
    ophConteudo: str | None = None
    ophAtivo: bool | None = None


class OportunidadeHistoricoInDBBase(OportunidadeHistoricoBase):
    ophId: int
    ophEmpId: int
    ophOpoId: int
    ophUsuId: int | None
    ophDataRegistro: datetime
    ophAtivo: bool
    ophDataCriacao: datetime
    ophDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class OportunidadeHistoricoResponse(OportunidadeHistoricoInDBBase):
    pass


class OportunidadeHistoricoListResponse(BaseModel):
    items: list[OportunidadeHistoricoResponse]
    total: int
    page: int
    page_size: int
