from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class ContratoModeloClausulaVariacao(Base):
    __tablename__ = "contrato_modelo_clausula_variacao"

    cmvId: Mapped[int] = IdColumnFactory.int_id("cmvId")
    cmvEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cmvCmcId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("contrato_modelo_clausula.cmcId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cmvNome: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cmvTitulo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cmvTexto: Mapped[str] = mapped_column(Text, nullable=False)
    cmvAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("cmvAtivo")
    cmvDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("cmvDataCriacao")
    cmvDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("cmvDataAtualizacao")

    clausula: Mapped["ContratoModeloClausula"] = relationship(
        "ContratoModeloClausula",
        back_populates="variacoes",
        foreign_keys=[cmvCmcId],
    )
    contrato_clausulas: Mapped[list["ContratoClausula"]] = relationship(
        "ContratoClausula",
        back_populates="modelo_clausula_variacao",
    )

