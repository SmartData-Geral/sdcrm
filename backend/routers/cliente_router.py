from typing import Iterable, Literal, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..dependencies import CompanyIdDep, DbSessionDep, CurrentUserDep, require_user_in_company
from ..schemas.cliente import ClienteCreate, ClienteListResponse, ClienteResponse, ClienteUpdate
from ..services import cliente_service

router = APIRouter(prefix="/api/clientes", tags=["clientes"])


@router.get("", response_model=ClienteListResponse)
def listar_clientes(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    nome: Optional[str] = Query(default=None),
    status: Literal["ativos", "inativos", "todos"] = Query(default="ativos"),
) -> ClienteListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return cliente_service.list_clientes(
        db,
        company_id=company_id,
        nome=nome,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/{cli_id}", response_model=ClienteResponse)
def obter_cliente(
    cli_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ClienteResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    cliente = cliente_service.get_cliente(db, cli_id, company_id)
    return ClienteResponse.model_validate(cliente)


@router.post("", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
def criar_cliente(
    data: ClienteCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ClienteResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return cliente_service.create_cliente(db, data, company_id)


@router.put("/{cli_id}", response_model=ClienteResponse)
def atualizar_cliente(
    cli_id: int,
    data: ClienteUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ClienteResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return cliente_service.update_cliente(db, cli_id, data, company_id)


@router.delete("/{cli_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_cliente(
    cli_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> None:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    cliente_service.delete_cliente(db, cli_id, company_id)

