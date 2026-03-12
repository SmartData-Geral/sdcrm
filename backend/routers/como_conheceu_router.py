from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..schemas.como_conheceu import ComoConheceuCreate, ComoConheceuListResponse, ComoConheceuResponse, ComoConheceuUpdate
from ..services import como_conheceu_service

router = APIRouter(prefix="/api/como-conheceu", tags=["como-conheceu"])


@router.get("", response_model=ComoConheceuListResponse)
def listar(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    nome: Optional[str] = Query(default=None),
    status: Literal["ativos", "inativos", "todos"] = Query(default="ativos"),
) -> ComoConheceuListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return como_conheceu_service.list_como_conheceu(
        db, company_id=company_id, nome=nome, status=status, page=page, page_size=page_size
    )


@router.get("/{cco_id}", response_model=ComoConheceuResponse)
def obter(
    cco_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ComoConheceuResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return como_conheceu_service.get_como_conheceu(db, cco_id, company_id)


@router.post("", response_model=ComoConheceuResponse, status_code=status.HTTP_201_CREATED)
def criar(
    data: ComoConheceuCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ComoConheceuResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return como_conheceu_service.create_como_conheceu(db, data, company_id)


@router.put("/{cco_id}", response_model=ComoConheceuResponse)
def atualizar(
    cco_id: int,
    data: ComoConheceuUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ComoConheceuResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return como_conheceu_service.update_como_conheceu(db, cco_id, data, company_id)


@router.patch("/{cco_id}/ativar", response_model=ComoConheceuResponse)
def ativar(
    cco_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ComoConheceuResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return como_conheceu_service.set_como_conheceu_ativo(db, cco_id, True, company_id)


@router.patch("/{cco_id}/inativar", response_model=ComoConheceuResponse)
def inativar(
    cco_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ComoConheceuResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return como_conheceu_service.set_como_conheceu_ativo(db, cco_id, False, company_id)
