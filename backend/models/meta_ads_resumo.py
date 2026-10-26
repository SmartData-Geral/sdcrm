from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import IdColumnFactory
from ..database import Base


class MetaAdsResumo(Base):
    """
    Resumo diario do monitoramento de campanhas Meta: um por (empresa, dia de geracao).

    `mrsInicio`/`mrsFim` e o periodo "anterior" (ontem; na segunda, sexta a domingo).
    `mrsDados` so tem ids, nomes de campanha/anuncio e numeros agregados, nunca dados pessoais.
    `mrsLeitura` e a leitura da IA; quando ela falha, fica nula e `mrsAviso` diz o motivo.
    """

    __tablename__ = "meta_ads_resumo"
    __table_args__ = (UniqueConstraint("mrsEmpId", "mrsData", name="uq_meta_ads_resumo_emp_data"),)

    mrsId: Mapped[int] = IdColumnFactory.int_id("mrsId")
    mrsEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False
    )
    mrsData: Mapped[date] = mapped_column(Date, nullable=False)
    mrsInicio: Mapped[date] = mapped_column(Date, nullable=False)
    mrsFim: Mapped[date] = mapped_column(Date, nullable=False)
    mrsDados: Mapped[dict] = mapped_column(JSON, nullable=False)
    mrsLeitura: Mapped[str | None] = mapped_column(Text, nullable=True)
    mrsAviso: Mapped[str | None] = mapped_column(String(300), nullable=True)
    mrsGeradoEm: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
