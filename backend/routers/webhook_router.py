"""Administracao dos webhooks de saida. JWT + admin, convencao interna em portugues."""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from ..core.tempo import utcnow
from ..dependencies import (
    CompanyIdDep,
    CurrentUserDep,
    DbSessionDep,
    require_admin,
    require_user_in_company,
)
from ..exceptions import NotFoundError
from ..models.webhook_entrega import WebhookEntrega
from ..schemas.webhook import (
    EventoCatalogoItem,
    EventoCatalogoResponse,
    WebhookAssinaturaCreate,
    WebhookAssinaturaCriadaResponse,
    WebhookAssinaturaListResponse,
    WebhookAssinaturaResponse,
    WebhookAssinaturaUpdate,
    WebhookEntregaListResponse,
    WebhookEntregaResponse,
)
from ..services import webhook_assinatura_service, webhook_emitter, webhook_eventos

router = APIRouter(tags=["webhooks"])


def _guarda(db, current_user, company_id) -> None:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    require_admin(current_user)


@router.get("/api/webhooks/eventos", response_model=EventoCatalogoResponse)
def catalogo(current_user: CurrentUserDep) -> EventoCatalogoResponse:
    """
    Catalogo vindo do backend para a UI nunca listar um evento que nao existe.
    task.completed aparece com disponivel=false e o motivo -- e melhor exibi-lo
    esmaecido do que o time achar que quebrou.
    """
    require_admin(current_user)
    return EventoCatalogoResponse(
        items=[EventoCatalogoItem(**vars(e)) for e in webhook_eventos.CATALOGO]
    )


@router.get("/api/webhooks", response_model=WebhookAssinaturaListResponse)
def listar(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filtro: Literal["ativos", "inativos", "todos"] = Query(default="todos", alias="status"),
) -> WebhookAssinaturaListResponse:
    _guarda(db, current_user, company_id)
    itens, total = webhook_assinatura_service.listar(db, company_id, status_filtro, page, page_size)
    return WebhookAssinaturaListResponse(
        items=[WebhookAssinaturaResponse.model_validate(i) for i in itens],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/api/webhooks",
    response_model=WebhookAssinaturaCriadaResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar(
    data: WebhookAssinaturaCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> WebhookAssinaturaCriadaResponse:
    _guarda(db, current_user, company_id)
    registro, segredo = webhook_assinatura_service.criar(
        db,
        company_id=company_id,
        nome=data.whaNome,
        url=data.whaUrl,
        eventos=data.eventos,
        headers=data.whaHeadersJson,
    )
    return WebhookAssinaturaCriadaResponse(
        assinatura=WebhookAssinaturaResponse.model_validate(registro), segredo=segredo
    )


@router.put("/api/webhooks/{wha_id}", response_model=WebhookAssinaturaResponse)
def atualizar(
    wha_id: int,
    data: WebhookAssinaturaUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> WebhookAssinaturaResponse:
    _guarda(db, current_user, company_id)
    registro = webhook_assinatura_service.atualizar(
        db, wha_id, company_id, nome=data.whaNome, url=data.whaUrl, eventos=data.eventos, ativo=data.whaAtivo
    )
    return WebhookAssinaturaResponse.model_validate(registro)


@router.post("/api/webhooks/{wha_id}/rotacionar-segredo", response_model=WebhookAssinaturaCriadaResponse)
def rotacionar(
    wha_id: int, db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> WebhookAssinaturaCriadaResponse:
    _guarda(db, current_user, company_id)
    registro, segredo = webhook_assinatura_service.rotacionar_segredo(db, wha_id, company_id)
    return WebhookAssinaturaCriadaResponse(
        assinatura=WebhookAssinaturaResponse.model_validate(registro), segredo=segredo
    )


@router.post("/api/webhooks/{wha_id}/testar")
def testar(
    wha_id: int, db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> dict:
    """
    Dispara um evento sintetico para a assinatura, sem depender de um fato de negocio.
    E o que permite validar a configuracao do Catch Hook do Zapier na hora.
    """
    _guarda(db, current_user, company_id)
    from ..models.webhook_evento import WebhookEvento

    assinatura = webhook_assinatura_service.get(db, wha_id, company_id)
    evento = WebhookEvento(
        wevEmpId=assinatura.whaEmpId,
        wevTipo="lead.created",
        wevOpoId=None,
        wevPayloadJson={
            "object": "deal",
            "lead_id": "ld_0",
            "deal_id": 0,
            "title": "Evento de teste",
            "contact": {"name": "Teste", "email": "teste@exemplo.com", "phone": None},
            "_teste": True,
        },
        wevOrigem="sistema",
        wevStatus="pendente",
    )
    db.add(evento)
    db.commit()
    webhook_emitter.acordar_worker()
    return {"enfileirado": True, "wevId": evento.wevId, "assinatura": assinatura.whaNome}


@router.get("/api/webhooks/{wha_id}/entregas", response_model=WebhookEntregaListResponse)
def entregas(
    wha_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filtro: Optional[str] = Query(default=None, alias="status"),
) -> WebhookEntregaListResponse:
    _guarda(db, current_user, company_id)
    webhook_assinatura_service.get(db, wha_id, company_id)
    stmt = select(WebhookEntrega).where(WebhookEntrega.wenWhaId == wha_id)
    if company_id is not None:
        stmt = stmt.where(WebhookEntrega.wenEmpId == company_id)
    if status_filtro:
        stmt = stmt.where(WebhookEntrega.wenStatus == status_filtro)
    stmt = stmt.order_by(WebhookEntrega.wenDataCriacao.desc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    itens = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all())
    return WebhookEntregaListResponse(
        items=[WebhookEntregaResponse.model_validate(i) for i in itens],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/api/webhooks/entregas/{wen_id}/reenviar", response_model=WebhookEntregaResponse)
def reenviar(
    wen_id: int, db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> WebhookEntregaResponse:
    _guarda(db, current_user, company_id)
    entrega = db.get(WebhookEntrega, wen_id)
    if entrega is None or (company_id is not None and entrega.wenEmpId != company_id):
        raise NotFoundError("Entrega nao encontrada")
    entrega.wenStatus = "retentando"
    entrega.wenProximaTentativaEm = utcnow()
    entrega.wenClaimedPor = None
    entrega.wenClaimedEm = None
    db.add(entrega)
    db.commit()
    db.refresh(entrega)
    webhook_emitter.acordar_worker()
    return WebhookEntregaResponse.model_validate(entrega)
