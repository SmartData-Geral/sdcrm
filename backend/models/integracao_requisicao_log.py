from datetime import datetime

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class IntegracaoRequisicaoLog(Base):
    """
    Log de toda requisição a /api/v1/*, inclusive as que nunca chegam ao service
    (401 na dependency, 422 na validação do Pydantic).

    O payload gravado é redigido: só chaves da allowlist, e-mail e telefone mascarados.
    Os dados reais já vivem na oportunidade, e irlOpoId aponta para lá -- este log existe
    para depurar integração, não para ser uma segunda base de contatos.
    """

    __tablename__ = "integracao_requisicao_log"

    irlId: Mapped[int] = IdColumnFactory.int_id("irlId")
    # Nulo quando a autenticação falha antes de sabermos de qual empresa se trata.
    irlEmpId: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("empresa.empId", ondelete="CASCADE"), nullable=True, index=True
    )
    irlIchId: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("integracao_chave.ichId", ondelete="SET NULL"), nullable=True, index=True
    )
    # Só a parte pública da chave apresentada -- nunca o segredo.
    irlPrefixoInformado: Mapped[str | None] = mapped_column(String(40), nullable=True)
    irlRota: Mapped[str] = mapped_column(String(120), nullable=False)
    irlMetodo: Mapped[str] = mapped_column(String(10), nullable=False)
    irlOrigemSistema: Mapped[str | None] = mapped_column(String(60), nullable=True)
    irlExternalId: Mapped[str | None] = mapped_column(String(120), nullable=True)
    irlStatusHttp: Mapped[int] = mapped_column(Integer, nullable=False)
    # created | updated | novo_ciclo | invalid | unauthorized | conflict | error
    irlResultado: Mapped[str] = mapped_column(String(20), nullable=False)
    irlOpoId: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("oportunidade.opoId", ondelete="SET NULL"), nullable=True, index=True
    )
    irlPayloadJson: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    irlErroJson: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    irlIp: Mapped[str | None] = mapped_column(String(64), nullable=True)
    irlUserAgent: Mapped[str | None] = mapped_column(String(600), nullable=True)
    irlDuracaoMs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    irlAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("irlAtivo")
    irlDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("irlDataCriacao")
    irlDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("irlDataAtualizacao")
