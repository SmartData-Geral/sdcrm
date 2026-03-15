"""add fechamento fields to oportunidade

Revision ID: 0008_opo_fechamento
Revises: 0007_produto_cor
Create Date: 2026-03-13
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0008_opo_fechamento"
down_revision: str | None = "0007_produto_cor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("oportunidade")}

    if "opoFechadoRecorrencia" not in existing_columns:
        op.add_column(
            "oportunidade",
            sa.Column(
                "opoFechadoRecorrencia",
                sa.Integer(),
                nullable=True,
                comment="0 = recorrência, 1 = projeto",
            ),
        )
    if "opoValorFechado" not in existing_columns:
        op.add_column(
            "oportunidade",
            sa.Column("opoValorFechado", sa.Numeric(14, 2), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("oportunidade")}

    if "opoValorFechado" in existing_columns:
        op.drop_column("oportunidade", "opoValorFechado")
    if "opoFechadoRecorrencia" in existing_columns:
        op.drop_column("oportunidade", "opoFechadoRecorrencia")

