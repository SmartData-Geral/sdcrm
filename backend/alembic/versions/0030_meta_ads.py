"""Meta Ads: contas, origens, campanhas, insights diarios, log e vinculo na oportunidade

Revision ID: 0030_meta_ads
Revises: 0029_crm_meta_valor_projeto
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0030_meta_ads"
down_revision: str | None = "0029_crm_meta_valor_projeto"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTA = "meta_ads_conta"
ORIGEM = "meta_ads_conta_origem"
CAMPANHA = "meta_ads_campanha"
INSIGHT = "meta_ads_insight_diario"
LOG = "meta_ads_sync_log"


def _tabelas(bind) -> set[str]:
    return set(inspect(bind).get_table_names())


def _indices(bind, tabela) -> set[str]:
    try:
        return {i["name"] for i in inspect(bind).get_indexes(tabela)}
    except Exception:
        return set()


def _criar_indices(bind, tabela, indices) -> None:
    existentes = _indices(bind, tabela)
    for nome, colunas in indices:
        if nome not in existentes:
            op.create_index(nome, tabela, colunas)


def upgrade() -> None:
    bind = op.get_bind()

    if CONTA not in _tabelas(bind):
        op.create_table(
            CONTA,
            sa.Column("macId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("macEmpId", sa.Integer(), nullable=False),
            sa.Column("macNome", sa.String(length=150), nullable=False),
            sa.Column("macContaExterna", sa.String(length=40), nullable=False),
            sa.Column("macToken", sa.Text(), nullable=False),
            sa.Column("macTokenFinal", sa.String(length=4), nullable=False),
            sa.Column("macMoeda", sa.String(length=3), nullable=True),
            sa.Column("macFuso", sa.String(length=60), nullable=True),
            sa.Column("macStatus", sa.String(length=20), nullable=False, server_default="pendente"),
            sa.Column("macMensagem", sa.String(length=500), nullable=True),
            sa.Column("macUltimaSync", sa.DateTime(timezone=True), nullable=True),
            sa.Column("macSyncIniciadaEm", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "macCargaInicialFeita", sa.Boolean(), nullable=False, server_default=sa.text("0")
            ),
            sa.Column("macAtivo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("macDataCriacao", sa.DateTime(timezone=True), nullable=False),
            sa.Column("macDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("macId"),
            sa.ForeignKeyConstraint(["macEmpId"], ["empresa.empId"], ondelete="CASCADE"),
            sa.UniqueConstraint("macEmpId", "macContaExterna", name="uq_meta_ads_conta_emp_ext"),
        )
    _criar_indices(bind, CONTA, [("ix_meta_ads_conta_macEmpId", ["macEmpId"])])

    if ORIGEM not in _tabelas(bind):
        op.create_table(
            ORIGEM,
            sa.Column("mcoId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("mcoMacId", sa.Integer(), nullable=False),
            sa.Column("mcoCcoId", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("mcoId"),
            sa.ForeignKeyConstraint(["mcoMacId"], ["meta_ads_conta.macId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["mcoCcoId"], ["como_conheceu.ccoId"], ondelete="CASCADE"),
            sa.UniqueConstraint("mcoMacId", "mcoCcoId", name="uq_meta_ads_conta_origem"),
        )
    _criar_indices(
        bind,
        ORIGEM,
        [
            ("ix_meta_ads_conta_origem_mcoMacId", ["mcoMacId"]),
            ("ix_meta_ads_conta_origem_mcoCcoId", ["mcoCcoId"]),
        ],
    )

    if CAMPANHA not in _tabelas(bind):
        op.create_table(
            CAMPANHA,
            sa.Column("mcgId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("mcgEmpId", sa.Integer(), nullable=False),
            sa.Column("mcgMacId", sa.Integer(), nullable=False),
            sa.Column("mcgCampanhaExterna", sa.String(length=40), nullable=False),
            sa.Column("mcgNome", sa.String(length=400), nullable=False),
            sa.Column("mcgNomeNormalizado", sa.String(length=400), nullable=False),
            sa.Column("mcgObjetivo", sa.String(length=60), nullable=True),
            sa.Column("mcgStatus", sa.String(length=30), nullable=True),
            sa.Column("mcgDataCriacao", sa.DateTime(timezone=True), nullable=False),
            sa.Column("mcgDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("mcgId"),
            sa.ForeignKeyConstraint(["mcgEmpId"], ["empresa.empId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["mcgMacId"], ["meta_ads_conta.macId"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "mcgMacId", "mcgCampanhaExterna", name="uq_meta_ads_campanha_conta_ext"
            ),
        )
    _criar_indices(
        bind,
        CAMPANHA,
        [
            ("ix_meta_ads_campanha_mcgEmpId", ["mcgEmpId"]),
            ("ix_meta_ads_campanha_mcgMacId", ["mcgMacId"]),
            ("ix_meta_ads_campanha_emp_nome", ["mcgEmpId", "mcgNomeNormalizado"]),
        ],
    )

    if INSIGHT not in _tabelas(bind):
        op.create_table(
            INSIGHT,
            sa.Column("midId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("midEmpId", sa.Integer(), nullable=False),
            sa.Column("midMacId", sa.Integer(), nullable=False),
            sa.Column("midMcgId", sa.Integer(), nullable=False),
            sa.Column("midData", sa.Date(), nullable=False),
            sa.Column(
                "midInvestimento", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")
            ),
            sa.Column("midImpressoes", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("midCliques", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("midAlcance", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("midLeadsMeta", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.PrimaryKeyConstraint("midId"),
            sa.ForeignKeyConstraint(["midEmpId"], ["empresa.empId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["midMacId"], ["meta_ads_conta.macId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["midMcgId"], ["meta_ads_campanha.mcgId"], ondelete="CASCADE"),
            sa.UniqueConstraint("midMcgId", "midData", name="uq_meta_ads_insight_campanha_dia"),
        )
    _criar_indices(
        bind,
        INSIGHT,
        [
            ("ix_meta_ads_insight_emp_data", ["midEmpId", "midData"]),
            ("ix_meta_ads_insight_diario_midMacId", ["midMacId"]),
        ],
    )

    if LOG not in _tabelas(bind):
        op.create_table(
            LOG,
            sa.Column("mslId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("mslMacId", sa.Integer(), nullable=False),
            sa.Column("mslInicio", sa.Date(), nullable=False),
            sa.Column("mslFim", sa.Date(), nullable=False),
            sa.Column("mslOrigem", sa.String(length=20), nullable=False),
            sa.Column("mslStatus", sa.String(length=20), nullable=False),
            sa.Column("mslLinhas", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column(
                "mslLeadsVinculados", sa.Integer(), nullable=False, server_default=sa.text("0")
            ),
            sa.Column("mslErro", sa.String(length=500), nullable=True),
            sa.Column("mslDuracaoMs", sa.Integer(), nullable=True),
            sa.Column("mslDataExecucao", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("mslId"),
            sa.ForeignKeyConstraint(["mslMacId"], ["meta_ads_conta.macId"], ondelete="CASCADE"),
        )
    _criar_indices(
        bind,
        LOG,
        [
            ("ix_meta_ads_sync_log_mslMacId", ["mslMacId"]),
            ("ix_meta_ads_sync_log_mslDataExecucao", ["mslDataExecucao"]),
        ],
    )

    colunas = {c["name"] for c in inspect(bind).get_columns("oportunidade")}
    if "opoMcgId" not in colunas:
        op.add_column("oportunidade", sa.Column("opoMcgId", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_oportunidade_opoMcgId",
            "oportunidade",
            CAMPANHA,
            ["opoMcgId"],
            ["mcgId"],
            ondelete="SET NULL",
        )
    _criar_indices(bind, "oportunidade", [("ix_oportunidade_opoMcgId", ["opoMcgId"])])
    if "opoMcgManual" not in colunas:
        op.add_column(
            "oportunidade",
            sa.Column("opoMcgManual", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    colunas = {c["name"] for c in inspect(bind).get_columns("oportunidade")}
    if "opoMcgManual" in colunas:
        op.drop_column("oportunidade", "opoMcgManual")
    if "opoMcgId" in colunas:
        op.drop_constraint("fk_oportunidade_opoMcgId", "oportunidade", type_="foreignkey")
        if "ix_oportunidade_opoMcgId" in _indices(bind, "oportunidade"):
            op.drop_index("ix_oportunidade_opoMcgId", table_name="oportunidade")
        op.drop_column("oportunidade", "opoMcgId")
    for tabela in (LOG, INSIGHT, CAMPANHA, ORIGEM, CONTA):
        if tabela in _tabelas(bind):
            op.drop_table(tabela)
