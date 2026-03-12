from typing import Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..exceptions import NotFoundError
from ..models.etapa_kanban import EtapaKanban
from ..schemas.etapa_kanban import (
    EtapaKanbanCreate,
    EtapaKanbanListResponse,
    EtapaKanbanResponse,
    EtapaKanbanUpdate,
)


def list_etapas_kanban(
    db: Session,
    company_id: Optional[int] = None,
    nome: Optional[str] = None,
    status: Literal["ativos", "inativos", "todos"] = "ativos",
    page: int = 1,
    page_size: int = 20,
) -> EtapaKanbanListResponse:
    stmt = select(EtapaKanban)
    if company_id is not None:
        stmt = stmt.where(EtapaKanban.etkEmpId == company_id)
    if nome:
        stmt = stmt.where(EtapaKanban.etkNome.ilike(f"%{nome}%"))
    if status == "ativos":
        stmt = stmt.where(EtapaKanban.etkAtivo.is_(True))
    elif status == "inativos":
        stmt = stmt.where(EtapaKanban.etkAtivo.is_(False))
    stmt = stmt.order_by(EtapaKanban.etkOrdem, EtapaKanban.etkNome)
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(total_stmt) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).all()
    return EtapaKanbanListResponse(
        items=[EtapaKanbanResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_etapa_kanban(db: Session, etk_id: int, company_id: Optional[int] = None) -> EtapaKanban:
    stmt = select(EtapaKanban).where(EtapaKanban.etkId == etk_id)
    if company_id is not None:
        stmt = stmt.where(EtapaKanban.etkEmpId == company_id)
    row = db.scalars(stmt).first()
    if row is None:
        raise NotFoundError("Etapa kanban não encontrada")
    return row


def create_etapa_kanban(
    db: Session,
    data: EtapaKanbanCreate,
    company_id: Optional[int] = None,
) -> EtapaKanbanResponse:
    obj = EtapaKanban(etkEmpId=company_id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return EtapaKanbanResponse.model_validate(obj)


def update_etapa_kanban(
    db: Session,
    etk_id: int,
    data: EtapaKanbanUpdate,
    company_id: Optional[int] = None,
) -> EtapaKanbanResponse:
    obj = get_etapa_kanban(db, etk_id, company_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return EtapaKanbanResponse.model_validate(obj)


def set_etapa_kanban_ativo(
    db: Session,
    etk_id: int,
    ativo: bool,
    company_id: Optional[int] = None,
) -> EtapaKanbanResponse:
    obj = get_etapa_kanban(db, etk_id, company_id)
    obj.etkAtivo = ativo
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return EtapaKanbanResponse.model_validate(obj)
