from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import IdColumnFactory
from ..database import Base


class MetaAdsCockpitLeitura(Base):
    """
    Leitura do analista (IA) do cockpit de campanhas: uma por recorte.

    Recorte = (empresa, inicio, fim, conta, somente ativas). `mclMacId` 0 significa todas as contas
    (sem FK, de proposito). `mclDigest` e a impressao digital do contexto enviado a IA, metas
    incluidas: se mudar, a leitura guardada fica "desatualizada". `mclLeitura` guarda
    `{"leitura": {...} | None, "texto": str | None}` e nunca dados pessoais.
    """

    __tablename__ = "meta_ads_cockpit_leitura"
    __table_args__ = (
        UniqueConstraint(
            "mclEmpId", "mclInicio", "mclFim", "mclMacId", "mclSomenteAtivas",
            name="uq_meta_ads_cockpit_leitura_recorte",
        ),
    )

    mclId: Mapped[int] = IdColumnFactory.int_id("mclId")
    mclEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False
    )
    mclInicio: Mapped[date] = mapped_column(Date, nullable=False)
    mclFim: Mapped[date] = mapped_column(Date, nullable=False)
    mclMacId: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mclSomenteAtivas: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mclDigest: Mapped[str] = mapped_column(String(64), nullable=False)
    mclLeitura: Mapped[dict] = mapped_column(JSON, nullable=False)
    mclGeradoEm: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
