from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth
from ..database import get_db
from ..exceptions import AuthenticationError
from ..models.usuario import Usuario
from ..schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    Token,
    UsuarioMeResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = db.query(Usuario).filter(Usuario.usuEmail == data.email).first()
    if user is None or not auth.verify_password(data.senha, user.usuSenhaHash):
        raise AuthenticationError("E-mail ou senha inválidos")

    access_token_expires = timedelta(minutes=auth.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=auth.settings.REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = auth.create_access_token(user.usuId, access_token_expires)
    refresh_token = auth.create_refresh_token(user.usuId, refresh_token_expires)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
def refresh_token(data: RefreshTokenRequest, db: Session = Depends(get_db)) -> Token:
    payload = auth.decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise AuthenticationError("Tipo de token inválido")

    user_id = int(payload["sub"])
    user = db.get(Usuario, user_id)
    if user is None or not user.usuAtivo:
        raise AuthenticationError("Usuário não encontrado ou inativo")

    access_token = auth.create_access_token(user.usuId)
    refresh_token = auth.create_refresh_token(user.usuId)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UsuarioMeResponse)
def me(current_user: Usuario = Depends(auth.get_current_user)) -> UsuarioMeResponse:
    return UsuarioMeResponse.model_validate(current_user)

