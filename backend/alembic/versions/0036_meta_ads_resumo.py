"""Resumo diario do monitoramento de campanhas Meta

Revision ID: 0036_meta_ads_resumo
Revises: 0035_meta_ads_alerta
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0036_meta_ads_resumo"
down_revision: str | None = "0035_meta_ads_alerta"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "meta_ads_resumo"
UNICO = "uq_meta_ads_resumo_emp_data"


def upgrade() -> None:
    bind = op.get_bind()
    if TABELA not in set(inspect(bind).get_table_names()):
        op.create_table(
            TABELA,
            sa.Column("mrsId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("mrsEmpId", sa.Integer(), nullable=False),
            sa.Column("mrsData", sa.Date(), nullable=False),
            sa.Column("mrsInicio", sa.Date(), nullable=False),
            sa.Column("mrsFim", sa.Date(), nullable=False),
            sa.Column("mrsDados", sa.JSON(), nullable=False),
            sa.Column("mrsLeitura", sa.Text(), nullable=True),
            sa.Column("mrsAviso", sa.String(length=300), nullable=True),
            sa.Column("mrsGeradoEm", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("mrsId"),
            sa.UniqueConstraint("mrsEmpId", "mrsData", name=UNICO),
        )
    else:
        uniques = {u["name"] for u in inspect(bind).get_unique_constraints(TABELA)}
        if UNICO not in uniques:
            op.create_unique_constraint(UNICO, TABELA, ["mrsEmpId", "mrsData"])
    # O unico (mrsEmpId, mrsData) vem antes da FK e tambem serve a ela.
    fks = {tuple(fk["constrained_columns"]) for fk in inspect(bind).get_foreign_keys(TABELA)}
    if ("mrsEmpId",) not in fks:
        op.create_foreign_key(
            "fk_meta_ads_resumo_mrsEmpId", TABELA, "empresa", ["mrsEmpId"], ["empId"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if TABELA in set(inspect(bind).get_table_names()):
        op.drop_table(TABELA)
