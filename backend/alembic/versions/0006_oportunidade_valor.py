"""add valor oportunidade field

Revision ID: 0006_oportunidade_valor
Revises: 0005_usuario_avatar
Create Date: 2026-03-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0006_oportunidade_valor"
down_revision: str | None = "0005_usuario_avatar"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("oportunidade", sa.Column("opoValorOportunidade", sa.Numeric(14, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("oportunidade", "opoValorOportunidade")
