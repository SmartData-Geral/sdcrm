from datetime import datetime, timezone
from typing import Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..exceptions import NotFoundError
from ..models.oportunidade import Oportunidade
from ..models.oportunidade_historico import OportunidadeHistorico
from ..schemas.oportunidade_historico import (
    OportunidadeHistoricoCreate,
    OportunidadeHistoricoListResponse,
    OportunidadeHistoricoResponse,
    OportunidadeHistoricoUpdate,
)


def list_historicos(
    db: Session,
    opo_id: int,
    company_id: Optional[int] = None,
    status: Literal["ativos", "inativos", "todos"] = "ativos",
    page: int = 1,
    page_size: int = 50,
) -> OportunidadeHistoricoListResponse:
    stmt = select(OportunidadeHistorico).where(OportunidadeHistorico.ophOpoId == opo_id)
    if company_id is not None:
        stmt = stmt.where(OportunidadeHistorico.ophEmpId == company_id)
    if status == "ativos":
        stmt = stmt.where(OportunidadeHistorico.ophAtivo.is_(True))
    elif status == "inativos":
        stmt = stmt.where(OportunidadeHistorico.ophAtivo.is_(False))
    stmt = stmt.order_by(OportunidadeHistorico.ophDataRegistro.desc())
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(total_stmt) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).all()
    return OportunidadeHistoricoListResponse(
        items=[OportunidadeHistoricoResponse.model_validate(h) for h in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_historico(
    db: Session,
    oph_id: int,
    company_id: Optional[int] = None,
) -> OportunidadeHistorico:
    stmt = select(OportunidadeHistorico).where(OportunidadeHistorico.ophId == oph_id)
    if company_id is not None:
        stmt = stmt.where(OportunidadeHistorico.ophEmpId == company_id)
    row = db.scalars(stmt).first()
    if row is None:
        raise NotFoundError("Histórico não encontrado")
    return row


def create_historico(
    db: Session,
    opo_id: int,
    data: OportunidadeHistoricoCreate,
    company_id: Optional[int] = None,
    usu_id: Optional[int] = None,
) -> OportunidadeHistoricoResponse:
    opo = db.get(Oportunidade, opo_id)
    if opo is None or (company_id is not None and opo.opoEmpId != company_id):
        raise NotFoundError("Oportunidade não encontrada")
    emp_id = company_id if company_id is not None else opo.opoEmpId
    data_registro = datetime.now(timezone.utc)
    obj = OportunidadeHistorico(
        ophEmpId=emp_id,
        ophOpoId=opo_id,
        ophUsuId=usu_id,
        ophDataRegistro=data_registro,
        ophConteudo=data.ophConteudo,
    )
    opo.opoDataUltimoContato = data_registro.date()
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return OportunidadeHistoricoResponse.model_validate(obj)


def update_historico(
    db: Session,
    oph_id: int,
    data: OportunidadeHistoricoUpdate,
    company_id: Optional[int] = None,
) -> OportunidadeHistoricoResponse:
    obj = get_historico(db, oph_id, company_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return OportunidadeHistoricoResponse.model_validate(obj)


def inativar_historico(
    db: Session,
    oph_id: int,
    company_id: Optional[int] = None,
) -> OportunidadeHistoricoResponse:
    obj = get_historico(db, oph_id, company_id)
    obj.ophAtivo = False
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return OportunidadeHistoricoResponse.model_validate(obj)
