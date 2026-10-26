from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import IdColumnFactory
from ..database import Base


class MetaAdsInsightAnuncioDiario(Base):
    """Metricas de um anuncio num dia (fuso da conta). Regravado a cada sync do periodo."""

    __tablename__ = "meta_ads_insight_anuncio_diario"
    __table_args__ = (
        UniqueConstraint("miaManId", "miaData", name="uq_meta_ads_insight_anuncio_dia"),
        Index("ix_meta_ads_insight_anuncio_emp_data", "miaEmpId", "miaData"),
    )

    miaId: Mapped[int] = IdColumnFactory.int_id("miaId")
    miaEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False
    )
    miaMacId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_conta.macId", ondelete="CASCADE"), nullable=False, index=True
    )
    miaManId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_anuncio.manId", ondelete="CASCADE"), nullable=False
    )
    miaData: Mapped[date] = mapped_column(Date, nullable=False)
    miaInvestimento: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    miaImpressoes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    miaAlcance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    miaCliques: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    miaCliquesLink: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    miaLeadsMeta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
