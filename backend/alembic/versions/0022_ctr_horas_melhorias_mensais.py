"""Contrato: horas de melhorias mensais (macro {{horas_melhorias_mensais}})

Revision ID: 0022_ctr_horas_melhorias_mensais
Revises: 0021_ctr_campos_v2
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0022_ctr_horas_melhorias_mensais"
down_revision: str | None = "0021_ctr_campos_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns("contrato")}

    if "ctrHorasMelhoriasMensais" not in cols:
        op.add_column(
            "contrato",
            sa.Column(
                "ctrHorasMelhoriasMensais",
                sa.Integer(),
                nullable=False,
                server_default="8",
            ),
        )
        op.alter_column("contrato", "ctrHorasMelhoriasMensais", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns("contrato")}
    if "ctrHorasMelhoriasMensais" in cols:
        op.drop_column("contrato", "ctrHorasMelhoriasMensais")
