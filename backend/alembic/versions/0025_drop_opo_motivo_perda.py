"""Remove coluna opoMotivoPerda (motivos usam motivo_cancelamento / opoMcaId)

Revision ID: 0025_drop_opo_motivo_perda
Revises: 0024_crm_meta_mensal
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0025_drop_opo_motivo_perda"
down_revision: str | None = "0024_crm_meta_mensal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("oportunidade")}
    if "opoMotivoPerda" in cols:
        op.drop_column("oportunidade", "opoMotivoPerda")


def downgrade() -> None:
    op.add_column(
        "oportunidade",
        sa.Column("opoMotivoPerda", sa.String(length=300), nullable=True),
    )
