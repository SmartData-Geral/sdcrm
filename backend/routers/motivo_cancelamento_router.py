from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..schemas.motivo_cancelamento import (
    MotivoCancelamentoCreate,
    MotivoCancelamentoListResponse,
    MotivoCancelamentoResponse,
    MotivoCancelamentoUpdate,
)
from ..services import motivo_cancelamento_service

router = APIRouter(prefix="/api/motivos-cancelamento", tags=["motivos-cancelamento"])


@router.get("", response_model=MotivoCancelamentoListResponse)
def listar(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    nome: Optional[str] = Query(default=None),
    status: Literal["ativos", "inativos", "todos"] = Query(default="ativos"),
) -> MotivoCancelamentoListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return motivo_cancelamento_service.list_motivos_cancelamento(
        db, company_id=company_id, nome=nome, status=status, page=page, page_size=page_size
    )


@router.get("/{mca_id}", response_model=MotivoCancelamentoResponse)
def obter(
    mca_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> MotivoCancelamentoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return motivo_cancelamento_service.get_motivo_cancelamento(db, mca_id, company_id)


@router.post("", response_model=MotivoCancelamentoResponse, status_code=status.HTTP_201_CREATED)
def criar(
    data: MotivoCancelamentoCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> MotivoCancelamentoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return motivo_cancelamento_service.create_motivo_cancelamento(db, data, company_id)


@router.put("/{mca_id}", response_model=MotivoCancelamentoResponse)
def atualizar(
    mca_id: int,
    data: MotivoCancelamentoUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> MotivoCancelamentoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return motivo_cancelamento_service.update_motivo_cancelamento(db, mca_id, data, company_id)


@router.patch("/{mca_id}/ativar", response_model=MotivoCancelamentoResponse)
def ativar(
    mca_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> MotivoCancelamentoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return motivo_cancelamento_service.set_motivo_cancelamento_ativo(db, mca_id, True, company_id)


@router.patch("/{mca_id}/inativar", response_model=MotivoCancelamentoResponse)
def inativar(
    mca_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> MotivoCancelamentoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return motivo_cancelamento_service.set_motivo_cancelamento_ativo(db, mca_id, False, company_id)
