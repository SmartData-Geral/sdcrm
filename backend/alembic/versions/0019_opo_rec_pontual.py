"""add opoReceitaPontual to oportunidade

Revision ID: 0019_opo_rec_pontual
Revises: 0018_seed_upsell_etapas
Create Date: 2026-04-11

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0019_opo_rec_pontual"
down_revision: str | None = "0018_seed_upsell_etapas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("oportunidade")}
    if "opoReceitaPontual" in cols:
        return
    op.add_column(
        "oportunidade",
        sa.Column(
            "opoReceitaPontual",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("oportunidade")}
    if "opoReceitaPontual" not in cols:
        return
    op.drop_column("oportunidade", "opoReceitaPontual")
