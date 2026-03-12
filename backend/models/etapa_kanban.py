from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory


class EtapaKanban(Base):
    __tablename__ = "etapa_kanban"

    etkId: Mapped[int] = IdColumnFactory.int_id("etkId")
    etkEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    etkNome: Mapped[str] = mapped_column(String(100), nullable=False)
    etkOrdem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    etkPipeline: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    etkCor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    etkAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("etkAtivo")
    etkDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("etkDataCriacao")
    etkDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("etkDataAtualizacao")
