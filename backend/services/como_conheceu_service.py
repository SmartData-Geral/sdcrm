from typing import Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..exceptions import NotFoundError
from ..models.como_conheceu import ComoConheceu
from ..schemas.como_conheceu import (
    ComoConheceuCreate,
    ComoConheceuListResponse,
    ComoConheceuResponse,
    ComoConheceuUpdate,
)


def list_como_conheceu(
    db: Session,
    company_id: Optional[int] = None,
    nome: Optional[str] = None,
    status: Literal["ativos", "inativos", "todos"] = "ativos",
    page: int = 1,
    page_size: int = 20,
) -> ComoConheceuListResponse:
    stmt = select(ComoConheceu)
    if company_id is not None:
        stmt = stmt.where(ComoConheceu.ccoEmpId == company_id)
    if nome:
        stmt = stmt.where(ComoConheceu.ccoNome.ilike(f"%{nome}%"))
    if status == "ativos":
        stmt = stmt.where(ComoConheceu.ccoAtivo.is_(True))
    elif status == "inativos":
        stmt = stmt.where(ComoConheceu.ccoAtivo.is_(False))
    stmt = stmt.order_by(ComoConheceu.ccoNome)
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(total_stmt) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).all()
    return ComoConheceuListResponse(
        items=[ComoConheceuResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_como_conheceu(db: Session, cco_id: int, company_id: Optional[int] = None) -> ComoConheceu:
    stmt = select(ComoConheceu).where(ComoConheceu.ccoId == cco_id)
    if company_id is not None:
        stmt = stmt.where(ComoConheceu.ccoEmpId == company_id)
    row = db.scalars(stmt).first()
    if row is None:
        raise NotFoundError("Como conheceu não encontrado")
    return row


def create_como_conheceu(
    db: Session,
    data: ComoConheceuCreate,
    company_id: Optional[int] = None,
) -> ComoConheceuResponse:
    obj = ComoConheceu(ccoEmpId=company_id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return ComoConheceuResponse.model_validate(obj)


def update_como_conheceu(
    db: Session,
    cco_id: int,
    data: ComoConheceuUpdate,
    company_id: Optional[int] = None,
) -> ComoConheceuResponse:
    obj = get_como_conheceu(db, cco_id, company_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return ComoConheceuResponse.model_validate(obj)


def set_como_conheceu_ativo(
    db: Session,
    cco_id: int,
    ativo: bool,
    company_id: Optional[int] = None,
) -> ComoConheceuResponse:
    obj = get_como_conheceu(db, cco_id, company_id)
    obj.ccoAtivo = ativo
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return ComoConheceuResponse.model_validate(obj)
