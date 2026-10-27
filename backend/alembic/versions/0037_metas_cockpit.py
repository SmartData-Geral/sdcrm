"""Metas de CPL e taxa de MQL do cockpit de campanhas

Revision ID: 0037_metas_cockpit
Revises: 0036_meta_ads_resumo
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0037_metas_cockpit"
down_revision: str | None = "0036_meta_ads_resumo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "meta_ads_monitor_config"


def _colunas(bind) -> set[str]:
    return {c["name"] for c in inspect(bind).get_columns(TABELA)}


def upgrade() -> None:
    bind = op.get_bind()
    existentes = _colunas(bind)
    if "mmcMetaCpl" not in existentes:
        op.add_column(
            TABELA,
            sa.Column("mmcMetaCpl", sa.Numeric(14, 2), nullable=False, server_default="150"),
        )
    if "mmcMetaTaxaMql" not in existentes:
        op.add_column(
            TABELA,
            sa.Column("mmcMetaTaxaMql", sa.Numeric(5, 2), nullable=False, server_default="10"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    existentes = _colunas(bind)
    for coluna in ("mmcMetaTaxaMql", "mmcMetaCpl"):
        if coluna in existentes:
            op.drop_column(TABELA, coluna)
