from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import IdColumnFactory
from ..database import Base


class OportunidadeEtapaHistorico(Base):
    """Uma linha por transicao de estagio do funil (estruturada, ao contrario do texto livre
    de oportunidade_historico). Origem: ui | api | mcp | retroativo."""

    __tablename__ = "oportunidade_etapa_historico"
    __table_args__ = (
        Index("ix_oeh_opo_data", "oehOpoId", "oehData"),
        Index("ix_oeh_emp_data", "oehEmpId", "oehData"),
    )

    oehId: Mapped[int] = IdColumnFactory.int_id("oehId")
    oehEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False, index=True
    )
    oehOpoId: Mapped[int] = mapped_column(
        Integer, ForeignKey("oportunidade.opoId", ondelete="CASCADE"), nullable=False, index=True
    )
    oehEtkIdDe: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("etapa_kanban.etkId", ondelete="SET NULL"), nullable=True, index=True
    )
    oehEtkIdPara: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("etapa_kanban.etkId", ondelete="SET NULL"), nullable=True, index=True
    )
    oehData: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    oehOrigem: Mapped[str] = mapped_column(String(20), nullable=False)
