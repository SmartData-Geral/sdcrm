"""Configuracao do monitoramento de campanhas Meta

Revision ID: 0034_monitor_config
Revises: 0033_rastreio_meta
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0034_monitor_config"
down_revision: str | None = "0033_rastreio_meta"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA = "meta_ads_monitor_config"


def _bool(nome: str) -> sa.Column:
    return sa.Column(nome, sa.Boolean(), nullable=False, server_default=sa.text("1"))


def upgrade() -> None:
    bind = op.get_bind()
    if TABELA in inspect(bind).get_table_names():
        return
    op.create_table(
        TABELA,
        sa.Column("mmcId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("mmcEmpId", sa.Integer(), nullable=False),
        sa.Column("mmcEtkMqlId", sa.Integer(), nullable=True),
        sa.Column("mmcEtkOportunidadeId", sa.Integer(), nullable=True),
        sa.Column("mmcCplFator", sa.Numeric(5, 2), nullable=False, server_default="1.50"),
        sa.Column("mmcGastoSemLead", sa.Numeric(14, 2), nullable=False, server_default="150.00"),
        sa.Column("mmcFrequenciaMax", sa.Numeric(5, 2), nullable=False, server_default="3.00"),
        sa.Column("mmcQuedaCtrPct", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("mmcHorasSemContato", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("mmcGastoMinRanking", sa.Numeric(14, 2), nullable=False, server_default="50.00"),
        sa.Column("mmcHoraResumo", sa.Integer(), nullable=False, server_default="8"),
        _bool("mmcAlertaCpl"),
        _bool("mmcAlertaGasto"),
        _bool("mmcAlertaFrequencia"),
        _bool("mmcAlertaCtr"),
        _bool("mmcAlertaParado"),
        _bool("mmcAlertaSemContato"),
        sa.Column("mmcSemContatoDesde", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mmcDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mmcDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["mmcEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mmcEtkMqlId"], ["etapa_kanban.etkId"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["mmcEtkOportunidadeId"], ["etapa_kanban.etkId"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("mmcEmpId", name="uq_meta_ads_monitor_config_emp"),
    )
    op.create_index("ix_meta_ads_monitor_config_mmcEtkMqlId", TABELA, ["mmcEtkMqlId"])
    op.create_index(
        "ix_meta_ads_monitor_config_mmcEtkOportunidadeId", TABELA, ["mmcEtkOportunidadeId"]
    )


def downgrade() -> None:
    bind = op.get_bind()
    if TABELA in inspect(bind).get_table_names():
        op.drop_table(TABELA)
