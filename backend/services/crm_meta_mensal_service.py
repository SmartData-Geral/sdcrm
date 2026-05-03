from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..exceptions import ConflictError, NotFoundError
from ..models.crm_meta_mensal import CrmMetaMensal
from ..schemas.crm_meta_mensal import (
    CrmMetaMensalCreate,
    CrmMetaMensalListResponse,
    CrmMetaMensalResponse,
    CrmMetaMensalResumoResponse,
    CrmMetaMensalUpdate,
)


def computar_derivados(qtd_recebimento: int, taxa_conversao: Decimal, mrr_medio: Decimal) -> tuple[int, Decimal]:
    """Qtd fechamento: truncagem (ex.: 6 * 0,35 → 2). MRR incremental: 2 casas decimais."""
    q_dec = Decimal(qtd_recebimento)
    t_dec = Decimal(str(taxa_conversao))
    m_dec = Decimal(str(mrr_medio))
    qtd_fechamento = int(q_dec * t_dec)
    mrr_incremental = (Decimal(qtd_fechamento) * m_dec).quantize(Decimal("0.01"))
    return qtd_fechamento, mrr_incremental


def _stmt_base(company_id: int) -> select:
    return select(CrmMetaMensal).where(CrmMetaMensal.cmmEmpId == company_id)


def list_metas(
    db: Session,
    company_id: int,
    ano: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> CrmMetaMensalListResponse:
    stmt = _stmt_base(company_id)
    if ano is not None:
        ano_inicio = date(ano, 1, 1)
        ano_fim = date(ano, 12, 31)
        stmt = stmt.where(CrmMetaMensal.cmmMesReferencia >= ano_inicio, CrmMetaMensal.cmmMesReferencia <= ano_fim)
    stmt = stmt.order_by(CrmMetaMensal.cmmMesReferencia.asc())
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = db.scalars(stmt).all()
    return CrmMetaMensalListResponse(
        items=[CrmMetaMensalResponse.model_validate(r) for r in rows],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def list_resumo_ano(db: Session, company_id: int, ano: int) -> CrmMetaMensalResumoResponse:
    ano_inicio = date(ano, 1, 1)
    ano_fim = date(ano, 12, 31)
    stmt = (
        _stmt_base(company_id)
        .where(CrmMetaMensal.cmmMesReferencia >= ano_inicio, CrmMetaMensal.cmmMesReferencia <= ano_fim)
        .order_by(CrmMetaMensal.cmmMesReferencia.asc())
    )
    rows = db.scalars(stmt).all()
    return CrmMetaMensalResumoResponse(
        items=[CrmMetaMensalResponse.model_validate(r) for r in rows],
        ano=ano,
    )


def get_meta(db: Session, meta_id: int, company_id: int) -> CrmMetaMensal:
    stmt = _stmt_base(company_id).where(CrmMetaMensal.cmmId == meta_id)
    row = db.scalars(stmt).first()
    if row is None:
        raise NotFoundError("Meta mensal não encontrada")
    return row


def _existe_meta_mes(db: Session, company_id: int, mes_ref: date, exclude_id: Optional[int] = None) -> bool:
    stmt = select(func.count()).select_from(CrmMetaMensal).where(
        CrmMetaMensal.cmmEmpId == company_id,
        CrmMetaMensal.cmmMesReferencia == mes_ref,
    )
    if exclude_id is not None:
        stmt = stmt.where(CrmMetaMensal.cmmId != exclude_id)
    n = db.scalar(stmt)
    return (n or 0) > 0


def create_meta(db: Session, company_id: int, data: CrmMetaMensalCreate) -> CrmMetaMensalResponse:
    mes_ref = data.cmmMesReferencia
    if _existe_meta_mes(db, company_id, mes_ref):
        raise ConflictError("Já existe meta cadastrada para este mês.")
    qfe, mir = computar_derivados(data.cmmQtdRecebimento, data.cmmTaxaConversao, data.cmmMrrMedio)
    obj = CrmMetaMensal(
        cmmEmpId=company_id,
        cmmMesReferencia=mes_ref,
        cmmQtdRecebimento=data.cmmQtdRecebimento,
        cmmTaxaConversao=data.cmmTaxaConversao,
        cmmMrrMedio=data.cmmMrrMedio,
        cmmQtdFechamento=qfe,
        cmmMrrIncremental=mir,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CrmMetaMensalResponse.model_validate(obj)


def update_meta(db: Session, meta_id: int, company_id: int, data: CrmMetaMensalUpdate) -> CrmMetaMensalResponse:
    obj = get_meta(db, meta_id, company_id)
    payload = data.model_dump(exclude_unset=True)
    if "cmmMesReferencia" in payload:
        nuevo = payload["cmmMesReferencia"]
        if nuevo is not None and nuevo != obj.cmmMesReferencia and _existe_meta_mes(db, company_id, nuevo, exclude_id=meta_id):
            raise ConflictError("Já existe meta cadastrada para este mês.")
    for key, val in payload.items():
        setattr(obj, key, val)
    qr = obj.cmmQtdRecebimento
    tx = obj.cmmTaxaConversao
    mm = obj.cmmMrrMedio
    qfe, mir = computar_derivados(qr, tx, mm)
    obj.cmmQtdFechamento = qfe
    obj.cmmMrrIncremental = mir
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CrmMetaMensalResponse.model_validate(obj)


def delete_meta(db: Session, meta_id: int, company_id: int) -> None:
    obj = get_meta(db, meta_id, company_id)
    db.delete(obj)
    db.commit()
