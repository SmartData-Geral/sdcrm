from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory


class Produto(Base):
    __tablename__ = "produto"

    proId: Mapped[int] = IdColumnFactory.int_id("proId")
    proEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proNome: Mapped[str] = mapped_column(String(200), nullable=False)
    proCor: Mapped[str | None] = mapped_column(String(7), nullable=True)
    proAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("proAtivo")
    proDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("proDataCriacao")
    proDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("proDataAtualizacao")
