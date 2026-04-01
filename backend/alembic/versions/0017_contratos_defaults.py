"""ajusta defaults de cláusulas por padrão

Revision ID: 0017_contratos_defaults
Revises: 0016_contratos_modulo
Create Date: 2026-03-26
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0017_contratos_defaults"
down_revision: str | None = "0016_contratos_modulo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "contrato_modelo_clausula",
        "cmcUtilizarPadrao",
        existing_type=sa.Boolean(),
        server_default=sa.true(),
    )
    op.alter_column(
        "contrato_clausula",
        "cclUtilizar",
        existing_type=sa.Boolean(),
        server_default=sa.true(),
    )


def downgrade() -> None:
    op.alter_column(
        "contrato_modelo_clausula",
        "cmcUtilizarPadrao",
        existing_type=sa.Boolean(),
        server_default=sa.false(),
    )
    op.alter_column(
        "contrato_clausula",
        "cclUtilizar",
        existing_type=sa.Boolean(),
        server_default=sa.false(),
    )

