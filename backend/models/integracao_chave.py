from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory
from ..database import Base


class IntegracaoChave(Base):
    """
    Chave de API por integração (Zapier, Meta Lead Ads, formulário do site...).

    O segredo nunca é persistido: guardamos o prefixo público, que permite localizar
    a linha, e o hash do segredo, que permite verificá-lo. A empresa vem daqui --
    rotas autenticadas por chave NÃO usam o header X-Company-Id.
    """

    __tablename__ = "integracao_chave"

    ichId: Mapped[int] = IdColumnFactory.int_id("ichId")
    ichEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ichNome: Mapped[str] = mapped_column(String(120), nullable=False)
    ichDescricao: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Parte pública da chave. Um hash não é pesquisável, então é o prefixo -- único e
    # indexado -- que transforma a autenticação em uma única leitura O(1).
    ichPrefixo: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    ichHashSecret: Mapped[str] = mapped_column(String(64), nullable=False)
    ichEscopos: Mapped[str] = mapped_column(String(255), nullable=False, default="leads:write")
    ichUsuResponsavelPadraoId: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuario.usuId", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ichUltimoUsoEm: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ichExpiraEm: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ichRevogadaEm: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ichRevogadaUsuId: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuario.usuId", ondelete="SET NULL"), nullable=True
    )
    ichCriadaUsuId: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuario.usuId", ondelete="SET NULL"), nullable=True
    )
    ichAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("ichAtivo")
    ichDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("ichDataCriacao")
    ichDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("ichDataAtualizacao")
