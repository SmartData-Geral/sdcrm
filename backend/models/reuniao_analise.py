from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class ReuniaoAnalise(Base):
    __tablename__ = "reuniao_analise"

    ranId: Mapped[int] = IdColumnFactory.int_id("ranId")
    ranEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ranOpoId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("oportunidade.opoId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ranUsuId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.usuId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ranTranscricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    ranArquivosResumo: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    ranResumo: Mapped[str | None] = mapped_column(Text, nullable=True)
    ranFeedbackIa: Mapped[str | None] = mapped_column(Text, nullable=True)
    ranLeadScoreSugerido: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ranTemperaturaSugerida: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ranDoresOportunidadesSugeridas: Mapped[str | None] = mapped_column(Text, nullable=True)
    ranObservacoesSugeridas: Mapped[str | None] = mapped_column(Text, nullable=True)
    ranProximosPassosSugeridos: Mapped[str | None] = mapped_column(Text, nullable=True)
    ranPromptUtilizado: Mapped[str | None] = mapped_column(Text, nullable=True)
    ranRespostaJson: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ranModeloIa: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ranProcessadoEm: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ranStatus: Mapped[str] = mapped_column(String(20), nullable=False, default="pendente", index=True)
    ranAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("ranAtivo")
    ranDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("ranDataCriacao")
    ranDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("ranDataAtualizacao")

    oportunidade: Mapped["Oportunidade"] = relationship("Oportunidade", back_populates="analisesReuniao")
