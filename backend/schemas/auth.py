from datetime import datetime

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: datetime
    type: str


class LoginRequest(BaseModel):
    email: str
    senha: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UsuarioBase(BaseModel):
    usuId: int
    usuNome: str
    usuEmail: str
    usuAdmin: bool
    usuAtivo: bool
    usuPerfil: str | None = None
    usuAvatarUrl: str | None = None

    class Config:
        from_attributes = True


class UsuarioMeResponse(UsuarioBase):
    pass

