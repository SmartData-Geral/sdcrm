from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory


class Empresa(Base):
    __tablename__ = "empresa"

    empId: Mapped[int] = IdColumnFactory.int_id("empId")
    empNome: Mapped[str] = mapped_column(String(200), nullable=False)
    empAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("empAtivo")
    empDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("empDataCriacao")
    empDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("empDataAtualizacao")

    usuarios_vinculo: Mapped[list["UsuarioEmpresa"]] = relationship(
        "UsuarioEmpresa",
        back_populates="empresa",
        cascade="all, delete-orphan",
    )

    clientes: Mapped[list["Cliente"]] = relationship(
        "Cliente",
        back_populates="empresa",
    )

