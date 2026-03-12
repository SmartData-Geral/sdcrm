from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory


class MotivoCancelamento(Base):
    __tablename__ = "motivo_cancelamento"

    mcaId: Mapped[int] = IdColumnFactory.int_id("mcaId")
    mcaEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mcaNome: Mapped[str] = mapped_column(String(200), nullable=False)
    mcaAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("mcaAtivo")
    mcaDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("mcaDataCriacao")
    mcaDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("mcaDataAtualizacao")
