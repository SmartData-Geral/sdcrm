from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..core.columns import AtivoColumnFactory, AuditColumnFactory, IdColumnFactory


class Tag(Base):
    __tablename__ = "tag"
    __table_args__ = (UniqueConstraint("tagEmpId", "tagNome", name="uq_tag_empresa_nome"),)

    tagId: Mapped[int] = IdColumnFactory.int_id("tagId")
    tagEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tagNome: Mapped[str] = mapped_column(String(60), nullable=False)
    tagCor: Mapped[str] = mapped_column(String(7), nullable=False)
    tagAtivo: Mapped[bool] = AtivoColumnFactory.bool_ativo("tagAtivo")
    tagDataCriacao: Mapped[datetime] = AuditColumnFactory.datetime_criacao("tagDataCriacao")
    tagDataAtualizacao: Mapped[datetime | None] = AuditColumnFactory.datetime_atualizacao("tagDataAtualizacao")


class OportunidadeTag(Base):
    __tablename__ = "oportunidade_tag"

    # A PK comeca por otgOpoId, entao tambem serve a FK do lead.
    otgOpoId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("oportunidade.opoId", ondelete="CASCADE"),
        primary_key=True,
    )
    otgTagId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tag.tagId", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
