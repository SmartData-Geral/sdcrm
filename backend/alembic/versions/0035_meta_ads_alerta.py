"""Alertas do monitoramento de campanhas Meta

Revision ID: 0035_meta_ads_alerta
Revises: 0034_monitor_config
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0035_meta_ads_alerta"
down_revision: str | None = "0034_monitor_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "meta_ads_alerta"


def _indices(bind) -> set[str]:
    try:
        return {i["name"] for i in inspect(bind).get_indexes(TABELA)}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    if TABELA not in set(inspect(bind).get_table_names()):
        op.create_table(
            TABELA,
            sa.Column("malId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("malEmpId", sa.Integer(), nullable=False),
            sa.Column("malTipo", sa.String(length=20), nullable=False),
            sa.Column("malChave", sa.String(length=60), nullable=False),
            sa.Column("malStatus", sa.String(length=20), nullable=False, server_default="aberto"),
            sa.Column("malMensagem", sa.String(length=500), nullable=False),
            sa.Column("malDados", sa.JSON(), nullable=True),
            sa.Column("malPrimeiroEm", sa.DateTime(timezone=True), nullable=False),
            sa.Column("malUltimoEm", sa.DateTime(timezone=True), nullable=False),
            sa.Column("malResolvidoEm", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("malId"),
        )
    # O indice (malEmpId, malStatus) vem antes da FK e tambem serve a ela.
    if "ix_meta_ads_alerta_emp_status" not in _indices(bind):
        op.create_index("ix_meta_ads_alerta_emp_status", TABELA, ["malEmpId", "malStatus"])
    fks = {tuple(fk["constrained_columns"]) for fk in inspect(bind).get_foreign_keys(TABELA)}
    if ("malEmpId",) not in fks:
        op.create_foreign_key(
            "fk_meta_ads_alerta_malEmpId", TABELA, "empresa", ["malEmpId"], ["empId"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if TABELA in set(inspect(bind).get_table_names()):
        op.drop_table(TABELA)
