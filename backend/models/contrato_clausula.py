from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class ContratoClausula(Base):
    __tablename__ = "contrato_clausula"

    cclId: Mapped[int] = IdColumnFactory.int_id("cclId")
    cclEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cclCtrId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("contrato.ctrId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cclCmcId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("contrato_modelo_clausula.cmcId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cclCmvId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("contrato_modelo_clausula_variacao.cmvId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Valores editáveis no contrato específico
    cclTitulo: Mapped[str] = mapped_column(String(200), nullable=False)
    cclTexto: Mapped[str] = mapped_column(Text, nullable=False)

    # Regras de inclusão/ordenação
    cclUtilizar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cclOrdemBase: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cclOrdemFinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cclAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("cclAtivo")
    cclDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("cclDataCriacao")
    cclDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("cclDataAtualizacao")

    contrato: Mapped["Contrato"] = relationship(
        "Contrato",
        back_populates="clausulas",
        foreign_keys=[cclCtrId],
    )
    modelo_clausula: Mapped["ContratoModeloClausula"] = relationship(
        "ContratoModeloClausula",
        back_populates="contrato_clausulas",
        foreign_keys=[cclCmcId],
    )
    modelo_clausula_variacao: Mapped["ContratoModeloClausulaVariacao | None"] = relationship(
        "ContratoModeloClausulaVariacao",
        back_populates="contrato_clausulas",
        foreign_keys=[cclCmvId],
    )

