"""
Wrapper ASGI do servidor MCP: valida a chave de integração antes do SDK.

A chave chega no primeiro segmento do caminho (/api/mcp/<chave>), porque o conector
personalizado do claude.ai não envia headers próprios, ou no header X-API-Key
(n8n, Claude Code). O id da chave validada segue para as ferramentas em HEADER_ICH_ID;
qualquer header x-sdcrm-* vindo de fora é descartado antes.
"""

from __future__ import annotations

import json

import anyio

from ..database import SessionLocal
from ..services import integracao_chave_service, integracao_log_service
from .sessao import ESCOPOS_MCP, HEADER_ICH_ID, MENSAGEM_CHAVE_RECUSADA, escopos_da_chave

MONTAGEM = "/api/mcp"
_PREFIXO_CHAVE = f"{integracao_chave_service.PREFIXO_LITERAL}_"


def caminho_efetivo(scope: dict) -> str:
    """Caminho dentro do mount. Mesmo tratamento do SDFin para root_path e proxy."""
    path = scope.get("path", "/") or "/"
    root = scope.get("root_path", "") or ""
    if root and path.startswith(root):
        return path[len(root):] or "/"
    if MONTAGEM + "/" in path:
        return path[path.index(MONTAGEM + "/") + len(MONTAGEM):]
    return path


def _header(scope: dict, nome: bytes) -> str | None:
    for chave, valor in scope.get("headers", []):
        if chave.lower() == nome:
            return valor.decode("latin-1")
    return None


def _ip(scope: dict) -> str | None:
    encaminhado = _header(scope, b"x-forwarded-for")
    if encaminhado:
        return encaminhado.split(",")[0].strip()[:64]
    cliente = scope.get("client")
    return cliente[0] if cliente else None


def autenticar_chave(
    valor: str | None, *, metodo: str, ip: str | None, user_agent: str | None
) -> int | None:
    """Id da chave se ela é válida e tem algum escopo mcp:*; senão loga e devolve None."""
    db = SessionLocal()
    try:
        chave = integracao_chave_service.autenticar(db, valor)
        if chave is not None and escopos_da_chave(chave) & ESCOPOS_MCP:
            return chave.ichId
        integracao_log_service.registrar(
            db,
            rota="mcp",
            metodo=metodo,
            status_http=401,
            resultado="unauthorized",
            prefixo_informado=integracao_chave_service.prefixo_para_log(valor),
            ip=ip,
            user_agent=user_agent,
        )
        return None
    finally:
        db.close()


class AutenticacaoMCPASGI:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        efetivo = caminho_efetivo(scope)
        segmento = efetivo.lstrip("/").split("/", 1)[0]
        if segmento.startswith(_PREFIXO_CHAVE):
            valor = segmento
            resto = efetivo[len("/" + segmento):] or "/"
        else:
            valor = _header(scope, b"x-api-key")
            resto = efetivo or "/"

        ich_id = await anyio.to_thread.run_sync(
            lambda: autenticar_chave(
                valor,
                metodo=scope.get("method", ""),
                ip=_ip(scope),
                user_agent=_header(scope, b"user-agent"),
            )
        )
        if ich_id is None:
            await self._negar(send)
            return

        headers = [
            (k, v)
            for k, v in scope.get("headers", [])
            if not k.lower().startswith(b"x-sdcrm-") and k.lower() != b"x-api-key"
        ]
        headers.append((HEADER_ICH_ID.encode(), str(ich_id).encode()))

        novo = dict(scope)
        novo["path"] = resto
        novo["raw_path"] = resto.encode()
        novo["root_path"] = ""
        novo["headers"] = headers
        await self.app(novo, receive, send)

    @staticmethod
    async def _negar(send) -> None:
        corpo = json.dumps({"detail": MENSAGEM_CHAVE_RECUSADA}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": corpo})
