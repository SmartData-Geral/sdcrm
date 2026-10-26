from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base

STATUS_PENDENTE = "pendente"
STATUS_SINCRONIZANDO = "sincronizando"
STATUS_OK = "ok"
STATUS_AVISO = "aviso"
STATUS_ERRO = "erro"
# Separado de "erro" porque a rodada diaria pula estas contas ate alguem trocar o token.
STATUS_TOKEN_INVALIDO = "token_invalido"
# Token com permissao de escrita: tambem pulado na rodada diaria ate trocarem o token.
STATUS_PERMISSAO_EXCESSIVA = "permissao_excessiva"


class MetaAdsConta(Base):
    """
    Conta de anuncios do Meta conectada por uma empresa.

    macToken guarda o token do System User cifrado (core/cripto). Ele nunca sai pela API:
    a tela mostra so macTokenFinal ("....1234").
    """

    __tablename__ = "meta_ads_conta"
    __table_args__ = (
        UniqueConstraint("macEmpId", "macContaExterna", name="uq_meta_ads_conta_emp_ext"),
    )

    macId: Mapped[int] = IdColumnFactory.int_id("macId")
    macEmpId: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=False, index=True
    )
    macNome: Mapped[str] = mapped_column(String(150), nullable=False)
    macContaExterna: Mapped[str] = mapped_column(String(40), nullable=False)
    macToken: Mapped[str] = mapped_column(Text, nullable=False)
    macTokenFinal: Mapped[str] = mapped_column(String(4), nullable=False)
    macMoeda: Mapped[str | None] = mapped_column(String(3), nullable=True)
    macFuso: Mapped[str | None] = mapped_column(String(60), nullable=True)
    macStatus: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_PENDENTE)
    macMensagem: Mapped[str | None] = mapped_column(String(500), nullable=True)
    macUltimaSync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Quando a trava de sincronizacao foi pega; trava com mais de 30 min e considerada morta.
    macSyncIniciadaEm: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    macCargaInicialFeita: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    macAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("macAtivo")
    macDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("macDataCriacao")
    macDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao(
        "macDataAtualizacao"
    )
