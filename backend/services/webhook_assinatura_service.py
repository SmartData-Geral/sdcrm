"""CRUD de assinaturas de webhook, com validacao anti-SSRF da URL de destino."""

from __future__ import annotations

import ipaddress
import socket
from typing import Literal, Optional
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.tempo import utcnow
from ..exceptions import BadRequestError, NotFoundError
from ..models.webhook_assinatura import WebhookAssinatura
from . import webhook_eventos, webhook_signature


def validar_url_destino(url: str) -> None:
    """
    Uma URL de webhook e um primitivo de requisicao server-side controlado pelo admin.
    Sem esta checagem, quem tiver acesso ao cadastro poderia fazer o CRM chamar
    169.254.169.254 (metadados da nuvem) ou servicos internos da rede.

    Roda na gravacao E de novo no envio -- o DNS pode mudar de resposta no meio
    (rebinding).
    """
    parsed = urlparse((url or "").strip())
    if parsed.scheme == "http" and not settings.DEBUG:
        raise BadRequestError("A URL do webhook precisa usar https.")
    if parsed.scheme not in ("http", "https"):
        raise BadRequestError("A URL do webhook precisa comecar com https://")

    host = parsed.hostname
    if not host:
        raise BadRequestError("URL de webhook invalida.")

    permitidos = [h.strip().lower() for h in (settings.WEBHOOK_HOSTS_PERMITIDOS or "").split(",") if h.strip()]
    if permitidos and host.lower() not in permitidos:
        raise BadRequestError("Host nao permitido para webhooks: " + host)

    try:
        enderecos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise BadRequestError("Nao foi possivel resolver o host do webhook: " + host)

    for info in enderecos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise BadRequestError(
                "O host do webhook resolve para um endereco interno (" + str(ip) + ")."
            )


def listar(
    db: Session,
    company_id: Optional[int],
    status: Literal["ativos", "inativos", "todos"] = "todos",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list, int]:
    stmt = select(WebhookAssinatura)
    if company_id is not None:
        stmt = stmt.where(WebhookAssinatura.whaEmpId == company_id)
    if status == "ativos":
        stmt = stmt.where(WebhookAssinatura.whaAtivo.is_(True))
    elif status == "inativos":
        stmt = stmt.where(WebhookAssinatura.whaAtivo.is_(False))
    stmt = stmt.order_by(WebhookAssinatura.whaDataCriacao.desc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt).all()), total


def get(db: Session, wha_id: int, company_id: Optional[int] = None) -> WebhookAssinatura:
    stmt = select(WebhookAssinatura).where(WebhookAssinatura.whaId == wha_id)
    if company_id is not None:
        stmt = stmt.where(WebhookAssinatura.whaEmpId == company_id)
    registro = db.scalars(stmt).first()
    if registro is None:
        raise NotFoundError("Assinatura de webhook nao encontrada")
    return registro


def criar(
    db: Session, *, company_id: int, nome: str, url: str, eventos: list[str] | None, headers: dict | None = None
) -> tuple[WebhookAssinatura, str]:
    """Devolve (registro, segredo). O segredo so aparece aqui -- exiba uma vez."""
    validar_url_destino(url)
    segredo = webhook_signature.gerar_segredo()
    registro = WebhookAssinatura(
        whaEmpId=company_id,
        whaNome=nome.strip(),
        whaUrl=url.strip(),
        whaSegredo=segredo,
        whaEventosJson=webhook_eventos.validar_lista(eventos),
        whaHeadersJson=headers or None,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro, segredo


def atualizar(
    db: Session, wha_id: int, company_id: Optional[int], *, nome=None, url=None, eventos=None, ativo=None
) -> WebhookAssinatura:
    registro = get(db, wha_id, company_id)
    if url is not None and url.strip() != registro.whaUrl:
        validar_url_destino(url)
        registro.whaUrl = url.strip()
    if nome is not None:
        registro.whaNome = nome.strip()
    if eventos is not None:
        registro.whaEventosJson = webhook_eventos.validar_lista(eventos)
    if ativo is not None:
        registro.whaAtivo = bool(ativo)
        if ativo:
            # Reativar limpa o contador da auto-desativacao.
            registro.whaFalhasConsecutivas = 0
            registro.whaDesativadaEm = None
            registro.whaDesativadaMotivo = None
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


def rotacionar_segredo(db: Session, wha_id: int, company_id: Optional[int]) -> tuple[WebhookAssinatura, str]:
    registro = get(db, wha_id, company_id)
    novo = webhook_signature.gerar_segredo()
    registro.whaSegredo = novo
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro, novo


def desativar_por_falhas(db: Session, registro: WebhookAssinatura) -> None:
    """Nao commita -- faz parte da transacao da entrega que falhou."""
    registro.whaAtivo = False
    registro.whaDesativadaEm = utcnow()
    registro.whaDesativadaMotivo = (
        str(registro.whaFalhasConsecutivas) + " falhas consecutivas de entrega."
    )
    db.add(registro)
