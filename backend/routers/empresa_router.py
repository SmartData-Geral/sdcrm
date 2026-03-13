from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import CurrentUserDep, DbSessionDep, require_admin
from ..schemas.empresa import (
    EmpresaCreate,
    EmpresaListGestaoResponse,
    EmpresaListResponse,
    EmpresaResponse,
    EmpresaUpdate,
)
from ..services import empresa_service

router = APIRouter(prefix="/api/empresas", tags=["empresas"])


@router.get("", response_model=EmpresaListResponse | EmpresaListGestaoResponse)
def listar(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    gestao: Optional[bool] = Query(default=False, description="Se True e admin, lista todas com paginação"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    nome: Optional[str] = Query(default=None),
    status: Literal["ativos", "inativos", "todos"] = Query(default="ativos"),
) -> EmpresaListResponse | EmpresaListGestaoResponse:
    """Sem gestao=1: empresas do usuário (para seletor). Com gestao=1 e admin: todas com paginação."""
    if gestao and current_user.usuAdmin:
        require_admin(current_user)
        return empresa_service.list_empresas_gestao(
            db, nome=nome, status=status, page=page, page_size=page_size
        )
    # Para o seletor de empresas:
    # - ADMIN: vê todas as empresas ativas
    # - USER: vê apenas empresas vinculadas (usuario_empresa)
    if current_user.usuAdmin:
        return empresa_service.list_empresas_ativas(db)
    return empresa_service.list_empresas_for_user(db, current_user.usuId)


@router.get("/{emp_id}", response_model=EmpresaResponse)
def obter(
    emp_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> EmpresaResponse:
    empresa = empresa_service.get_empresa(db, emp_id)
    return EmpresaResponse.model_validate(empresa)


@router.post("", response_model=EmpresaResponse, status_code=status.HTTP_201_CREATED)
def criar(
    data: EmpresaCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> EmpresaResponse:
    require_admin(current_user)
    return empresa_service.create_empresa(db, data)


@router.put("/{emp_id}", response_model=EmpresaResponse)
def atualizar(
    emp_id: int,
    data: EmpresaUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> EmpresaResponse:
    require_admin(current_user)
    return empresa_service.update_empresa(db, emp_id, data)


@router.patch("/{emp_id}/ativar", response_model=EmpresaResponse)
def ativar(
    emp_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> EmpresaResponse:
    require_admin(current_user)
    return empresa_service.set_empresa_ativo(db, emp_id, True)


@router.patch("/{emp_id}/inativar", response_model=EmpresaResponse)
def inativar(
    emp_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> EmpresaResponse:
    require_admin(current_user)
    return empresa_service.set_empresa_ativo(db, emp_id, False)
