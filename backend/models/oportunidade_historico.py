from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory


class OportunidadeHistorico(Base):
    __tablename__ = "oportunidade_historico"

    ophId: Mapped[int] = IdColumnFactory.int_id("ophId")
    ophEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ophOpoId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("oportunidade.opoId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ophUsuId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.usuId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ophDataRegistro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    ophConteudo: Mapped[str | None] = mapped_column(Text, nullable=True)
    ophAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("ophAtivo")
    ophDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("ophDataCriacao")
    ophDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("ophDataAtualizacao")

    oportunidade: Mapped["Oportunidade"] = relationship(
        "Oportunidade",
        back_populates="historicos",
    )
