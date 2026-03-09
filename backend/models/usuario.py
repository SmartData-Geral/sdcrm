from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory


class Usuario(Base):
    __tablename__ = "usuario"

    usuId: Mapped[int] = IdColumnFactory.int_id("usuId")
    usuNome: Mapped[str] = mapped_column(String(200), nullable=False)
    usuEmail: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    usuSenhaHash: Mapped[str] = mapped_column(String(255), nullable=False)
    usuAdmin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    usuPerfil: Mapped[str | None] = mapped_column(String(50), nullable=True)
    usuAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("usuAtivo")
    usuDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("usuDataCriacao")
    usuDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("usuDataAtualizacao")

    empresas_vinculo: Mapped[list["UsuarioEmpresa"]] = relationship(
        "UsuarioEmpresa",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )


