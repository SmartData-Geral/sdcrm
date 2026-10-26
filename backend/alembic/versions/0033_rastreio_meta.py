"""Ids da Meta no lead, vinculo por anuncio e exigencia de rastreio na conta

Revision ID: 0033_rastreio_meta
Revises: 0032_etapa_historico
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0033_rastreio_meta"
down_revision: str | None = "0032_etapa_historico"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OPO = "oportunidade"
CONTA = "meta_ads_conta"


def _colunas(bind, tabela) -> set[str]:
    return {c["name"] for c in inspect(bind).get_columns(tabela)}


def _indices(bind, tabela) -> set[str]:
    return {i["name"] for i in inspect(bind).get_indexes(tabela)}


def upgrade() -> None:
    bind = op.get_bind()
    existentes = _colunas(bind, OPO)
    for nome in ("opoMetaLeadId", "opoMetaCampanhaId", "opoMetaConjuntoId", "opoMetaAnuncioId"):
        if nome not in existentes:
            op.add_column(OPO, sa.Column(nome, sa.String(length=40), nullable=True))
    if "opoManId" not in existentes:
        op.add_column(OPO, sa.Column("opoManId", sa.Integer(), nullable=True))

    indices = _indices(bind, OPO)
    # O indice da FK vem antes dela (MySQL exige indice na coluna da FK).
    for nome, colunas in [
        ("ix_oportunidade_opoMetaAnuncioId", ["opoMetaAnuncioId"]),
        ("ix_oportunidade_opoManId", ["opoManId"]),
    ]:
        if nome not in indices:
            op.create_index(nome, OPO, colunas)

    fks = {tuple(fk["constrained_columns"]) for fk in inspect(bind).get_foreign_keys(OPO)}
    if ("opoManId",) not in fks:
        op.create_foreign_key(
            "fk_oportunidade_opoManId",
            OPO,
            "meta_ads_anuncio",
            ["opoManId"],
            ["manId"],
            ondelete="SET NULL",
        )

    if "macExigirRastreio" not in _colunas(bind, CONTA):
        op.add_column(
            CONTA,
            sa.Column(
                "macExigirRastreio", sa.Boolean(), nullable=False, server_default=sa.text("0")
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "macExigirRastreio" in _colunas(bind, CONTA):
        op.drop_column(CONTA, "macExigirRastreio")
    fks = {fk["name"] for fk in inspect(bind).get_foreign_keys(OPO)}
    if "fk_oportunidade_opoManId" in fks:
        op.drop_constraint("fk_oportunidade_opoManId", OPO, type_="foreignkey")
    indices = _indices(bind, OPO)
    for nome in ("ix_oportunidade_opoManId", "ix_oportunidade_opoMetaAnuncioId"):
        if nome in indices:
            op.drop_index(nome, table_name=OPO)
    existentes = _colunas(bind, OPO)
    for nome in (
        "opoManId",
        "opoMetaAnuncioId",
        "opoMetaConjuntoId",
        "opoMetaCampanhaId",
        "opoMetaLeadId",
    ):
        if nome in existentes:
            op.drop_column(OPO, nome)
