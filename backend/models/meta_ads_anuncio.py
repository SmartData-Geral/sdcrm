from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import AuditColumnFactory, IdColumnFactory
from ..database import Base


class MetaAdsAnuncio(Base):
    """Anuncio (criativo) de um conjunto Meta. Nome e status sao atualizados a cada sync."""

    __tablename__ = "meta_ads_anuncio"
    __table_args__ = (
        UniqueConstraint("manMacId", "manAnuncioExterno", name="uq_meta_ads_anuncio_conta_ext"),
        Index("ix_meta_ads_anuncio_emp_ext", "manEmpId", "manAnuncioExterno"),
    )

    manId: Mapped[int] = IdColumnFactory.int_id("manId")
    manEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False
    )
    manMacId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_conta.macId", ondelete="CASCADE"), nullable=False, index=True
    )
    manMcgId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_campanha.mcgId", ondelete="CASCADE"), nullable=False, index=True
    )
    manMcjId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_conjunto.mcjId", ondelete="CASCADE"), nullable=False, index=True
    )
    manAnuncioExterno: Mapped[str] = mapped_column(String(40), nullable=False)
    manNome: Mapped[str] = mapped_column(String(400), nullable=False)
    manStatus: Mapped[str | None] = mapped_column(String(30), nullable=True)
    manMotivo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    manCriadoEmMeta: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Menor dia com impressao ja visto; nunca avanca (so recua) entre syncs.
    manPrimeiroDia: Mapped[date | None] = mapped_column(Date, nullable=True)
    manDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("manDataCriacao")
    manDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao(
        "manDataAtualizacao"
    )
