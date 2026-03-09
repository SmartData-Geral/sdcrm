from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ClienteBase(BaseModel):
    cliNome: str = Field(..., max_length=200)
    cliEmail: EmailStr | None = None
    cliTelefone: str | None = Field(default=None, max_length=50)
    cliAtivo: bool = True


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    cliNome: str | None = Field(default=None, max_length=200)
    cliEmail: EmailStr | None = None
    cliTelefone: str | None = Field(default=None, max_length=50)
    cliAtivo: bool | None = None


class ClienteInDBBase(ClienteBase):
    cliId: int
    cliEmpId: int | None
    cliDataCriacao: datetime
    cliDataAtualizacao: datetime | None

    class Config:
        from_attributes = True


class ClienteResponse(ClienteInDBBase):
    pass


class ClienteListResponse(BaseModel):
    items: list[ClienteResponse]
    total: int
    page: int
    page_size: int

