from typing import Optional

from fastapi import APIRouter, Query, status

from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..schemas.crm_meta_mensal import (
    CrmMetaMensalCreate,
    CrmMetaMensalListResponse,
    CrmMetaMensalResponse,
    CrmMetaMensalResumoResponse,
    CrmMetaMensalUpdate,
)
from ..services import crm_meta_mensal_service

router = APIRouter(prefix="/api/crm/metas-mensais", tags=["crm-metas-mensais"])


@router.get("", response_model=CrmMetaMensalListResponse)
def listar(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    ano: Optional[int] = Query(default=None, ge=1900, le=2100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> CrmMetaMensalListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return crm_meta_mensal_service.list_metas(
        db,
        company_id=company_id,
        ano=ano,
        page=page,
        page_size=page_size,
    )


@router.get("/resumo", response_model=CrmMetaMensalResumoResponse)
def resumo(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    ano: int = Query(..., ge=1900, le=2100),
) -> CrmMetaMensalResumoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return crm_meta_mensal_service.list_resumo_ano(db, company_id=company_id, ano=ano)


@router.get("/{meta_id}", response_model=CrmMetaMensalResponse)
def obter(
    meta_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> CrmMetaMensalResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    row = crm_meta_mensal_service.get_meta(db, meta_id=meta_id, company_id=company_id)
    return CrmMetaMensalResponse.model_validate(row)


@router.post("", response_model=CrmMetaMensalResponse, status_code=status.HTTP_201_CREATED)
def criar(
    data: CrmMetaMensalCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> CrmMetaMensalResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return crm_meta_mensal_service.create_meta(db, company_id=company_id, data=data)


@router.put("/{meta_id}", response_model=CrmMetaMensalResponse)
def atualizar(
    meta_id: int,
    data: CrmMetaMensalUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> CrmMetaMensalResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return crm_meta_mensal_service.update_meta(db, meta_id=meta_id, company_id=company_id, data=data)


@router.delete("/{meta_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover(
    meta_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> None:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    crm_meta_mensal_service.delete_meta(db, meta_id=meta_id, company_id=company_id)
