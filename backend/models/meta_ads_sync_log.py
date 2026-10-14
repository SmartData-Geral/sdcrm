from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import IdColumnFactory
from ..core.tempo import utcnow
from ..database import Base


class MetaAdsSyncLog(Base):
    """Uma execucao de sincronizacao de uma conta. Origem: agendada|manual|periodo|carga_inicial."""

    __tablename__ = "meta_ads_sync_log"

    mslId: Mapped[int] = IdColumnFactory.int_id("mslId")
    mslMacId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_conta.macId", ondelete="CASCADE"), nullable=False, index=True
    )
    mslInicio: Mapped[date] = mapped_column(Date, nullable=False)
    mslFim: Mapped[date] = mapped_column(Date, nullable=False)
    mslOrigem: Mapped[str] = mapped_column(String(20), nullable=False)
    mslStatus: Mapped[str] = mapped_column(String(20), nullable=False)
    mslLinhas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mslLeadsVinculados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mslErro: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mslDuracaoMs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mslDataExecucao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )
