from typing import Literal, Optional

from fastapi import APIRouter, Query, status

from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..schemas.tag import TagCreate, TagListResponse, TagResponse, TagUpdate
from ..services import tag_service

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=TagListResponse)
def listar(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    nome: Optional[str] = Query(default=None),
    status: Literal["ativos", "inativos", "todos"] = Query(default="ativos"),
) -> TagListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return tag_service.list_tags(db, company_id=company_id, nome=nome, status=status, page=page, page_size=page_size)


@router.get("/{tag_id}", response_model=TagResponse)
def obter(
    tag_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> TagResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return tag_service.get_tag(db, tag_id, company_id)


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def criar(
    data: TagCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> TagResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return tag_service.create_tag(db, data, company_id)


@router.put("/{tag_id}", response_model=TagResponse)
def atualizar(
    tag_id: int,
    data: TagUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> TagResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return tag_service.update_tag(db, tag_id, data, company_id)


@router.patch("/{tag_id}/ativar", response_model=TagResponse)
def ativar(
    tag_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> TagResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return tag_service.set_tag_ativo(db, tag_id, True, company_id)


@router.patch("/{tag_id}/inativar", response_model=TagResponse)
def inativar(
    tag_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> TagResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return tag_service.set_tag_ativo(db, tag_id, False, company_id)
