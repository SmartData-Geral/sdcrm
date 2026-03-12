from typing import Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..exceptions import NotFoundError
from ..models.empresa import Empresa
from ..models.usuario_empresa import UsuarioEmpresa
from ..schemas.empresa import (
    EmpresaCreate,
    EmpresaListGestaoResponse,
    EmpresaListResponse,
    EmpresaResponse,
    EmpresaUpdate,
)


def list_empresas_for_user(db: Session, user_id: int) -> EmpresaListResponse:
    """Lista empresas às quais o usuário tem vínculo (usuario_empresa)."""
    stmt = (
        select(Empresa)
        .join(UsuarioEmpresa, Empresa.empId == UsuarioEmpresa.useEmpId)
        .where(
            UsuarioEmpresa.useUsuId == user_id,
            Empresa.empAtivo.is_(True),
        )
        .order_by(Empresa.empNome)
    )
    items = db.scalars(stmt).unique().all()
    return EmpresaListResponse(items=[EmpresaResponse.model_validate(e) for e in items])


def list_empresas_gestao(
    db: Session,
    nome: Optional[str] = None,
    status: Literal["ativos", "inativos", "todos"] = "ativos",
    page: int = 1,
    page_size: int = 20,
) -> EmpresaListGestaoResponse:
    stmt = select(Empresa)
    if nome:
        stmt = stmt.where(Empresa.empNome.ilike(f"%{nome}%"))
    if status == "ativos":
        stmt = stmt.where(Empresa.empAtivo.is_(True))
    elif status == "inativos":
        stmt = stmt.where(Empresa.empAtivo.is_(False))
    stmt = stmt.order_by(Empresa.empNome)
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(total_stmt) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).all()
    return EmpresaListGestaoResponse(
        items=[EmpresaResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_empresa(db: Session, emp_id: int) -> Empresa:
    empresa = db.get(Empresa, emp_id)
    if empresa is None:
        raise NotFoundError("Empresa não encontrada")
    return empresa


def create_empresa(db: Session, data: EmpresaCreate) -> EmpresaResponse:
    obj = Empresa(empNome=data.empNome)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return EmpresaResponse.model_validate(obj)


def update_empresa(db: Session, emp_id: int, data: EmpresaUpdate) -> EmpresaResponse:
    obj = get_empresa(db, emp_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return EmpresaResponse.model_validate(obj)


def set_empresa_ativo(db: Session, emp_id: int, ativo: bool) -> EmpresaResponse:
    obj = get_empresa(db, emp_id)
    obj.empAtivo = ativo
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return EmpresaResponse.model_validate(obj)
