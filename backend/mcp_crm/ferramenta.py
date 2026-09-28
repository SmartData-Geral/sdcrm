"""
Execução padronizada de uma ferramenta MCP.

Toda ferramenta faz:

    with executar_ferramenta(ctx, "nome", escrita=..., argumentos=dict(locals()), opo_id=...) as sessao:
        ...

É um gerenciador de contexto, e não um decorador, porque o SDK monta o esquema de
entrada lendo a assinatura da função registrada; um decorador que a trocasse quebraria
esse esquema.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError

from ..database import SessionLocal
from ..services import integracao_log_service
from .sessao import (
    ESCOPO_ESCRITA,
    ContextoMCP,
    ErroMCP,
    carregar_contexto,
    ich_id_do_contexto,
)

logger = logging.getLogger(__name__)

MENSAGEM_ERRO_INTERNO = "Erro interno ao executar a ferramenta."

_RESULTADO_POR_STATUS = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
}


def _mensagens_de_validacao(exc: ValidationError) -> str:
    partes = []
    for erro in exc.errors():
        msg = str(erro.get("msg", "")).removeprefix("Value error, ")
        local = ".".join(str(p) for p in erro.get("loc", ()) if p != "__root__")
        partes.append(f"{local}: {msg}" if local else msg)
    return "; ".join(partes) or "Parâmetros inválidos."


def traduzir_excecao(exc: BaseException) -> tuple[int, str, str]:
    """(status_http, resultado, mensagem para o Claude)."""
    if isinstance(exc, ErroMCP):
        return exc.status_http, exc.resultado, exc.mensagem
    if isinstance(exc, HTTPException):
        status = int(exc.status_code)
        return status, _RESULTADO_POR_STATUS.get(status, "error"), str(exc.detail)
    # ValidationError é subclasse de ValueError: precisa vir antes.
    if isinstance(exc, ValidationError):
        return 400, "bad_request", _mensagens_de_validacao(exc)
    if isinstance(exc, ValueError):
        return 400, "bad_request", str(exc)
    return 500, "error", MENSAGEM_ERRO_INTERNO


def exigir_escopo(sessao: ContextoMCP, escrita: bool) -> None:
    if escrita and ESCOPO_ESCRITA not in sessao.escopos:
        raise ErroMCP(
            "Esta chave não tem permissão de escrita (escopo mcp:write).",
            status_http=403,
            resultado="forbidden",
        )


@contextmanager
def executar_ferramenta(
    ctx: Any,
    nome: str,
    *,
    escrita: bool,
    argumentos: dict,
    opo_id: int | None = None,
) -> Iterator[ContextoMCP]:
    inicio = time.perf_counter()
    db = SessionLocal()
    sessao: ContextoMCP | None = None
    status_http, resultado, erro = 200, "ok", None
    try:
        try:
            sessao = carregar_contexto(db, ich_id_do_contexto(ctx))
            exigir_escopo(sessao, escrita)
            sessao.opo_id = opo_id
            yield sessao
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                logger.exception("Falha no rollback da ferramenta MCP %s", nome)
            status_http, resultado, mensagem = traduzir_excecao(exc)
            erro = {"detalhe": mensagem}
            if status_http >= 500:
                logger.exception("Erro inesperado na ferramenta MCP %s", nome)
            raise ToolError(mensagem) from exc
    finally:
        integracao_log_service.registrar(
            db,
            rota=f"mcp:{nome}",
            metodo="TOOL",
            status_http=status_http,
            resultado=resultado,
            emp_id=sessao.empId if sessao else None,
            ich_id=sessao.ichId if sessao else None,
            opo_id=sessao.opo_id if sessao else opo_id,
            payload=jsonable_encoder({k: v for k, v in (argumentos or {}).items() if k != "ctx"}),
            erro=erro,
            duracao_ms=int((time.perf_counter() - inicio) * 1000),
        )
        db.close()
