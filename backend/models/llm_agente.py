from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory


class LlmAgente(Base):
    __tablename__ = "llm_agente"
    __table_args__ = (UniqueConstraint("agnEmpId", "agnCodigo", name="uq_llm_agente_emp_codigo"),)

    agnId: Mapped[int] = IdColumnFactory.int_id("agnId")
    agnEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agnCodigo: Mapped[str] = mapped_column(String(80), nullable=False)
    agnNome: Mapped[str] = mapped_column(String(200), nullable=False)
    agnDescricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    agnSystemPrompt: Mapped[str] = mapped_column(Text, nullable=False)
    agnLlmProvider: Mapped[str] = mapped_column(String(40), nullable=False, default="openai")
    agnLlmModel: Mapped[str | None] = mapped_column(String(120), nullable=True)
    agnRespostaJsonEstruturada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    agnAvisoEstrutura: Mapped[str | None] = mapped_column(Text, nullable=True)
    agnAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("agnAtivo")
    agnDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("agnDataCriacao")
    agnDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("agnDataAtualizacao")
