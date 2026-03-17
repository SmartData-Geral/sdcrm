from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class PropostaTemplate(Base):
    __tablename__ = "proposta_template"

    ptlId: Mapped[int] = IdColumnFactory.int_id("ptlId")
    ptlEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ptlNome: Mapped[str] = mapped_column(String(200), nullable=False)
    ptlTipoSolucao: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    ptlTipoProposta: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    ptlPrpOrigemId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("proposta.prpId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ptlPadrao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ptlSchemaJson: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ptlConfigJson: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ptlAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("ptlAtivo")
    ptlDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("ptlDataCriacao")
    ptlDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("ptlDataAtualizacao")

    propostas: Mapped[list["Proposta"]] = relationship(
        "Proposta",
        back_populates="template",
        foreign_keys="Proposta.prpTplId",
    )
    proposta_origem: Mapped["Proposta | None"] = relationship("Proposta", foreign_keys=[ptlPrpOrigemId])
    template_blocos: Mapped[list["TemplateBloco"]] = relationship(
        "TemplateBloco",
        back_populates="template",
        cascade="all, delete-orphan",
    )

