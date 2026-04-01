from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class ContratoModelo(Base):
    __tablename__ = "contrato_modelo"

    ctmId: Mapped[int] = IdColumnFactory.int_id("ctmId")
    ctmEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ctmNome: Mapped[str] = mapped_column(String(200), nullable=False)
    ctmDescricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    ctmAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("ctmAtivo")
    ctmDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("ctmDataCriacao")
    ctmDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("ctmDataAtualizacao")

    empresa: Mapped["Empresa"] = relationship(
        "Empresa",
        back_populates="contratos_modelo",
        foreign_keys=[ctmEmpId],
    )
    clausulas: Mapped[list["ContratoModeloClausula"]] = relationship(
        "ContratoModeloClausula",
        back_populates="modelo",
        cascade="all, delete-orphan",
    )
    contratos: Mapped[list["Contrato"]] = relationship(
        "Contrato",
        back_populates="modelo",
    )

