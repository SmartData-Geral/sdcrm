"""Peças compartilhadas pelas ferramentas."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from ...exceptions import BadRequestError, NotFoundError
from ...models.como_conheceu import ComoConheceu
from ...models.motivo_cancelamento import MotivoCancelamento
from ...models.oportunidade import Oportunidade
from ...models.produto import Produto
from ...models.usuario import Usuario
from ...models.usuario_empresa import UsuarioEmpresa
from ...services import oportunidade_service
from ..serializacao import carregar_nomes, oportunidade_completa
from ..sessao import ContextoMCP

FUSO = ZoneInfo("America/Sao_Paulo")
MAX_POR_PAGINA = 50


def hoje() -> date:
    return datetime.now(FUSO).date()


def limitar_pagina(pagina: int, por_pagina: int) -> tuple[int, int]:
    return max(1, pagina), min(max(1, por_pagina), MAX_POR_PAGINA)


def obter_oportunidade_ativa(sessao: ContextoMCP, opo_id: int) -> Oportunidade:
    """Inexistente, de outra empresa ou inativa: sempre a mesma resposta."""
    opo = oportunidade_service.get_oportunidade(sessao.db, opo_id, sessao.empId)
    if not opo.opoAtivo:
        raise NotFoundError("Oportunidade não encontrada")
    return opo


def responder_oportunidade(sessao: ContextoMCP, opo) -> dict:
    return oportunidade_completa(opo, carregar_nomes(sessao.db, [opo]))


def prefixar(sessao: ContextoMCP, texto: str) -> str:
    return f"[via MCP · {sessao.nome}] {texto.strip()}"


def _exigir(sessao: ContextoMCP, stmt, rotulo: str, valor: int) -> None:
    if sessao.db.scalar(stmt) is None:
        raise BadRequestError(f"{rotulo} {valor} não existe nesta empresa.")


def validar_produto(sessao: ContextoMCP, produto_id: int) -> None:
    _exigir(
        sessao,
        select(Produto.proId).where(
            Produto.proId == produto_id, Produto.proEmpId == sessao.empId, Produto.proAtivo.is_(True)
        ),
        "Produto",
        produto_id,
    )


def validar_origem(sessao: ContextoMCP, origem_id: int) -> None:
    _exigir(
        sessao,
        select(ComoConheceu.ccoId).where(
            ComoConheceu.ccoId == origem_id,
            ComoConheceu.ccoEmpId == sessao.empId,
            ComoConheceu.ccoAtivo.is_(True),
        ),
        "Origem",
        origem_id,
    )


def validar_motivo(sessao: ContextoMCP, motivo_id: int) -> None:
    _exigir(
        sessao,
        select(MotivoCancelamento.mcaId).where(
            MotivoCancelamento.mcaId == motivo_id,
            MotivoCancelamento.mcaEmpId == sessao.empId,
            MotivoCancelamento.mcaAtivo.is_(True),
        ),
        "Motivo de perda",
        motivo_id,
    )


def validar_responsavel(sessao: ContextoMCP, usuario_id: int) -> None:
    _exigir(
        sessao,
        select(Usuario.usuId)
        .join(UsuarioEmpresa, UsuarioEmpresa.useUsuId == Usuario.usuId)
        .where(
            Usuario.usuId == usuario_id,
            UsuarioEmpresa.useEmpId == sessao.empId,
            Usuario.usuAtivo.is_(True),
        ),
        "Responsável",
        usuario_id,
    )
