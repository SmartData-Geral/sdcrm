"""add avatar url to usuario

Revision ID: 0005_usuario_avatar
Revises: 0004_seed_etapas
Create Date: 2026-03-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_usuario_avatar"
down_revision: str | None = "0004_seed_etapas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("usuario", sa.Column("usuAvatarUrl", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("usuario", "usuAvatarUrl")
