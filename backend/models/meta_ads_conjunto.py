from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import AuditColumnFactory, IdColumnFactory
from ..database import Base


class MetaAdsConjunto(Base):
    """Conjunto de anuncios (ad set) de uma campanha Meta."""

    __tablename__ = "meta_ads_conjunto"
    __table_args__ = (
        UniqueConstraint("mcjMacId", "mcjConjuntoExterno", name="uq_meta_ads_conjunto_conta_ext"),
    )

    mcjId: Mapped[int] = IdColumnFactory.int_id("mcjId")
    mcjEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False, index=True
    )
    mcjMacId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_conta.macId", ondelete="CASCADE"), nullable=False, index=True
    )
    mcjMcgId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_campanha.mcgId", ondelete="CASCADE"), nullable=False, index=True
    )
    mcjConjuntoExterno: Mapped[str] = mapped_column(String(40), nullable=False)
    mcjNome: Mapped[str] = mapped_column(String(400), nullable=False)
    mcjStatus: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mcjDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("mcjDataCriacao")
    mcjDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao(
        "mcjDataAtualizacao"
    )
