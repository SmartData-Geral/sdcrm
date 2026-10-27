"""Contagem diaria de perguntas ao analista do cockpit, por usuario

Revision ID: 0039_pergunta_uso
Revises: 0038_cockpit_leitura
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0039_pergunta_uso"
down_revision: str | None = "0038_cockpit_leitura"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "meta_ads_pergunta_uso"
UNICO = "uq_meta_ads_pergunta_uso_usuario_data"
COLUNAS_UNICO = ["mpuUsuId", "mpuData"]


def upgrade() -> None:
    bind = op.get_bind()
    if TABELA not in set(inspect(bind).get_table_names()):
        op.create_table(
            TABELA,
            sa.Column("mpuId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("mpuUsuId", sa.Integer(), nullable=False),
            sa.Column("mpuData", sa.Date(), nullable=False),
            sa.Column("mpuQuantidade", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("mpuId"),
            sa.UniqueConstraint(*COLUNAS_UNICO, name=UNICO),
        )
    else:
        uniques = {u["name"] for u in inspect(bind).get_unique_constraints(TABELA)}
        if UNICO not in uniques:
            op.create_unique_constraint(UNICO, TABELA, COLUNAS_UNICO)
    # O unico comeca por mpuUsuId, entao tambem serve a FK.
    fks = {tuple(fk["constrained_columns"]) for fk in inspect(bind).get_foreign_keys(TABELA)}
    if ("mpuUsuId",) not in fks:
        op.create_foreign_key(
            "fk_meta_ads_pergunta_uso_mpuUsuId", TABELA, "usuario", ["mpuUsuId"], ["usuId"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if TABELA in set(inspect(bind).get_table_names()):
        op.drop_table(TABELA)
