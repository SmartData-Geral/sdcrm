from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory


class ComoConheceu(Base):
    __tablename__ = "como_conheceu"

    ccoId: Mapped[int] = IdColumnFactory.int_id("ccoId")
    ccoEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ccoNome: Mapped[str] = mapped_column(String(200), nullable=False)
    ccoAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("ccoAtivo")
    ccoDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("ccoDataCriacao")
    ccoDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("ccoDataAtualizacao")
