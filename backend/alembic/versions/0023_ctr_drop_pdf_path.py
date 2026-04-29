"""Contrato: remove legado ctrPdfPath

Revision ID: 0023_ctr_drop_pdf_path
Revises: 0022_ctr_horas_melhorias_mensais
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0023_ctr_drop_pdf_path"
down_revision: str | None = "0022_ctr_horas_melhorias_mensais"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns("contrato")}
    if "ctrPdfPath" in cols:
        op.drop_column("contrato", "ctrPdfPath")


def downgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns("contrato")}
    if "ctrPdfPath" not in cols:
        op.add_column(
            "contrato",
            sa.Column("ctrPdfPath", sa.String(length=500), nullable=True),
        )
