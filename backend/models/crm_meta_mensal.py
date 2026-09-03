from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..core.columns import AuditColumnFactory, IdColumnFactory


class CrmMetaMensal(Base):
    __tablename__ = "crm_meta_mensal"

    cmmId: Mapped[int] = IdColumnFactory.int_id("cmmId")
    cmmEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cmmMesReferencia: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cmmQtdRecebimento: Mapped[int] = mapped_column(Integer, nullable=False)
    cmmTaxaConversao: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    cmmMrrMedio: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cmmQtdFechamento: Mapped[int] = mapped_column(Integer, nullable=False)
    cmmMrrIncremental: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    # Meta de valor de projeto (venda pontual). Valor direto em R$, sem derivação:
    # projeto não segue o funil recebimento x conversão x ticket usado pelo MRR.
    cmmValorProjeto: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default="0"
    )
    cmmDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("cmmDataCriacao")
    cmmDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("cmmDataAtualizacao")
