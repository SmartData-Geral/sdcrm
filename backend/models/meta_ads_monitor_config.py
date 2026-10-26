from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import AuditColumnFactory, IdColumnFactory
from ..database import Base


class MetaAdsMonitorConfig(Base):
    """Configuracao do monitoramento de campanhas Meta: uma linha por empresa."""

    __tablename__ = "meta_ads_monitor_config"

    mmcId: Mapped[int] = IdColumnFactory.int_id("mmcId")
    mmcEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False, unique=True
    )
    mmcEtkMqlId: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("etapa_kanban.etkId", ondelete="SET NULL"), nullable=True, index=True
    )
    mmcEtkOportunidadeId: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("etapa_kanban.etkId", ondelete="SET NULL"), nullable=True, index=True
    )
    mmcCplFator: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("1.5"))
    mmcGastoSemLead: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("150")
    )
    mmcFrequenciaMax: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("3"))
    mmcQuedaCtrPct: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    mmcHorasSemContato: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    mmcGastoMinRanking: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("50")
    )
    mmcHoraResumo: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    mmcAlertaCpl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    mmcAlertaGasto: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    mmcAlertaFrequencia: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    mmcAlertaCtr: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    mmcAlertaParado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    mmcAlertaSemContato: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Quando o alerta de lead sem contato foi ligado; leads anteriores nao geram alerta.
    mmcSemContatoDesde: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mmcDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("mmcDataCriacao")
    mmcDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao(
        "mmcDataAtualizacao"
    )
