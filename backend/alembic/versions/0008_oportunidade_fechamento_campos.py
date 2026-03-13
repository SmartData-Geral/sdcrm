"""add fechamento fields to oportunidade

Revision ID: 0008_oportunidade_fechamento_campos
Revises: 0007_produto_cor
Create Date: 2026-03-13
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0008_oportunidade_fechamento_campos"
down_revision: str | None = "0007_produto_cor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "oportunidade",
        sa.Column(
            "opoFechadoRecorrencia",
            sa.Integer(),
            nullable=True,
            comment="0 = recorrência, 1 = projeto",
        ),
    )
    op.add_column(
        "oportunidade",
        sa.Column("opoValorFechado", sa.Numeric(14, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("oportunidade", "opoValorFechado")
    op.drop_column("oportunidade", "opoFechadoRecorrencia")

