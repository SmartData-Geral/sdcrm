"""cria módulo de contratos

Revision ID: 0016_contratos_modulo
Revises: 0015_llm_agente
Create Date: 2026-03-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0016_contratos_modulo"
down_revision: str | None = "0015_llm_agente"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contrato_modelo",
        sa.Column("ctmId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ctmEmpId", sa.Integer(), nullable=False),
        sa.Column("ctmNome", sa.String(length=200), nullable=False),
        sa.Column("ctmDescricao", sa.Text(), nullable=True),
        sa.Column("ctmAtivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ctmDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ctmDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ctmEmpId"], ["empresa.empId"], ondelete="CASCADE"),
    )
    op.create_index("ix_contrato_modelo_ctmEmpId", "contrato_modelo", ["ctmEmpId"])

    op.create_table(
        "contrato_modelo_clausula",
        sa.Column("cmcId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cmcEmpId", sa.Integer(), nullable=False),
        sa.Column("cmcCtmId", sa.Integer(), nullable=False),
        sa.Column("cmcTitulo", sa.String(length=200), nullable=False),
        sa.Column("cmcTextoPadrao", sa.Text(), nullable=False),
        sa.Column("cmcUtilizarPadrao", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cmcOrdem", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("cmcAtivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("cmcDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cmcDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["cmcEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cmcCtmId"], ["contrato_modelo.ctmId"], ondelete="CASCADE"),
    )
    op.create_index("ix_contrato_modelo_clausula_cmcEmpId", "contrato_modelo_clausula", ["cmcEmpId"])
    op.create_index("ix_contrato_modelo_clausula_cmcCtmId", "contrato_modelo_clausula", ["cmcCtmId"])
    op.create_index("ix_contrato_modelo_clausula_cmcAtivo", "contrato_modelo_clausula", ["cmcAtivo"])
    op.create_index("ix_contrato_modelo_clausula_cmcOrdem", "contrato_modelo_clausula", ["cmcOrdem"])

    op.create_table(
        "contrato_modelo_clausula_variacao",
        sa.Column("cmvId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cmvEmpId", sa.Integer(), nullable=False),
        sa.Column("cmvCmcId", sa.Integer(), nullable=False),
        sa.Column("cmvNome", sa.String(length=200), nullable=True),
        sa.Column("cmvTitulo", sa.String(length=200), nullable=True),
        sa.Column("cmvTexto", sa.Text(), nullable=False),
        sa.Column("cmvAtivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("cmvDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cmvDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["cmvEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cmvCmcId"], ["contrato_modelo_clausula.cmcId"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_contrato_modelo_clausula_variacao_cmvEmpId", "contrato_modelo_clausula_variacao", ["cmvEmpId"]
    )
    op.create_index(
        "ix_contrato_modelo_clausula_variacao_cmvCmcId", "contrato_modelo_clausula_variacao", ["cmvCmcId"]
    )
    op.create_index(
        "ix_contrato_modelo_clausula_variacao_cmvAtivo", "contrato_modelo_clausula_variacao", ["cmvAtivo"]
    )

    op.create_table(
        "contrato",
        sa.Column("ctrId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ctrEmpId", sa.Integer(), nullable=False),
        sa.Column("ctrOpoId", sa.Integer(), nullable=True),
        sa.Column("ctrCtmId", sa.Integer(), nullable=False),
        sa.Column("ctrNome", sa.String(length=200), nullable=False),
        sa.Column("ctrStatus", sa.String(length=20), nullable=False, server_default="pronto"),
        sa.Column("ctrTokenPublico", sa.String(length=80), nullable=True),
        sa.Column("ctrRazaoSocial", sa.String(length=200), nullable=False),
        sa.Column("ctrCnpj", sa.String(length=20), nullable=False),
        sa.Column("ctrEndereco", sa.String(length=500), nullable=False),
        sa.Column("ctrResponsavelNome", sa.String(length=200), nullable=False),
        sa.Column("ctrResponsavelCpf", sa.String(length=20), nullable=False),
        sa.Column("ctrObjetoContrato", sa.Text(), nullable=False),
        sa.Column("ctrValorContrato", sa.Numeric(14, 2), nullable=False),
        sa.Column("ctrFormaPagamento", sa.String(length=200), nullable=False),
        sa.Column("ctrVigencia", sa.String(length=200), nullable=False),
        sa.Column("ctrDataInicio", sa.Date(), nullable=False),
        sa.Column("ctrForo", sa.String(length=200), nullable=False),
        sa.Column("ctrReajuste", sa.Text(), nullable=True),
        sa.Column("ctrHtmlSnapshot", sa.Text(), nullable=True),
        sa.Column("ctrPdfPath", sa.String(length=500), nullable=True),
        sa.Column("ctrAtivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ctrDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ctrDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ctrEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ctrOpoId"], ["oportunidade.opoId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ctrCtmId"], ["contrato_modelo.ctmId"], ondelete="CASCADE"),
        sa.UniqueConstraint("ctrOpoId", name="uq_contrato_ctrOpoId"),
        sa.UniqueConstraint("ctrTokenPublico", name="uq_contrato_token_publico"),
    )
    op.create_index("ix_contrato_ctrEmpId", "contrato", ["ctrEmpId"])
    op.create_index("ix_contrato_ctrOpoId", "contrato", ["ctrOpoId"])
    op.create_index("ix_contrato_ctrStatus", "contrato", ["ctrStatus"])
    op.create_index("ix_contrato_ctrCtmId", "contrato", ["ctrCtmId"])
    op.create_index("ix_contrato_ctrDataCriacao", "contrato", ["ctrDataCriacao"])

    op.create_table(
        "contrato_clausula",
        sa.Column("cclId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cclEmpId", sa.Integer(), nullable=False),
        sa.Column("cclCtrId", sa.Integer(), nullable=False),
        sa.Column("cclCmcId", sa.Integer(), nullable=False),
        sa.Column("cclCmvId", sa.Integer(), nullable=True),
        sa.Column("cclTitulo", sa.String(length=200), nullable=False),
        sa.Column("cclTexto", sa.Text(), nullable=False),
        sa.Column("cclUtilizar", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cclOrdemBase", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("cclOrdemFinal", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("cclAtivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("cclDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cclDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["cclEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cclCtrId"], ["contrato.ctrId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cclCmcId"], ["contrato_modelo_clausula.cmcId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cclCmvId"], ["contrato_modelo_clausula_variacao.cmvId"], ondelete="SET NULL"),
    )
    op.create_index("ix_contrato_clausula_cclEmpId", "contrato_clausula", ["cclEmpId"])
    op.create_index("ix_contrato_clausula_cclCtrId", "contrato_clausula", ["cclCtrId"])
    op.create_index("ix_contrato_clausula_cclCmcId", "contrato_clausula", ["cclCmcId"])
    op.create_index("ix_contrato_clausula_cclCmvId", "contrato_clausula", ["cclCmvId"])
    op.create_index("ix_contrato_clausula_cclOrdemBase", "contrato_clausula", ["cclOrdemBase"])
    op.create_index("ix_contrato_clausula_cclOrdemFinal", "contrato_clausula", ["cclOrdemFinal"])


def downgrade() -> None:
    op.drop_index("ix_contrato_clausula_cclOrdemFinal", table_name="contrato_clausula")
    op.drop_index("ix_contrato_clausula_cclOrdemBase", table_name="contrato_clausula")
    op.drop_index("ix_contrato_clausula_cclCmvId", table_name="contrato_clausula")
    op.drop_index("ix_contrato_clausula_cclCmcId", table_name="contrato_clausula")
    op.drop_index("ix_contrato_clausula_cclCtrId", table_name="contrato_clausula")
    op.drop_index("ix_contrato_clausula_cclEmpId", table_name="contrato_clausula")
    op.drop_table("contrato_clausula")

    op.drop_index("ix_contrato_ctrDataCriacao", table_name="contrato")
    op.drop_index("ix_contrato_ctrCtmId", table_name="contrato")
    op.drop_index("ix_contrato_ctrStatus", table_name="contrato")
    op.drop_index("ix_contrato_ctrOpoId", table_name="contrato")
    op.drop_index("ix_contrato_ctrEmpId", table_name="contrato")
    op.drop_table("contrato")

    op.drop_index(
        "ix_contrato_modelo_clausula_variacao_cmvAtivo", table_name="contrato_modelo_clausula_variacao"
    )
    op.drop_index(
        "ix_contrato_modelo_clausula_variacao_cmvCmcId", table_name="contrato_modelo_clausula_variacao"
    )
    op.drop_index(
        "ix_contrato_modelo_clausula_variacao_cmvEmpId", table_name="contrato_modelo_clausula_variacao"
    )
    op.drop_table("contrato_modelo_clausula_variacao")

    op.drop_index("ix_contrato_modelo_clausula_cmcOrdem", table_name="contrato_modelo_clausula")
    op.drop_index("ix_contrato_modelo_clausula_cmcAtivo", table_name="contrato_modelo_clausula")
    op.drop_index("ix_contrato_modelo_clausula_cmcCtmId", table_name="contrato_modelo_clausula")
    op.drop_index("ix_contrato_modelo_clausula_cmcEmpId", table_name="contrato_modelo_clausula")
    op.drop_table("contrato_modelo_clausula")

    op.drop_index("ix_contrato_modelo_ctmEmpId", table_name="contrato_modelo")
    op.drop_table("contrato_modelo")

