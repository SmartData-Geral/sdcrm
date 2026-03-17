"""add campo logo na empresa

Revision ID: 0012_empresa_logo
Revises: 0011_cadastro_bloco_padrao
Create Date: 2026-03-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0012_empresa_logo"
down_revision: str | None = "0011_cadastro_bloco_padrao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("empresa", sa.Column("empLogoUrl", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("empresa", "empLogoUrl")

