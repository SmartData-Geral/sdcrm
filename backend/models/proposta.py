from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class Proposta(Base):
    __tablename__ = "proposta"

    prpId: Mapped[int] = IdColumnFactory.int_id("prpId")
    prpEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prpOpoId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("oportunidade.opoId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prpTplId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("proposta_template.ptlId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prpTitulo: Mapped[str] = mapped_column(String(300), nullable=False)
    prpTipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    prpStatus: Mapped[str] = mapped_column(String(20), nullable=False, default="rascunho", index=True)
    prpTokenPublico: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    prpVersaoAtual: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prpUsuCriadorId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.usuId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prpUsuEditorId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.usuId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prpUsuResponsavelId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.usuId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prpNomeContato: Mapped[str | None] = mapped_column(String(200), nullable=True)
    prpEmailContato: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prpWhatsappContato: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prpObservacaoInterna: Mapped[str | None] = mapped_column(Text, nullable=True)
    prpJsonConfiguracao: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prpHtmlRenderizado: Mapped[str | None] = mapped_column(Text, nullable=True)
    prpPublicadaEm: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    prpAceitaEm: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    prpAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("prpAtivo")
    prpDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("prpDataCriacao")
    prpDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("prpDataAtualizacao")

    oportunidade: Mapped["Oportunidade"] = relationship("Oportunidade", back_populates="propostas")
    template: Mapped["PropostaTemplate | None"] = relationship(
        "PropostaTemplate",
        back_populates="propostas",
        foreign_keys=[prpTplId],
    )
    criador: Mapped["Usuario | None"] = relationship("Usuario", foreign_keys=[prpUsuCriadorId])
    editor: Mapped["Usuario | None"] = relationship("Usuario", foreign_keys=[prpUsuEditorId])
    responsavel: Mapped["Usuario | None"] = relationship("Usuario", foreign_keys=[prpUsuResponsavelId])

    versoes: Mapped[list["PropostaVersao"]] = relationship(
        "PropostaVersao",
        back_populates="proposta",
        cascade="all, delete-orphan",
    )
    blocos: Mapped[list["PropostaBloco"]] = relationship(
        "PropostaBloco",
        back_populates="proposta",
        cascade="all, delete-orphan",
    )
    eventos: Mapped[list["PropostaEvento"]] = relationship(
        "PropostaEvento",
        back_populates="proposta",
        cascade="all, delete-orphan",
    )

