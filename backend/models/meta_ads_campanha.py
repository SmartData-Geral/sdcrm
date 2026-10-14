from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import AuditColumnFactory, IdColumnFactory
from ..database import Base


class MetaAdsCampanha(Base):
    """Campanha sincronizada do Meta. O nome e atualizado a cada sync (pode mudar no Meta)."""

    __tablename__ = "meta_ads_campanha"
    __table_args__ = (
        UniqueConstraint("mcgMacId", "mcgCampanhaExterna", name="uq_meta_ads_campanha_conta_ext"),
        Index("ix_meta_ads_campanha_emp_nome", "mcgEmpId", "mcgNomeNormalizado"),
    )

    mcgId: Mapped[int] = IdColumnFactory.int_id("mcgId")
    mcgEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False, index=True
    )
    mcgMacId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_conta.macId", ondelete="CASCADE"), nullable=False, index=True
    )
    mcgCampanhaExterna: Mapped[str] = mapped_column(String(40), nullable=False)
    mcgNome: Mapped[str] = mapped_column(String(400), nullable=False)
    mcgNomeNormalizado: Mapped[str] = mapped_column(String(400), nullable=False)
    mcgObjetivo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    mcgStatus: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mcgDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("mcgDataCriacao")
    mcgDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao(
        "mcgDataAtualizacao"
    )
