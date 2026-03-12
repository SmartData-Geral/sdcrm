from typing import Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_password_hash
from ..exceptions import BadRequestError, NotFoundError
from ..models.usuario import Usuario
from ..models.usuario_empresa import UsuarioEmpresa
from ..schemas.usuario import UsuarioCreate, UsuarioListResponse, UsuarioResponse, UsuarioUpdate


def list_usuarios(
    db: Session,
    company_id: Optional[int] = None,
    nome: Optional[str] = None,
    status: Literal["ativos", "inativos", "todos"] = "ativos",
    page: int = 1,
    page_size: int = 20,
) -> UsuarioListResponse:
    stmt = select(Usuario)
    if company_id is not None:
        stmt = stmt.join(UsuarioEmpresa, Usuario.usuId == UsuarioEmpresa.useUsuId).where(
            UsuarioEmpresa.useEmpId == company_id
        )
    if nome:
        stmt = stmt.where(Usuario.usuNome.ilike(f"%{nome}%"))
    if status == "ativos":
        stmt = stmt.where(Usuario.usuAtivo.is_(True))
    elif status == "inativos":
        stmt = stmt.where(Usuario.usuAtivo.is_(False))
    stmt = stmt.distinct().order_by(Usuario.usuNome)
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(total_stmt) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).all()
    return UsuarioListResponse(
        items=[UsuarioResponse.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_usuario(db: Session, usu_id: int) -> Usuario:
    user = db.get(Usuario, usu_id)
    if user is None:
        raise NotFoundError("Usuário não encontrado")
    return user


def create_usuario(db: Session, data: UsuarioCreate) -> UsuarioResponse:
    existing = db.execute(select(Usuario).where(Usuario.usuEmail == data.usuEmail)).scalars().first()
    if existing is not None:
        raise BadRequestError("Já existe usuário com este e-mail")
    user = Usuario(
        usuNome=data.usuNome,
        usuEmail=data.usuEmail,
        usuSenhaHash=get_password_hash(data.usuSenha),
        usuAdmin=data.usuAdmin,
        usuPerfil=data.usuPerfil,
        usuAvatarUrl=data.usuAvatarUrl,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UsuarioResponse.model_validate(user)


def update_usuario(db: Session, usu_id: int, data: UsuarioUpdate) -> UsuarioResponse:
    user = get_usuario(db, usu_id)
    update_data = data.model_dump(exclude_unset=True)
    if "usuSenha" in update_data:
        update_data["usuSenhaHash"] = get_password_hash(update_data.pop("usuSenha"))
    if "usuEmail" in update_data:
        existing = (
            db.execute(
                select(Usuario).where(
                    Usuario.usuEmail == update_data["usuEmail"],
                    Usuario.usuId != usu_id,
                )
            ).scalars().first()
        )
        if existing is not None:
            raise BadRequestError("Já existe usuário com este e-mail")
    for k, v in update_data.items():
        setattr(user, k, v)
    db.add(user)
    db.commit()
    db.refresh(user)
    return UsuarioResponse.model_validate(user)


def set_usuario_ativo(db: Session, usu_id: int, ativo: bool) -> UsuarioResponse:
    user = get_usuario(db, usu_id)
    user.usuAtivo = ativo
    db.add(user)
    db.commit()
    db.refresh(user)
    return UsuarioResponse.model_validate(user)
