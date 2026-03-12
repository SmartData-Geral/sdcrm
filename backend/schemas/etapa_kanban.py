from datetime import datetime

from pydantic import BaseModel, Field


class EtapaKanbanBase(BaseModel):
    etkNome: str = Field(..., max_length=100)
    etkOrdem: int = 0
    etkPipeline: str = Field(default="default", max_length=100)
    etkCor: str | None = Field(default=None, max_length=20)


class EtapaKanbanCreate(EtapaKanbanBase):
    pass


class EtapaKanbanUpdate(BaseModel):
    etkNome: str | None = Field(default=None, max_length=100)
    etkOrdem: int | None = None
    etkPipeline: str | None = Field(default=None, max_length=100)
    etkCor: str | None = Field(default=None, max_length=20)
    etkAtivo: bool | None = None


class EtapaKanbanInDBBase(EtapaKanbanBase):
    etkId: int
    etkEmpId: int
    etkAtivo: bool
    etkDataCriacao: datetime
    etkDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class EtapaKanbanResponse(EtapaKanbanInDBBase):
    pass


class EtapaKanbanListResponse(BaseModel):
    items: list[EtapaKanbanResponse]
    total: int
    page: int
    page_size: int
