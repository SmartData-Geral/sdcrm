from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..core.columns import AtivoColumnFactory, AuditColumnFactory, EmpIdColumnFactory, IdColumnFactory


class Cliente(Base):
    __tablename__ = "cliente"

    cliId: Mapped[int] = IdColumnFactory.int_id("cliId")
    cliEmpId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cliNome: Mapped[str] = mapped_column(String(200), nullable=False)
    cliEmail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cliTelefone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cliAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("cliAtivo")
    cliDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("cliDataCriacao")
    cliDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("cliDataAtualizacao")

    empresa: Mapped["Empresa | None"] = relationship("Empresa", back_populates="clientes")

