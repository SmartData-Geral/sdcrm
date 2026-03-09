from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .exceptions import AuthenticationError
from .models.usuario import Usuario

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str | int, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": datetime.now(timezone.utc) + expires_delta,
        "type": "access",
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str | int, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": datetime.now(timezone.utc) + expires_delta,
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise AuthenticationError("Token inválido ou expirado")


def get_current_user_from_token(token: str, db: Session) -> Usuario:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise AuthenticationError("Tipo de token inválido")
    sub = payload.get("sub")
    if sub is None:
        raise AuthenticationError("Token inválido")

    user = db.get(Usuario, int(sub))
    if user is None or not user.usuAtivo:
        raise AuthenticationError("Usuário não encontrado ou inativo")
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    return get_current_user_from_token(token, db)

