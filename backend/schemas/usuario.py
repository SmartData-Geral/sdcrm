from datetime import datetime
from typing import List

from pydantic import BaseModel, EmailStr, Field


class UsuarioCreate(BaseModel):
    usuNome: str = Field(..., max_length=200)
    usuEmail: EmailStr
    usuSenha: str = Field(..., min_length=6)
    usuAdmin: bool = False
    usuPerfil: str | None = Field(default=None, max_length=50)
    usuAvatarUrl: str | None = Field(default=None, max_length=500)
    empresasIds: List[int] = Field(default_factory=list, description="Ids das empresas vinculadas (para perfil USER)")


class UsuarioUpdate(BaseModel):
    usuNome: str | None = Field(default=None, max_length=200)
    usuEmail: EmailStr | None = None
    usuSenha: str | None = Field(default=None, min_length=6)
    usuAdmin: bool | None = None
    usuPerfil: str | None = Field(default=None, max_length=50)
    usuAvatarUrl: str | None = Field(default=None, max_length=500)
    usuAtivo: bool | None = None
    empresasIds: List[int] | None = Field(
        default=None, description="Ids das empresas vinculadas (para perfil USER)"
    )


class UsuarioInDBBase(BaseModel):
    usuId: int
    usuNome: str
    usuEmail: str
    usuAdmin: bool
    usuAtivo: bool
    usuPerfil: str | None = None
    usuAvatarUrl: str | None = None
    usuDataCriacao: datetime | None = None
    usuDataAtualizacao: datetime | None = None

    class Config:
        from_attributes = True


class UsuarioResponse(UsuarioInDBBase):
    # Para listagem: nomes das empresas vinculadas (se USER)
    empresas: list[str] | None = None


class UsuarioListResponse(BaseModel):
    items: list[UsuarioResponse]
    total: int
    page: int
    page_size: int
