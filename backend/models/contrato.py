from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class Contrato(Base):
    __tablename__ = "contrato"

    __table_args__ = (
        UniqueConstraint("ctrOpoId", name="uq_contrato_ctrOpoId"),
        UniqueConstraint("ctrTokenPublico", name="uq_contrato_token_publico"),
    )

    ctrId: Mapped[int] = IdColumnFactory.int_id("ctrId")
    ctrEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ctrOpoId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("oportunidade.opoId", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    ctrCtmId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("contrato_modelo.ctmId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ctrNome: Mapped[str] = mapped_column(String(200), nullable=False)
    ctrStatus: Mapped[str] = mapped_column(String(20), nullable=False, default="pronto")
    ctrTokenPublico: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # Dados variáveis do contrato (substituem placeholders)
    ctrRazaoSocial: Mapped[str] = mapped_column(String(200), nullable=False)
    ctrCnpj: Mapped[str] = mapped_column(String(20), nullable=False)
    ctrEndereco: Mapped[str] = mapped_column(String(500), nullable=False)
    ctrResponsavelNome: Mapped[str] = mapped_column(String(200), nullable=False)
    ctrResponsavelCpf: Mapped[str] = mapped_column(String(20), nullable=False)
    ctrObjetoContrato: Mapped[str] = mapped_column(Text, nullable=False)
    ctrValorContrato: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    ctrFormaPagamento: Mapped[str] = mapped_column(String(200), nullable=False)
    ctrVigencia: Mapped[str] = mapped_column(String(200), nullable=False)
    ctrDataInicio: Mapped[date] = mapped_column(Date, nullable=False)
    ctrForo: Mapped[str] = mapped_column(String(200), nullable=False)
    ctrReajuste: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Snapshots/artefatos
    ctrHtmlSnapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    ctrPdfPath: Mapped[str | None] = mapped_column(String(500), nullable=True)

    ctrAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("ctrAtivo")
    ctrDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("ctrDataCriacao")
    ctrDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("ctrDataAtualizacao")

    # Relacionamentos
    empresa: Mapped["Empresa"] = relationship(
        "Empresa",
        back_populates="contratos",
        foreign_keys=[ctrEmpId],
    )
    oportunidade: Mapped["Oportunidade | None"] = relationship(
        "Oportunidade",
        back_populates="contratos",
        foreign_keys=[ctrOpoId],
    )
    modelo: Mapped["ContratoModelo"] = relationship(
        "ContratoModelo",
        back_populates="contratos",
        foreign_keys=[ctrCtmId],
    )
    clausulas: Mapped[list["ContratoClausula"]] = relationship(
        "ContratoClausula",
        back_populates="contrato",
        cascade="all, delete-orphan",
    )

