from typing import Annotated, Optional

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from .auth import get_current_user
from .config import settings
from .database import get_db
from .exceptions import AuthorizationError, BadRequestError
from .models.usuario import Usuario
from .models.usuario_empresa import UsuarioEmpresa

DbSessionDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[Usuario, Depends(get_current_user)]


def get_company_id_from_header(
    x_company_id: Optional[int] = Header(default=None, alias="X-Company-Id"),
) -> Optional[int]:
    if not settings.MULTIEMPRESA_ENABLED:
        return None
    if x_company_id is None:
        raise BadRequestError("Header X-Company-Id é obrigatório em modo multiempresa")
    return x_company_id


CompanyIdDep = Annotated[Optional[int], Depends(get_company_id_from_header)]


def require_user_in_company(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> None:
    if not settings.MULTIEMPRESA_ENABLED or company_id is None:
        return
    vinculo = (
        db.query(UsuarioEmpresa)
        .filter(
            UsuarioEmpresa.useUsuId == current_user.usuId,
            UsuarioEmpresa.useEmpId == company_id,
        )
        .first()
    )
    if vinculo is None:
        raise AuthorizationError("Usuário não possui acesso à empresa selecionada")


def require_admin(current_user: CurrentUserDep) -> Usuario:
    # Campo de perfil/permissão pode ser evoluído aqui.
    if not current_user.usuAdmin:
        raise AuthorizationError("Apenas administradores podem acessar este recurso")
    return current_user

