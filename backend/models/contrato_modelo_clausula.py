from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class ContratoModeloClausula(Base):
    __tablename__ = "contrato_modelo_clausula"

    cmcId: Mapped[int] = IdColumnFactory.int_id("cmcId")
    cmcEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cmcCtmId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("contrato_modelo.ctmId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cmcTitulo: Mapped[str] = mapped_column(String(200), nullable=False)
    cmcTextoPadrao: Mapped[str] = mapped_column(Text, nullable=False)
    cmcUtilizarPadrao: Mapped[bool] = mapped_column(
        # Flag: se entra por padrão no contrato gerado.
        Boolean,
        nullable=False,
        default=True,
    )
    cmcOrdem: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    cmcAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("cmcAtivo")
    cmcDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("cmcDataCriacao")
    cmcDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("cmcDataAtualizacao")

    modelo: Mapped["ContratoModelo"] = relationship(
        "ContratoModelo",
        back_populates="clausulas",
        foreign_keys=[cmcCtmId],
    )
    variacoes: Mapped[list["ContratoModeloClausulaVariacao"]] = relationship(
        "ContratoModeloClausulaVariacao",
        back_populates="clausula",
        cascade="all, delete-orphan",
    )
    contrato_clausulas: Mapped[list["ContratoClausula"]] = relationship(
        "ContratoClausula",
        back_populates="modelo_clausula",
    )

