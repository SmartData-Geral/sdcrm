from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..schemas.produto import ProdutoCreate, ProdutoListResponse, ProdutoResponse, ProdutoUpdate
from ..services import produto_service

router = APIRouter(prefix="/api/produtos", tags=["produtos"])


@router.get("", response_model=ProdutoListResponse)
def listar(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    nome: Optional[str] = Query(default=None),
    status: Literal["ativos", "inativos", "todos"] = Query(default="ativos"),
) -> ProdutoListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return produto_service.list_produtos(
        db, company_id=company_id, nome=nome, status=status, page=page, page_size=page_size
    )


@router.get("/{pro_id}", response_model=ProdutoResponse)
def obter(
    pro_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ProdutoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return produto_service.get_produto(db, pro_id, company_id)


@router.post("", response_model=ProdutoResponse, status_code=status.HTTP_201_CREATED)
def criar(
    data: ProdutoCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ProdutoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return produto_service.create_produto(db, data, company_id)


@router.put("/{pro_id}", response_model=ProdutoResponse)
def atualizar(
    pro_id: int,
    data: ProdutoUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ProdutoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return produto_service.update_produto(db, pro_id, data, company_id)


@router.patch("/{pro_id}/ativar", response_model=ProdutoResponse)
def ativar(
    pro_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ProdutoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return produto_service.set_produto_ativo(db, pro_id, True, company_id)


@router.patch("/{pro_id}/inativar", response_model=ProdutoResponse)
def inativar(
    pro_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ProdutoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return produto_service.set_produto_ativo(db, pro_id, False, company_id)
