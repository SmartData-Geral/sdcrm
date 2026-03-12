"""add color field to produto

Revision ID: 0007_produto_cor
Revises: 0006_oportunidade_valor
Create Date: 2026-03-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0007_produto_cor"
down_revision: str | None = "0006_oportunidade_valor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("produto", sa.Column("proCor", sa.String(length=7), nullable=True))


def downgrade() -> None:
    op.drop_column("produto", "proCor")
