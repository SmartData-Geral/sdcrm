"""
Cifra simetrica (Fernet) para segredos guardados no banco, como o token do Meta Ads.

Formato gravado: "enc:v1:<token Fernet>". A chave e o SHA-256 de SECRETS_ENCRYPTION_KEY,
ou do JWT_SECRET_KEY quando a primeira nao esta definida (mesmo modelo do Adverse).
Trocar a semente torna os valores gravados ilegiveis: decifrar devolve None e quem chama
trata como "token precisa ser cadastrado de novo".
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings

PREFIXO = "enc:v1:"


def _fernet() -> Fernet:
    semente = settings.SECRETS_ENCRYPTION_KEY or settings.JWT_SECRET_KEY
    chave = base64.urlsafe_b64encode(hashlib.sha256(semente.encode("utf-8")).digest())
    return Fernet(chave)


def cifrar(texto: str) -> str:
    return PREFIXO + _fernet().encrypt(texto.encode("utf-8")).decode("ascii")


def decifrar(valor: str | None) -> str | None:
    """Texto puro, ou None se o valor nao for legivel (formato invalido ou chave trocada)."""
    if not valor or not valor.startswith(PREFIXO):
        return None
    try:
        return _fernet().decrypt(valor[len(PREFIXO):].encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None
