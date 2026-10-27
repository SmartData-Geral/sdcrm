"""Leitura do analista (IA) do cockpit de campanhas, guardada por recorte

Revision ID: 0038_cockpit_leitura
Revises: 0037_metas_cockpit
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0038_cockpit_leitura"
down_revision: str | None = "0037_metas_cockpit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "meta_ads_cockpit_leitura"
UNICO = "uq_meta_ads_cockpit_leitura_recorte"
COLUNAS_UNICO = ["mclEmpId", "mclInicio", "mclFim", "mclMacId", "mclSomenteAtivas"]


def upgrade() -> None:
    bind = op.get_bind()
    if TABELA not in set(inspect(bind).get_table_names()):
        op.create_table(
            TABELA,
            sa.Column("mclId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("mclEmpId", sa.Integer(), nullable=False),
            sa.Column("mclInicio", sa.Date(), nullable=False),
            sa.Column("mclFim", sa.Date(), nullable=False),
            sa.Column("mclMacId", sa.Integer(), nullable=False),
            sa.Column("mclSomenteAtivas", sa.Boolean(), nullable=False),
            sa.Column("mclDigest", sa.String(length=64), nullable=False),
            sa.Column("mclLeitura", sa.JSON(), nullable=False),
            sa.Column("mclGeradoEm", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("mclId"),
            sa.UniqueConstraint(*COLUNAS_UNICO, name=UNICO),
        )
    else:
        uniques = {u["name"] for u in inspect(bind).get_unique_constraints(TABELA)}
        if UNICO not in uniques:
            op.create_unique_constraint(UNICO, TABELA, COLUNAS_UNICO)
    # O unico comeca por mclEmpId, entao tambem serve a FK.
    fks = {tuple(fk["constrained_columns"]) for fk in inspect(bind).get_foreign_keys(TABELA)}
    if ("mclEmpId",) not in fks:
        op.create_foreign_key(
            "fk_meta_ads_cockpit_leitura_mclEmpId", TABELA, "empresa", ["mclEmpId"], ["empId"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if TABELA in set(inspect(bind).get_table_names()):
        op.drop_table(TABELA)
