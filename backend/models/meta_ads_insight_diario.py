from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import IdColumnFactory
from ..database import Base


class MetaAdsInsightDiario(Base):
    """Metricas de uma campanha num dia (fuso da conta). Regravado a cada sync do periodo."""

    __tablename__ = "meta_ads_insight_diario"
    __table_args__ = (
        UniqueConstraint("midMcgId", "midData", name="uq_meta_ads_insight_campanha_dia"),
        Index("ix_meta_ads_insight_emp_data", "midEmpId", "midData"),
    )

    midId: Mapped[int] = IdColumnFactory.int_id("midId")
    midEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False
    )
    midMacId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_conta.macId", ondelete="CASCADE"), nullable=False, index=True
    )
    midMcgId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_campanha.mcgId", ondelete="CASCADE"), nullable=False
    )
    midData: Mapped[date] = mapped_column(Date, nullable=False)
    midInvestimento: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    midImpressoes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    midCliques: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Gravado mas nao exibido: alcance diario nao e somavel entre dias.
    midAlcance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    midLeadsMeta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
