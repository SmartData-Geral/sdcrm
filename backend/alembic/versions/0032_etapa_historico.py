"""Registro estruturado de mudanca de estagio do funil

Revision ID: 0032_etapa_historico
Revises: 0031_meta_ads_anuncios
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0032_etapa_historico"
down_revision: str | None = "0031_meta_ads_anuncios"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "oportunidade_etapa_historico"


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
            sa.Column("oehId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("oehEmpId", sa.Integer(), nullable=False),
            sa.Column("oehOpoId", sa.Integer(), nullable=False),
            sa.Column("oehEtkIdDe", sa.Integer(), nullable=True),
            sa.Column("oehEtkIdPara", sa.Integer(), nullable=True),
            sa.Column("oehData", sa.DateTime(timezone=True), nullable=False),
            sa.Column("oehOrigem", sa.String(length=20), nullable=False),
            sa.PrimaryKeyConstraint("oehId"),
        )
    existentes = _indices(bind)
    for nome, colunas in [
        ("ix_oportunidade_etapa_historico_oehEmpId", ["oehEmpId"]),
        ("ix_oportunidade_etapa_historico_oehOpoId", ["oehOpoId"]),
        ("ix_oportunidade_etapa_historico_oehEtkIdDe", ["oehEtkIdDe"]),
        ("ix_oportunidade_etapa_historico_oehEtkIdPara", ["oehEtkIdPara"]),
        ("ix_oeh_opo_data", ["oehOpoId", "oehData"]),
        ("ix_oeh_emp_data", ["oehEmpId", "oehData"]),
    ]:
        if nome not in existentes:
            op.create_index(nome, TABELA, colunas)
    fks = {tuple(fk["constrained_columns"]) for fk in inspect(bind).get_foreign_keys(TABELA)}
    for nome, colunas, ref, ref_cols, ondelete in [
        ("fk_oeh_oehEmpId", ["oehEmpId"], "empresa", ["empId"], "CASCADE"),
        ("fk_oeh_oehOpoId", ["oehOpoId"], "oportunidade", ["opoId"], "CASCADE"),
        ("fk_oeh_oehEtkIdDe", ["oehEtkIdDe"], "etapa_kanban", ["etkId"], "SET NULL"),
        ("fk_oeh_oehEtkIdPara", ["oehEtkIdPara"], "etapa_kanban", ["etkId"], "SET NULL"),
    ]:
        if tuple(colunas) not in fks:
            op.create_foreign_key(nome, TABELA, ref, colunas, ref_cols, ondelete=ondelete)


def downgrade() -> None:
    bind = op.get_bind()
    if TABELA in set(inspect(bind).get_table_names()):
        op.drop_table(TABELA)
