"""Meta Ads: conjuntos, anuncios, metricas diarias por anuncio e saude da conta

Revision ID: 0031_meta_ads_anuncios
Revises: 0030_meta_ads
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0031_meta_ads_anuncios"
down_revision: str | None = "0030_meta_ads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTA = "meta_ads_conta"
CAMPANHA = "meta_ads_campanha"
CONJUNTO = "meta_ads_conjunto"
ANUNCIO = "meta_ads_anuncio"
INSIGHT_ANUNCIO = "meta_ads_insight_anuncio_diario"


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

    colunas = {c["name"] for c in inspect(bind).get_columns(CONTA)}
    if "macAccountStatus" not in colunas:
        op.add_column(CONTA, sa.Column("macAccountStatus", sa.Integer(), nullable=True))
    if "macDisableReason" not in colunas:
        op.add_column(CONTA, sa.Column("macDisableReason", sa.Integer(), nullable=True))

    if CONJUNTO not in _tabelas(bind):
        op.create_table(
            CONJUNTO,
            sa.Column("mcjId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("mcjEmpId", sa.Integer(), nullable=False),
            sa.Column("mcjMacId", sa.Integer(), nullable=False),
            sa.Column("mcjMcgId", sa.Integer(), nullable=False),
            sa.Column("mcjConjuntoExterno", sa.String(length=40), nullable=False),
            sa.Column("mcjNome", sa.String(length=400), nullable=False),
            sa.Column("mcjStatus", sa.String(length=30), nullable=True),
            sa.Column("mcjDataCriacao", sa.DateTime(timezone=True), nullable=False),
            sa.Column("mcjDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("mcjId"),
            sa.UniqueConstraint(
                "mcjMacId", "mcjConjuntoExterno", name="uq_meta_ads_conjunto_conta_ext"
            ),
        )
    _criar_indices(
        bind,
        CONJUNTO,
        [
            ("ix_meta_ads_conjunto_mcjEmpId", ["mcjEmpId"]),
            ("ix_meta_ads_conjunto_mcjMacId", ["mcjMacId"]),
            ("ix_meta_ads_conjunto_mcjMcgId", ["mcjMcgId"]),
        ],
    )
    _criar_fks(
        bind,
        CONJUNTO,
        [
            ("fk_meta_ads_conjunto_mcjEmpId", ["mcjEmpId"], "empresa", ["empId"]),
            ("fk_meta_ads_conjunto_mcjMacId", ["mcjMacId"], CONTA, ["macId"]),
            ("fk_meta_ads_conjunto_mcjMcgId", ["mcjMcgId"], CAMPANHA, ["mcgId"]),
        ],
    )

    if ANUNCIO not in _tabelas(bind):
        op.create_table(
            ANUNCIO,
            sa.Column("manId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("manEmpId", sa.Integer(), nullable=False),
            sa.Column("manMacId", sa.Integer(), nullable=False),
            sa.Column("manMcgId", sa.Integer(), nullable=False),
            sa.Column("manMcjId", sa.Integer(), nullable=False),
            sa.Column("manAnuncioExterno", sa.String(length=40), nullable=False),
            sa.Column("manNome", sa.String(length=400), nullable=False),
            sa.Column("manStatus", sa.String(length=30), nullable=True),
            sa.Column("manMotivo", sa.String(length=300), nullable=True),
            sa.Column("manCriadoEmMeta", sa.Date(), nullable=True),
            sa.Column("manPrimeiroDia", sa.Date(), nullable=True),
            sa.Column("manDataCriacao", sa.DateTime(timezone=True), nullable=False),
            sa.Column("manDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("manId"),
            sa.UniqueConstraint(
                "manMacId", "manAnuncioExterno", name="uq_meta_ads_anuncio_conta_ext"
            ),
        )
    _criar_indices(
        bind,
        ANUNCIO,
        [
            ("ix_meta_ads_anuncio_manMacId", ["manMacId"]),
            ("ix_meta_ads_anuncio_manMcgId", ["manMcgId"]),
            ("ix_meta_ads_anuncio_manMcjId", ["manMcjId"]),
            ("ix_meta_ads_anuncio_emp_ext", ["manEmpId", "manAnuncioExterno"]),
        ],
    )
    _criar_fks(
        bind,
        ANUNCIO,
        [
            ("fk_meta_ads_anuncio_manEmpId", ["manEmpId"], "empresa", ["empId"]),
            ("fk_meta_ads_anuncio_manMacId", ["manMacId"], CONTA, ["macId"]),
            ("fk_meta_ads_anuncio_manMcgId", ["manMcgId"], CAMPANHA, ["mcgId"]),
            ("fk_meta_ads_anuncio_manMcjId", ["manMcjId"], CONJUNTO, ["mcjId"]),
        ],
    )

    if INSIGHT_ANUNCIO not in _tabelas(bind):
        op.create_table(
            INSIGHT_ANUNCIO,
            sa.Column("miaId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("miaEmpId", sa.Integer(), nullable=False),
            sa.Column("miaMacId", sa.Integer(), nullable=False),
            sa.Column("miaManId", sa.Integer(), nullable=False),
            sa.Column("miaData", sa.Date(), nullable=False),
            sa.Column(
                "miaInvestimento", sa.Numeric(14, 2), nullable=False, server_default=sa.text("0")
            ),
            sa.Column("miaImpressoes", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("miaAlcance", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("miaCliques", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("miaCliquesLink", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("miaLeadsMeta", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.PrimaryKeyConstraint("miaId"),
            sa.UniqueConstraint("miaManId", "miaData", name="uq_meta_ads_insight_anuncio_dia"),
        )
    _criar_indices(
        bind,
        INSIGHT_ANUNCIO,
        [
            ("ix_meta_ads_insight_anuncio_emp_data", ["miaEmpId", "miaData"]),
            ("ix_meta_ads_insight_anuncio_diario_miaMacId", ["miaMacId"]),
        ],
    )
    _criar_fks(
        bind,
        INSIGHT_ANUNCIO,
        [
            ("fk_meta_ads_insight_anuncio_miaEmpId", ["miaEmpId"], "empresa", ["empId"]),
            ("fk_meta_ads_insight_anuncio_miaMacId", ["miaMacId"], CONTA, ["macId"]),
            ("fk_meta_ads_insight_anuncio_miaManId", ["miaManId"], ANUNCIO, ["manId"]),
        ],
    )


def _criar_fks(bind, tabela, fks) -> None:
    """FKs criadas depois dos indices (o indice da FK ja existe) e so se ainda faltarem."""
    existentes = {
        tuple(fk["constrained_columns"]) for fk in inspect(bind).get_foreign_keys(tabela)
    }
    for nome, colunas, ref_tabela, ref_colunas in fks:
        if tuple(colunas) in existentes:
            continue
        op.create_foreign_key(
            nome, tabela, ref_tabela, colunas, ref_colunas, ondelete="CASCADE"
        )


def downgrade() -> None:
    bind = op.get_bind()
    for tabela in (INSIGHT_ANUNCIO, ANUNCIO, CONJUNTO):
        if tabela in _tabelas(bind):
            op.drop_table(tabela)
    colunas = {c["name"] for c in inspect(bind).get_columns(CONTA)}
    if "macDisableReason" in colunas:
        op.drop_column(CONTA, "macDisableReason")
    if "macAccountStatus" in colunas:
        op.drop_column(CONTA, "macAccountStatus")
