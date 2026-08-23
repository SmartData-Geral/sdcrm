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
    # True = receita única (não entra no MRR); False = recorrente / mensal
    opoReceitaPontual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    opoDataUltimoContato: Mapped[date | None] = mapped_column(Date, nullable=True)
    opoDataFechamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    # 0 = recorrência, 1 = projeto
    opoFechadoRecorrencia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opoValorFechado: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    opoStatusFechamento: Mapped[str | None] = mapped_column(String(20), nullable=True)
    opoDoresMotivadores: Mapped[str | None] = mapped_column(Text, nullable=True)
    opoComentarios: Mapped[str | None] = mapped_column(Text, nullable=True)
    # --- Rastreio de origem (integração de entrada de leads) ---
    # `source` cru do payload. Gravado sempre, independente de opoCcoId ter sido
    # resolvido, para que renomear um "como conheceu" nunca perca o rastro de máquina.
    opoOrigemSistema: Mapped[str | None] = mapped_column(String(60), nullable=True)
    opoOrigemExternalId: Mapped[str | None] = mapped_column(String(120), nullable=True)
    opoUtmSource: Mapped[str | None] = mapped_column(String(100), nullable=True)
    opoUtmMedium: Mapped[str | None] = mapped_column(String(100), nullable=True)
    opoUtmCampaign: Mapped[str | None] = mapped_column(String(150), nullable=True)
    opoUtmContent: Mapped[str | None] = mapped_column(String(150), nullable=True)
    opoUtmTerm: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # Cópias normalizadas usadas pelo dedup. Existem como coluna própria porque
    # LOWER()/REGEXP no WHERE invalidaria o índice no MySQL.
    opoEmailNormalizado: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opoTelefoneNormalizado: Mapped[str | None] = mapped_column(String(20), nullable=True)
    opoIchId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("integracao_chave.ichId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Ciclo anterior encerrado do mesmo contato: quando um lead volta depois de a
    # oportunidade ter sido ganha/perdida, abrimos uma nova e apontamos para a antiga.
    opoOpoAnteriorId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("oportunidade.opoId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    opoAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("opoAtivo")
    opoDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("opoDataCriacao")
    opoDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("opoDataAtualizacao")

    historicos: Mapped[list["OportunidadeHistorico"]] = relationship(
        "OportunidadeHistorico",
        back_populates="oportunidade",
        cascade="all, delete-orphan",
    )
    propostas: Mapped[list["Proposta"]] = relationship(
        "Proposta",
        back_populates="oportunidade",
        cascade="all, delete-orphan",
    )
    analisesReuniao: Mapped[list["ReuniaoAnalise"]] = relationship(
        "ReuniaoAnalise",
        back_populates="oportunidade",
        cascade="all, delete-orphan",
    )

    contratos: Mapped[list["Contrato"]] = relationship(
        "Contrato",
        back_populates="oportunidade",
        cascade="all, delete-orphan",
    )
    smartAgenteMensagens: Mapped[list["OportunidadeSmartAgenteMensagem"]] = relationship(
        "OportunidadeSmartAgenteMensagem",
        back_populates="oportunidade",
        cascade="all, delete-orphan",
    )
