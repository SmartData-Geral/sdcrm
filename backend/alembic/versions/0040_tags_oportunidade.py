"""Tags personalizaveis por empresa e vinculo com oportunidades

Revision ID: 0040_tags_oportunidade
Revises: 0039_pergunta_uso
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0040_tags_oportunidade"
down_revision: str | None = "0039_pergunta_uso"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    tabelas = set(inspect(op.get_bind()).get_table_names())
    if "tag" not in tabelas:
        op.create_table(
            "tag",
            sa.Column("tagId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tagEmpId", sa.Integer(), nullable=False),
            sa.Column("tagNome", sa.String(length=60), nullable=False),
            sa.Column("tagCor", sa.String(length=7), nullable=False),
            sa.Column("tagAtivo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("tagDataCriacao", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("tagDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["tagEmpId"], ["empresa.empId"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("tagId"),
            sa.UniqueConstraint("tagEmpId", "tagNome", name="uq_tag_empresa_nome"),
        )
        op.create_index("ix_tag_tagEmpId", "tag", ["tagEmpId"])
    if "oportunidade_tag" not in tabelas:
        op.create_table(
            "oportunidade_tag",
            sa.Column("otgOpoId", sa.Integer(), nullable=False),
            sa.Column("otgTagId", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["otgOpoId"], ["oportunidade.opoId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["otgTagId"], ["tag.tagId"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("otgOpoId", "otgTagId"),
        )
        op.create_index("ix_oportunidade_tag_otgTagId", "oportunidade_tag", ["otgTagId"])


def downgrade() -> None:
    tabelas = set(inspect(op.get_bind()).get_table_names())
    if "oportunidade_tag" in tabelas:
        op.drop_table("oportunidade_tag")
    if "tag" in tabelas:
        op.drop_table("tag")
