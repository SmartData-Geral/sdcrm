"""Webhooks de saida: assinaturas, outbox de eventos e fila de entregas

Revision ID: 0028_webhooks_saida
Revises: 0027_integracao_leads
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0028_webhooks_saida"
down_revision: str | None = "0027_integracao_leads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELA_ASSINATURA = "webhook_assinatura"
TABELA_EVENTO = "webhook_evento"
TABELA_ENTREGA = "webhook_entrega"


def _indices(insp, tabela):
    try:
        return {i["name"] for i in insp.get_indexes(tabela)}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    tabelas = set(inspect(bind).get_table_names())

    if TABELA_ASSINATURA not in tabelas:
        op.create_table(
            TABELA_ASSINATURA,
            sa.Column("whaId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("whaEmpId", sa.Integer(), nullable=False),
            sa.Column("whaNome", sa.String(length=120), nullable=False),
            sa.Column("whaUrl", sa.String(length=600), nullable=False),
            sa.Column("whaSegredo", sa.String(length=80), nullable=False),
            sa.Column("whaEventosJson", sa.JSON(), nullable=False),
            sa.Column("whaHeadersJson", sa.JSON(), nullable=True),
            sa.Column(
                "whaFalhasConsecutivas", sa.Integer(), nullable=False, server_default=sa.text("0")
            ),
            sa.Column("whaDesativadaEm", sa.DateTime(timezone=True), nullable=True),
            sa.Column("whaDesativadaMotivo", sa.String(length=300), nullable=True),
            sa.Column("whaUltimaEntregaEm", sa.DateTime(timezone=True), nullable=True),
            sa.Column("whaUltimoStatusHttp", sa.Integer(), nullable=True),
            sa.Column("whaAtivo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("whaDataCriacao", sa.DateTime(timezone=True), nullable=False),
            sa.Column("whaDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("whaId"),
            sa.ForeignKeyConstraint(["whaEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        )

    idx = _indices(inspect(bind), TABELA_ASSINATURA)
    if "ix_webhook_assinatura_whaEmpId" not in idx:
        op.create_index("ix_webhook_assinatura_whaEmpId", TABELA_ASSINATURA, ["whaEmpId"])

    if TABELA_EVENTO not in set(inspect(bind).get_table_names()):
        op.create_table(
            TABELA_EVENTO,
            sa.Column("wevId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("wevEmpId", sa.Integer(), nullable=False),
            sa.Column("wevTipo", sa.String(length=60), nullable=False),
            sa.Column("wevChaveIdempotencia", sa.String(length=120), nullable=True),
            sa.Column("wevOpoId", sa.Integer(), nullable=True),
            sa.Column("wevPayloadJson", sa.JSON(), nullable=False),
            sa.Column("wevOrigem", sa.String(length=20), nullable=False, server_default="ui"),
            sa.Column("wevStatus", sa.String(length=20), nullable=False, server_default="pendente"),
            sa.Column("wevProcessadoEm", sa.DateTime(timezone=True), nullable=True),
            sa.Column("wevAtivo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("wevDataCriacao", sa.DateTime(timezone=True), nullable=False),
            sa.Column("wevDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("wevId"),
            sa.ForeignKeyConstraint(["wevEmpId"], ["empresa.empId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["wevOpoId"], ["oportunidade.opoId"], ondelete="SET NULL"),
            sa.UniqueConstraint("wevEmpId", "wevChaveIdempotencia", name="uq_webhook_evento_idem"),
        )

    idx = _indices(inspect(bind), TABELA_EVENTO)
    for nome, colunas in (
        # O indice quente do fan-out: reivindicar os pendentes mais antigos primeiro.
        ("ix_webhook_evento_fila", ["wevStatus", "wevDataCriacao"]),
        ("ix_webhook_evento_wevEmpId", ["wevEmpId"]),
        ("ix_webhook_evento_wevTipo", ["wevTipo"]),
        ("ix_webhook_evento_wevOpoId", ["wevOpoId"]),
    ):
        if nome not in idx:
            op.create_index(nome, TABELA_EVENTO, colunas)

    if TABELA_ENTREGA not in set(inspect(bind).get_table_names()):
        op.create_table(
            TABELA_ENTREGA,
            sa.Column("wenId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("wenEmpId", sa.Integer(), nullable=False),
            sa.Column("wenWevId", sa.Integer(), nullable=False),
            sa.Column("wenWhaId", sa.Integer(), nullable=False),
            sa.Column("wenStatus", sa.String(length=20), nullable=False, server_default="pendente"),
            sa.Column("wenTentativas", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("wenProximaTentativaEm", sa.DateTime(timezone=True), nullable=True),
            sa.Column("wenUltimaTentativaEm", sa.DateTime(timezone=True), nullable=True),
            sa.Column("wenUltimoStatusHttp", sa.Integer(), nullable=True),
            sa.Column("wenUltimoErro", sa.String(length=500), nullable=True),
            sa.Column("wenRespostaTrecho", sa.String(length=2000), nullable=True),
            sa.Column("wenDuracaoMs", sa.Integer(), nullable=True),
            sa.Column("wenClaimedPor", sa.String(length=80), nullable=True),
            sa.Column("wenClaimedEm", sa.DateTime(timezone=True), nullable=True),
            sa.Column("wenHistoricoJson", sa.JSON(), nullable=True),
            sa.Column("wenDataEntrega", sa.DateTime(timezone=True), nullable=True),
            sa.Column("wenDataCriacao", sa.DateTime(timezone=True), nullable=False),
            sa.Column("wenDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("wenId"),
            sa.ForeignKeyConstraint(["wenEmpId"], ["empresa.empId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["wenWevId"], ["webhook_evento.wevId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["wenWhaId"], ["webhook_assinatura.whaId"], ondelete="CASCADE"
            ),
            # Impede fan-out duplicado do mesmo evento para a mesma assinatura.
            sa.UniqueConstraint(
                "wenWevId", "wenWhaId", name="uq_webhook_entrega_evento_assinatura"
            ),
        )

    idx = _indices(inspect(bind), TABELA_ENTREGA)
    for nome, colunas in (
        # Indice quente do dispatcher: pendentes cuja hora ja chegou.
        ("ix_webhook_entrega_fila", ["wenStatus", "wenProximaTentativaEm"]),
        ("ix_webhook_entrega_emp_data", ["wenEmpId", "wenDataCriacao"]),
        ("ix_webhook_entrega_wenWevId", ["wenWevId"]),
        ("ix_webhook_entrega_wenWhaId", ["wenWhaId"]),
    ):
        if nome not in idx:
            op.create_index(nome, TABELA_ENTREGA, colunas)


def downgrade() -> None:
    bind = op.get_bind()
    tabelas = set(inspect(bind).get_table_names())
    for tabela in (TABELA_ENTREGA, TABELA_EVENTO, TABELA_ASSINATURA):
        if tabela in tabelas:
            op.drop_table(tabela)
