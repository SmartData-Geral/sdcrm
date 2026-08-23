from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class WebhookEvento(Base):
    """
    O outbox transacional: um registro por fato de negocio.

    A insercao acontece na MESMA transacao da mudanca que o originou -- por isso o
    emitter faz apenas db.add() e nunca commit. Disparar HTTP dentro da request daria
    latencia e eventos de mudancas que sofreram rollback; inserir depois do commit
    perderia eventos numa queda entre os dois.

    O payload e congelado no momento da emissao: uma entrega retentada 6 horas depois
    reporta o estado do evento, nao o estado atual.
    """

    __tablename__ = "webhook_evento"
    __table_args__ = (
        UniqueConstraint("wevEmpId", "wevChaveIdempotencia", name="uq_webhook_evento_idem"),
    )

    wevId: Mapped[int] = IdColumnFactory.int_id("wevId")
    wevEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False, index=True
    )
    wevTipo: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    wevChaveIdempotencia: Mapped[str | None] = mapped_column(String(120), nullable=True)
    wevOpoId: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("oportunidade.opoId", ondelete="SET NULL"), nullable=True, index=True
    )
    wevPayloadJson: Mapped[dict] = mapped_column(JSON, nullable=False)
    wevOrigem: Mapped[str] = mapped_column(String(20), nullable=False, default="ui")
    # pendente | processado | ignorado
    wevStatus: Mapped[str] = mapped_column(String(20), nullable=False, default="pendente")
    wevProcessadoEm: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    wevAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("wevAtivo")
    wevDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("wevDataCriacao")
    wevDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao(
        "wevDataAtualizacao"
    )
