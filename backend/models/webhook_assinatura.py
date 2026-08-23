from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class WebhookAssinatura(Base):
    """
    Um destino inscrito em eventos do CRM.

    whaSegredo fica em texto puro por necessidade: o HMAC precisa ser recalculado a cada
    envio, entao nao ha como guardar so o hash. Mitigacoes: exibido uma unica vez na
    criacao, rotacionavel, nunca devolvido por GET e nunca escrito em log.
    """

    __tablename__ = "webhook_assinatura"

    whaId: Mapped[int] = IdColumnFactory.int_id("whaId")
    whaEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False, index=True
    )
    whaNome: Mapped[str] = mapped_column(String(120), nullable=False)
    whaUrl: Mapped[str] = mapped_column(String(600), nullable=False)
    whaSegredo: Mapped[str] = mapped_column(String(80), nullable=False)
    whaEventosJson: Mapped[list] = mapped_column(JSON, nullable=False)
    whaHeadersJson: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Desativa sozinha depois de N falhas seguidas, para um Zap abandonado nao queimar
    # o worker indefinidamente.
    whaFalhasConsecutivas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    whaDesativadaEm: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    whaDesativadaMotivo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    whaUltimaEntregaEm: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    whaUltimoStatusHttp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    whaAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("whaAtivo")
    whaDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("whaDataCriacao")
    whaDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao(
        "whaDataAtualizacao"
    )
