from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class PropostaVersao(Base):
    __tablename__ = "proposta_versao"

    prvId: Mapped[int] = IdColumnFactory.int_id("prvId")
    prvEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prvPrpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("proposta.prpId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prvNumero: Mapped[int] = mapped_column(Integer, nullable=False)
    prvTitulo: Mapped[str | None] = mapped_column(Text, nullable=True)
    prvJsonSnapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prvHtmlSnapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    prvPublicada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    prvUsuId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.usuId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prvDataPublicacao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    prvAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("prvAtivo")
    prvDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("prvDataCriacao")
    prvDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("prvDataAtualizacao")

    proposta: Mapped["Proposta"] = relationship("Proposta", back_populates="versoes")

