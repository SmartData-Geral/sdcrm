from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import AuditColumnFactory, IdColumnFactory
from ..database import Base


class WebhookEntrega(Base):
    """
    Uma tentativa de entrega de um evento para uma assinatura. E a unidade de retry e,
    ao mesmo tempo, o log de entrega que a tela de administracao mostra.

    Separada de webhook_evento de proposito: assim uma assinatura criada hoje nao recebe
    eventos antigos retroativamente, e um endpoint lento nao trava o fan-out dos demais.
    """

    __tablename__ = "webhook_entrega"
    __table_args__ = (
        UniqueConstraint("wenWevId", "wenWhaId", name="uq_webhook_entrega_evento_assinatura"),
    )

    wenId: Mapped[int] = IdColumnFactory.int_id("wenId")
    wenEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False, index=True
    )
    wenWevId: Mapped[int] = mapped_column(
        Integer, ForeignKey("webhook_evento.wevId", ondelete="CASCADE"), nullable=False, index=True
    )
    wenWhaId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("webhook_assinatura.whaId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # pendente | retentando | entregue | falha_permanente | cancelada
    wenStatus: Mapped[str] = mapped_column(String(20), nullable=False, default="pendente")
    wenTentativas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wenProximaTentativaEm: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    wenUltimaTentativaEm: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    wenUltimoStatusHttp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wenUltimoErro: Mapped[str | None] = mapped_column(String(500), nullable=True)
    wenRespostaTrecho: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    wenDuracaoMs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Quem reivindicou a linha, no formato "<host>:<pid>". Com SKIP LOCKED, N workers
    # sao corretos; o carimbo serve para recuperar linhas orfas de um processo morto.
    wenClaimedPor: Mapped[str | None] = mapped_column(String(80), nullable=True)
    wenClaimedEm: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    wenHistoricoJson: Mapped[list | None] = mapped_column(JSON, nullable=True)
    wenDataEntrega: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    wenDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("wenDataCriacao")
    wenDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao(
        "wenDataAtualizacao"
    )
