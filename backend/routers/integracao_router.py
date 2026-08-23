"""
Administracao das integracoes: chaves de API e log de requisicoes.

Rotas internas -- convencao em portugues, autenticadas por JWT e restritas a admin.
Nao confundir com /api/v1/*, que e a superficie externa autenticada por chave.
"""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Query, status

from ..dependencies import (
    CompanyIdDep,
    CurrentUserDep,
    DbSessionDep,
    require_admin,
    require_user_in_company,
)
from ..schemas.integracao import (
    EscopoCatalogoResponse,
    IntegracaoChaveCreate,
    IntegracaoChaveCriadaResponse,
    IntegracaoChaveListResponse,
    IntegracaoChaveResponse,
    IntegracaoLogListResponse,
    IntegracaoLogResponse,
)
from ..services import integracao_chave_service, integracao_log_service

router = APIRouter(tags=["integracoes"])


@router.get("/api/integracao-chaves/escopos", response_model=EscopoCatalogoResponse)
def listar_escopos(current_user: CurrentUserDep) -> EscopoCatalogoResponse:
    require_admin(current_user)
    return EscopoCatalogoResponse(escopos=list(integracao_chave_service.ESCOPOS_CONHECIDOS))


@router.get("/api/integracao-chaves", response_model=IntegracaoChaveListResponse)
def listar_chaves(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filtro: Literal["ativos", "inativos", "todos"] = Query(default="todos", alias="status"),
) -> IntegracaoChaveListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    require_admin(current_user)
    itens, total = integracao_chave_service.listar_chaves(
        db, company_id=company_id, status=status_filtro, page=page, page_size=page_size
    )
    return IntegracaoChaveListResponse(
        items=[IntegracaoChaveResponse.model_validate(i) for i in itens],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/api/integracao-chaves",
    response_model=IntegracaoChaveCriadaResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_chave(
    data: IntegracaoChaveCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> IntegracaoChaveCriadaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    require_admin(current_user)
    registro, chave_plana = integracao_chave_service.criar_chave(
        db,
        company_id=company_id,
        nome=data.ichNome,
        descricao=data.ichDescricao,
        escopos=data.escopos,
        usu_responsavel_padrao_id=data.ichUsuResponsavelPadraoId,
        expira_em=data.ichExpiraEm,
        criada_usu_id=current_user.usuId,
    )
    return IntegracaoChaveCriadaResponse(
        chave=IntegracaoChaveResponse.model_validate(registro),
        apiKey=chave_plana,
    )


@router.post("/api/integracao-chaves/{ich_id}/revogar", response_model=IntegracaoChaveResponse)
def revogar_chave(
    ich_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> IntegracaoChaveResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    require_admin(current_user)
    registro = integracao_chave_service.revogar_chave(db, ich_id, company_id, current_user.usuId)
    return IntegracaoChaveResponse.model_validate(registro)


@router.get("/api/integracao-logs", response_model=IntegracaoLogListResponse)
def listar_logs(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    resultado: Optional[str] = Query(default=None),
    ich_id: Optional[int] = Query(default=None),
    origem: Optional[str] = Query(default=None),
) -> IntegracaoLogListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    require_admin(current_user)
    itens, total = integracao_log_service.listar(
        db,
        company_id=company_id,
        resultado=resultado,
        ich_id=ich_id,
        origem=origem,
        page=page,
        page_size=page_size,
    )
    return IntegracaoLogListResponse(
        items=[IntegracaoLogResponse.model_validate(i) for i in itens],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/api/integracao-logs/expurgar")
def expurgar_logs(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    dias: Optional[int] = Query(default=None, ge=1, le=3650),
) -> dict:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    require_admin(current_user)
    return {"removidos": integracao_log_service.expurgar(db, dias)}
