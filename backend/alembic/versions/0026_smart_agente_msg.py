"""Tabela de mensagens do Smart Agente por oportunidade

Revision ID: 0026_smart_agente_msg
Revises: 0025_drop_opo_motivo_perda
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0026_smart_agente_msg"
down_revision: str | None = "0025_drop_opo_motivo_perda"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    table_name = "oportunidade_smart_agente_mensagem"
    if table_name not in insp.get_table_names():
        op.create_table(
            table_name,
            sa.Column("osmId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("osmEmpId", sa.Integer(), nullable=False),
            sa.Column("osmOpoId", sa.Integer(), nullable=False),
            sa.Column("osmUsuId", sa.Integer(), nullable=True),
            sa.Column("osmRole", sa.String(length=12), nullable=False),
            sa.Column("osmContent", sa.Text(), nullable=False),
            sa.Column("osmDataCriacao", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["osmEmpId"], ["empresa.empId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["osmOpoId"], ["oportunidade.opoId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["osmUsuId"], ["usuario.usuId"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("osmId"),
        )
    insp = inspect(bind)
    idx_names = {i["name"] for i in insp.get_indexes(table_name)}
    ix_opo_data = "ix_oportunidade_smart_agente_mensagem_osmOpoId_osmDataCriacao"
    ix_emp = "ix_oportunidade_smart_agente_mensagem_osmEmpId"
    if ix_opo_data not in idx_names:
        op.create_index(
            ix_opo_data,
            table_name,
            ["osmOpoId", "osmDataCriacao"],
            unique=False,
        )
    if ix_emp not in idx_names:
        op.create_index(
            ix_emp,
            table_name,
            ["osmEmpId"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    table_name = "oportunidade_smart_agente_mensagem"
    if table_name not in insp.get_table_names():
        return
    idx_names = {i["name"] for i in insp.get_indexes(table_name)}
    ix_emp = "ix_oportunidade_smart_agente_mensagem_osmEmpId"
    ix_opo_data = "ix_oportunidade_smart_agente_mensagem_osmOpoId_osmDataCriacao"
    if ix_emp in idx_names:
        op.drop_index(ix_emp, table_name=table_name)
    if ix_opo_data in idx_names:
        op.drop_index(ix_opo_data, table_name=table_name)
    op.drop_table(table_name)
