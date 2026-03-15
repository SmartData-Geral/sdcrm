"""add grupo field to como_conheceu

Revision ID: 0009_como_conheceu_grupo
Revises: 0008_opo_fechamento
Create Date: 2026-03-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0009_como_conheceu_grupo"
down_revision: str | None = "0008_opo_fechamento"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("como_conheceu", sa.Column("ccoGrupo", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("como_conheceu", "ccoGrupo")
