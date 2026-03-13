from typing import Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_password_hash
from ..exceptions import BadRequestError, NotFoundError
from ..models.usuario import Usuario
from ..models.usuario_empresa import UsuarioEmpresa
from ..schemas.usuario import UsuarioCreate, UsuarioListResponse, UsuarioResponse, UsuarioUpdate


def _usuario_to_response(user: Usuario) -> UsuarioResponse:
    resp = UsuarioResponse.model_validate(user)
    resp.empresas = [v.empresa.empNome for v in user.empresas_vinculo if v.empresa is not None]
    return resp


def list_usuarios(
    db: Session,
    nome: Optional[str] = None,
    status: Literal["ativos", "inativos", "todos"] = "ativos",
    page: int = 1,
    page_size: int = 20,
) -> UsuarioListResponse:
    stmt = select(Usuario)
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
        items=[_usuario_to_response(u) for u in items],
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
    # Vínculos de empresa para perfil USER
    if data.empresasIds:
        user.empresas_vinculo = [UsuarioEmpresa(useEmpId=emp_id) for emp_id in data.empresasIds]
    db.add(user)
    db.commit()
    db.refresh(user)
    return _usuario_to_response(user)


def update_usuario(db: Session, usu_id: int, data: UsuarioUpdate) -> UsuarioResponse:
    user = get_usuario(db, usu_id)
    update_data = data.model_dump(exclude_unset=True)
    empresas_ids = update_data.pop("empresasIds", None)
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
    # Atualiza vínculos de empresa quando enviado
    if empresas_ids is not None:
        user.empresas_vinculo.clear()
        for emp_id in empresas_ids:
            user.empresas_vinculo.append(UsuarioEmpresa(useEmpId=emp_id))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _usuario_to_response(user)


def set_usuario_ativo(db: Session, usu_id: int, ativo: bool) -> UsuarioResponse:
    user = get_usuario(db, usu_id)
    user.usuAtivo = ativo
    db.add(user)
    db.commit()
    db.refresh(user)
    return _usuario_to_response(user)
