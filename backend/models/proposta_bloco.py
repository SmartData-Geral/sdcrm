from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class PropostaBloco(Base):
    __tablename__ = "proposta_bloco"

    pblId: Mapped[int] = IdColumnFactory.int_id("pblId")
    pblEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pblPrpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("proposta.prpId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pblTipo: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    pblTitulo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    pblSubtitulo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    pblOrdem: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    pblVisivel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pblDadosJson: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pblAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("pblAtivo")
    pblDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("pblDataCriacao")
    pblDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("pblDataAtualizacao")

    proposta: Mapped["Proposta"] = relationship("Proposta", back_populates="blocos")

