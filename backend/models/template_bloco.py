from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class TemplateBloco(Base):
    __tablename__ = "template_bloco"

    tblId: Mapped[int] = IdColumnFactory.int_id("tblId")
    tblEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tblPtlId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("proposta_template.ptlId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tblTipo: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    tblTitulo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tblSubtitulo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    tblOrdem: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    tblVisivel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tblDadosJson: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tblAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("tblAtivo")
    tblDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("tblDataCriacao")
    tblDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("tblDataAtualizacao")

    template: Mapped["PropostaTemplate"] = relationship("PropostaTemplate", back_populates="template_blocos")
