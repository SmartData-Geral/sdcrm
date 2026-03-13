from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory


class Oportunidade(Base):
    __tablename__ = "oportunidade"

    opoId: Mapped[int] = IdColumnFactory.int_id("opoId")
    opoEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opoTitulo: Mapped[str] = mapped_column(String(300), nullable=False)
    opoNomeContato: Mapped[str | None] = mapped_column(String(200), nullable=True)
    opoEmpresaContato: Mapped[str | None] = mapped_column(String(200), nullable=True)
    opoEmail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opoTelefone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    opoSolucao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    opoProId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("produto.proId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    opoEtkId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("etapa_kanban.etkId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    opoUsuResponsavelId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.usuId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    opoCcoId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("como_conheceu.ccoId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    opoMcaId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("motivo_cancelamento.mcaId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    opoLeadScore: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opoTemperatura: Mapped[str | None] = mapped_column(String(20), nullable=True)
    opoReuniaoConfirmada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    opoPropostaEnviada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    opoDataRecebimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    opoValorOportunidade: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    opoDataUltimoContato: Mapped[date | None] = mapped_column(Date, nullable=True)
    opoDataFechamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    # 0 = recorrência, 1 = projeto
    opoFechadoRecorrencia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opoValorFechado: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    opoStatusFechamento: Mapped[str | None] = mapped_column(String(20), nullable=True)
    opoDoresMotivadores: Mapped[str | None] = mapped_column(Text, nullable=True)
    opoComentarios: Mapped[str | None] = mapped_column(Text, nullable=True)
    opoAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("opoAtivo")
    opoDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("opoDataCriacao")
    opoDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("opoDataAtualizacao")

    historicos: Mapped[list["OportunidadeHistorico"]] = relationship(
        "OportunidadeHistorico",
        back_populates="oportunidade",
        cascade="all, delete-orphan",
    )
