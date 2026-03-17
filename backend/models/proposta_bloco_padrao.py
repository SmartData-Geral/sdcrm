from datetime import datetime

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class PropostaBlocoPadrao(Base):
    __tablename__ = "proposta_bloco_padrao"

    pbpId: Mapped[int] = IdColumnFactory.int_id("pbpId")
    pbpEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pbpPtlId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("proposta_template.ptlId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pbpTipo: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    pbpTitulo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    pbpSubtitulo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    pbpOrdem: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    pbpVisivel: Mapped[bool] = mapped_column(default=True, nullable=False)
    pbpDadosJson: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pbpAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("pbpAtivo")
    pbpDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("pbpDataCriacao")
    pbpDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("pbpDataAtualizacao")

