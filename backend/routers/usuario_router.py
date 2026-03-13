from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import CurrentUserDep, DbSessionDep, require_admin
from ..schemas.usuario import UsuarioCreate, UsuarioListResponse, UsuarioResponse, UsuarioUpdate
from ..services import usuario_service

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


@router.get("", response_model=UsuarioListResponse)
def listar(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    nome: Optional[str] = Query(default=None),
    status: Literal["ativos", "inativos", "todos"] = Query(default="ativos"),
) -> UsuarioListResponse:
    """Lista todos os usuários do sistema (apenas para admin), independente de empresa."""
    require_admin(current_user)
    return usuario_service.list_usuarios(
        db, nome=nome, status=status, page=page, page_size=page_size
    )


@router.get("/{usu_id}", response_model=UsuarioResponse)
def obter(
    usu_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> UsuarioResponse:
    require_admin(current_user)
    return usuario_service.get_usuario(db, usu_id)


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def criar(
    data: UsuarioCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> UsuarioResponse:
    require_admin(current_user)
    return usuario_service.create_usuario(db, data)


@router.put("/{usu_id}", response_model=UsuarioResponse)
def atualizar(
    usu_id: int,
    data: UsuarioUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> UsuarioResponse:
    require_admin(current_user)
    return usuario_service.update_usuario(db, usu_id, data)


@router.patch("/{usu_id}/ativar", response_model=UsuarioResponse)
def ativar(
    usu_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> UsuarioResponse:
    require_admin(current_user)
    return usuario_service.set_usuario_ativo(db, usu_id, True)


@router.patch("/{usu_id}/inativar", response_model=UsuarioResponse)
def inativar(
    usu_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> UsuarioResponse:
    require_admin(current_user)
    return usuario_service.set_usuario_ativo(db, usu_id, False)
