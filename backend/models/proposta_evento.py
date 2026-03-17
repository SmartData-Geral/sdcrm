from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class PropostaEvento(Base):
    __tablename__ = "proposta_evento"

    pevId: Mapped[int] = IdColumnFactory.int_id("pevId")
    pevEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pevPrpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("proposta.prpId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pevPrvId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("proposta_versao.prvId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pevTipo: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    pevIp: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pevUserAgent: Mapped[str | None] = mapped_column(String(600), nullable=True)
    pevDadosJson: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pevDataEvento: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    pevAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("pevAtivo")
    pevDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("pevDataCriacao")
    pevDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("pevDataAtualizacao")

    proposta: Mapped["Proposta"] = relationship("Proposta", back_populates="eventos")
    versao: Mapped["PropostaVersao | None"] = relationship("PropostaVersao")

