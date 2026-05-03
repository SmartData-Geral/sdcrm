from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.columns import AuditColumnFactory, IdColumnFactory
from ..database import Base


class OportunidadeSmartAgenteMensagem(Base):
    """Mensagens do chat Smart Agente por oportunidade (persistidas)."""

    __tablename__ = "oportunidade_smart_agente_mensagem"

    osmId: Mapped[int] = IdColumnFactory.int_id("osmId")
    osmEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    osmOpoId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("oportunidade.opoId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    osmUsuId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.usuId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    osmRole: Mapped[str] = mapped_column(String(12), nullable=False)
    osmContent: Mapped[str] = mapped_column(Text, nullable=False)
    osmDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("osmDataCriacao")

    oportunidade: Mapped["Oportunidade"] = relationship("Oportunidade", back_populates="smartAgenteMensagens")
