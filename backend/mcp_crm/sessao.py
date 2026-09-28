"""
Identidade de cada chamada de ferramenta MCP.

O wrapper ASGI (autenticacao.py) valida a chave uma vez por requisição HTTP e injeta
o id dela em HEADER_ICH_ID. Aqui a chave é recarregada e revalidada a cada chamada,
para que revogar a chave corte o acesso mesmo com o conector já conectado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from ..models.integracao_chave import IntegracaoChave
from ..services import integracao_chave_service

HEADER_ICH_ID = "x-sdcrm-ich-id"
ESCOPO_LEITURA = "mcp:read"
ESCOPO_ESCRITA = "mcp:write"
ESCOPOS_MCP = frozenset({ESCOPO_LEITURA, ESCOPO_ESCRITA})

MENSAGEM_CHAVE_RECUSADA = "Chave de API invalida ou revogada"


class ErroMCP(Exception):
    """Falha de uso ou de permissão com mensagem pronta para o Claude."""

    def __init__(self, mensagem: str, status_http: int = 400, resultado: str = "bad_request") -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status_http = status_http
        self.resultado = resultado


@dataclass
class ContextoMCP:
    db: Session
    ichId: int
    empId: int
    nome: str
    escopos: frozenset[str]
    usuResponsavelPadraoId: int | None
    # Preenchido pela ferramenta quando ela descobre a oportunidade (ex.: criar_lead),
    # para o log de integração apontar para ela.
    opo_id: int | None = None


def escopos_da_chave(chave: Any) -> frozenset[str]:
    return frozenset(e.strip() for e in (chave.ichEscopos or "").split(",") if e.strip())


def ich_id_do_contexto(ctx: Any) -> int:
    headers = getattr(ctx, "headers", None) or {}
    valor = headers.get(HEADER_ICH_ID)
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise ErroMCP(
            "Requisição MCP sem autenticação. Verifique a URL do conector.",
            status_http=401,
            resultado="unauthorized",
        )


def carregar_contexto(db: Session, ich_id: int) -> ContextoMCP:
    chave = db.get(IntegracaoChave, ich_id)
    if chave is None or not integracao_chave_service.chave_utilizavel(chave):
        raise ErroMCP(MENSAGEM_CHAVE_RECUSADA, status_http=401, resultado="unauthorized")
    escopos = escopos_da_chave(chave)
    if not escopos & ESCOPOS_MCP:
        raise ErroMCP(MENSAGEM_CHAVE_RECUSADA, status_http=401, resultado="unauthorized")
    integracao_chave_service.registrar_uso(db, chave)
    db.commit()
    return ContextoMCP(
        db=db,
        ichId=chave.ichId,
        empId=chave.ichEmpId,
        nome=chave.ichNome,
        escopos=escopos,
        usuResponsavelPadraoId=chave.ichUsuResponsavelPadraoId,
    )
