from typing import Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..exceptions import NotFoundError
from ..models.motivo_cancelamento import MotivoCancelamento
from ..schemas.motivo_cancelamento import (
    MotivoCancelamentoCreate,
    MotivoCancelamentoListResponse,
    MotivoCancelamentoResponse,
    MotivoCancelamentoUpdate,
)


def list_motivos_cancelamento(
    db: Session,
    company_id: Optional[int] = None,
    nome: Optional[str] = None,
    status: Literal["ativos", "inativos", "todos"] = "ativos",
    page: int = 1,
    page_size: int = 20,
) -> MotivoCancelamentoListResponse:
    stmt = select(MotivoCancelamento)
    if company_id is not None:
        stmt = stmt.where(MotivoCancelamento.mcaEmpId == company_id)
    if nome:
        stmt = stmt.where(MotivoCancelamento.mcaNome.ilike(f"%{nome}%"))
    if status == "ativos":
        stmt = stmt.where(MotivoCancelamento.mcaAtivo.is_(True))
    elif status == "inativos":
        stmt = stmt.where(MotivoCancelamento.mcaAtivo.is_(False))
    stmt = stmt.order_by(MotivoCancelamento.mcaNome)
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(total_stmt) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).all()
    return MotivoCancelamentoListResponse(
        items=[MotivoCancelamentoResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_motivo_cancelamento(db: Session, mca_id: int, company_id: Optional[int] = None) -> MotivoCancelamento:
    stmt = select(MotivoCancelamento).where(MotivoCancelamento.mcaId == mca_id)
    if company_id is not None:
        stmt = stmt.where(MotivoCancelamento.mcaEmpId == company_id)
    row = db.scalars(stmt).first()
    if row is None:
        raise NotFoundError("Motivo de cancelamento não encontrado")
    return row


def create_motivo_cancelamento(
    db: Session,
    data: MotivoCancelamentoCreate,
    company_id: Optional[int] = None,
) -> MotivoCancelamentoResponse:
    obj = MotivoCancelamento(mcaEmpId=company_id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return MotivoCancelamentoResponse.model_validate(obj)


def update_motivo_cancelamento(
    db: Session,
    mca_id: int,
    data: MotivoCancelamentoUpdate,
    company_id: Optional[int] = None,
) -> MotivoCancelamentoResponse:
    obj = get_motivo_cancelamento(db, mca_id, company_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return MotivoCancelamentoResponse.model_validate(obj)


def set_motivo_cancelamento_ativo(
    db: Session,
    mca_id: int,
    ativo: bool,
    company_id: Optional[int] = None,
) -> MotivoCancelamentoResponse:
    obj = get_motivo_cancelamento(db, mca_id, company_id)
    obj.mcaAtivo = ativo
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return MotivoCancelamentoResponse.model_validate(obj)
