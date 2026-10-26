from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import IdColumnFactory
from ..database import Base

STATUS_ABERTO = "aberto"
STATUS_CIENTE = "ciente"
STATUS_RESOLVIDO = "resolvido"


class MetaAdsAlerta(Base):
    """
    Alerta do monitoramento de campanhas Meta.

    No maximo um alerta nao resolvido por (malEmpId, malTipo, malChave): regra garantida no
    codigo (alertas.sincronizar_disparos), pois o banco nao tem indice unico parcial.
    Datas em UTC naive (core.tempo.utcnow).
    """

    __tablename__ = "meta_ads_alerta"
    __table_args__ = (Index("ix_meta_ads_alerta_emp_status", "malEmpId", "malStatus"),)

    malId: Mapped[int] = IdColumnFactory.int_id("malId")
    malEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False
    )
    malTipo: Mapped[str] = mapped_column(String(20), nullable=False)
    # Alvo: "anuncio:<manId>", "campanha:<mcgId>", "conta:<macId>" ou "lead:<opoId>".
    malChave: Mapped[str] = mapped_column(String(60), nullable=False)
    malStatus: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_ABERTO)
    malMensagem: Mapped[str] = mapped_column(String(500), nullable=False)
    malDados: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    malPrimeiroEm: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    malUltimoEm: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    malResolvidoEm: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
