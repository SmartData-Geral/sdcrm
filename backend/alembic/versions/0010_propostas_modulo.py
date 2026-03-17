"""add modulo de propostas integrado ao CRM

Revision ID: 0010_propostas_modulo
Revises: 0009_como_conheceu_grupo
Create Date: 2026-03-15
"""

from collections.abc import Sequence
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "0010_propostas_modulo"
down_revision: str | None = "0009_como_conheceu_grupo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    usuario_columns = {column["name"] for column in inspector.get_columns("usuario")}
    if "usuWhatsapp" not in usuario_columns:
        op.add_column("usuario", sa.Column("usuWhatsapp", sa.String(length=50), nullable=True))

    op.create_table(
        "proposta_template",
        sa.Column("ptlId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ptlEmpId", sa.Integer(), nullable=False),
        sa.Column("ptlNome", sa.String(length=200), nullable=False),
        sa.Column("ptlTipoSolucao", sa.String(length=120), nullable=True),
        sa.Column("ptlTipoProposta", sa.String(length=20), nullable=False),
        sa.Column("ptlPadrao", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ptlSchemaJson", sa.JSON(), nullable=True),
        sa.Column("ptlConfigJson", sa.JSON(), nullable=True),
        sa.Column("ptlAtivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ptlDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ptlDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ptlEmpId"], ["empresa.empId"], ondelete="CASCADE"),
    )
    op.create_index("ix_proposta_template_ptlEmpId", "proposta_template", ["ptlEmpId"])
    op.create_index("ix_proposta_template_ptlTipoSolucao", "proposta_template", ["ptlTipoSolucao"])
    op.create_index("ix_proposta_template_ptlTipoProposta", "proposta_template", ["ptlTipoProposta"])

    op.create_table(
        "proposta",
        sa.Column("prpId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("prpEmpId", sa.Integer(), nullable=False),
        sa.Column("prpOpoId", sa.Integer(), nullable=False),
        sa.Column("prpTplId", sa.Integer(), nullable=True),
        sa.Column("prpTitulo", sa.String(length=300), nullable=False),
        sa.Column("prpTipo", sa.String(length=20), nullable=False),
        sa.Column("prpStatus", sa.String(length=20), nullable=False, server_default="rascunho"),
        sa.Column("prpTokenPublico", sa.String(length=80), nullable=False),
        sa.Column("prpVersaoAtual", sa.Integer(), nullable=True),
        sa.Column("prpUsuCriadorId", sa.Integer(), nullable=True),
        sa.Column("prpUsuEditorId", sa.Integer(), nullable=True),
        sa.Column("prpUsuResponsavelId", sa.Integer(), nullable=True),
        sa.Column("prpNomeContato", sa.String(length=200), nullable=True),
        sa.Column("prpEmailContato", sa.String(length=255), nullable=True),
        sa.Column("prpWhatsappContato", sa.String(length=50), nullable=True),
        sa.Column("prpObservacaoInterna", sa.Text(), nullable=True),
        sa.Column("prpJsonConfiguracao", sa.JSON(), nullable=True),
        sa.Column("prpHtmlRenderizado", sa.Text(), nullable=True),
        sa.Column("prpPublicadaEm", sa.DateTime(timezone=True), nullable=True),
        sa.Column("prpAceitaEm", sa.DateTime(timezone=True), nullable=True),
        sa.Column("prpAtivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("prpDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prpDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["prpEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prpOpoId"], ["oportunidade.opoId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prpTplId"], ["proposta_template.ptlId"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["prpUsuCriadorId"], ["usuario.usuId"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["prpUsuEditorId"], ["usuario.usuId"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["prpUsuResponsavelId"], ["usuario.usuId"], ondelete="SET NULL"),
    )
    op.create_index("ix_proposta_prpEmpId", "proposta", ["prpEmpId"])
    op.create_index("ix_proposta_prpOpoId", "proposta", ["prpOpoId"])
    op.create_index("ix_proposta_prpTipo", "proposta", ["prpTipo"])
    op.create_index("ix_proposta_prpStatus", "proposta", ["prpStatus"])
    op.create_index("ix_proposta_prpTokenPublico", "proposta", ["prpTokenPublico"], unique=True)
    op.create_index("ix_proposta_prpUsuResponsavelId", "proposta", ["prpUsuResponsavelId"])
    op.create_index("ix_proposta_prpDataCriacao", "proposta", ["prpDataCriacao"])

    op.create_table(
        "proposta_versao",
        sa.Column("prvId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("prvEmpId", sa.Integer(), nullable=False),
        sa.Column("prvPrpId", sa.Integer(), nullable=False),
        sa.Column("prvNumero", sa.Integer(), nullable=False),
        sa.Column("prvTitulo", sa.Text(), nullable=True),
        sa.Column("prvJsonSnapshot", sa.JSON(), nullable=True),
        sa.Column("prvHtmlSnapshot", sa.Text(), nullable=True),
        sa.Column("prvPublicada", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("prvUsuId", sa.Integer(), nullable=True),
        sa.Column("prvDataPublicacao", sa.DateTime(timezone=True), nullable=True),
        sa.Column("prvAtivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("prvDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prvDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["prvEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prvPrpId"], ["proposta.prpId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prvUsuId"], ["usuario.usuId"], ondelete="SET NULL"),
        sa.UniqueConstraint("prvPrpId", "prvNumero", name="uq_proposta_versao_prp_numero"),
    )
    op.create_index("ix_proposta_versao_prvEmpId", "proposta_versao", ["prvEmpId"])
    op.create_index("ix_proposta_versao_prvPrpId", "proposta_versao", ["prvPrpId"])
    op.create_index("ix_proposta_versao_prvPublicada", "proposta_versao", ["prvPublicada"])
    op.create_index("ix_proposta_versao_prvDataCriacao", "proposta_versao", ["prvDataCriacao"])

    op.create_table(
        "proposta_bloco",
        sa.Column("pblId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pblEmpId", sa.Integer(), nullable=False),
        sa.Column("pblPrpId", sa.Integer(), nullable=False),
        sa.Column("pblTipo", sa.String(length=60), nullable=False),
        sa.Column("pblTitulo", sa.String(length=200), nullable=True),
        sa.Column("pblSubtitulo", sa.String(length=300), nullable=True),
        sa.Column("pblOrdem", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("pblVisivel", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("pblDadosJson", sa.JSON(), nullable=True),
        sa.Column("pblAtivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("pblDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pblDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pblEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pblPrpId"], ["proposta.prpId"], ondelete="CASCADE"),
    )
    op.create_index("ix_proposta_bloco_pblEmpId", "proposta_bloco", ["pblEmpId"])
    op.create_index("ix_proposta_bloco_pblPrpId", "proposta_bloco", ["pblPrpId"])
    op.create_index("ix_proposta_bloco_pblTipo", "proposta_bloco", ["pblTipo"])
    op.create_index("ix_proposta_bloco_pblOrdem", "proposta_bloco", ["pblOrdem"])

    op.create_table(
        "proposta_evento",
        sa.Column("pevId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pevEmpId", sa.Integer(), nullable=False),
        sa.Column("pevPrpId", sa.Integer(), nullable=False),
        sa.Column("pevPrvId", sa.Integer(), nullable=True),
        sa.Column("pevTipo", sa.String(length=40), nullable=False),
        sa.Column("pevIp", sa.String(length=64), nullable=True),
        sa.Column("pevUserAgent", sa.String(length=600), nullable=True),
        sa.Column("pevDadosJson", sa.JSON(), nullable=True),
        sa.Column("pevDataEvento", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pevAtivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("pevDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pevDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pevEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pevPrpId"], ["proposta.prpId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pevPrvId"], ["proposta_versao.prvId"], ondelete="SET NULL"),
    )
    op.create_index("ix_proposta_evento_pevEmpId", "proposta_evento", ["pevEmpId"])
    op.create_index("ix_proposta_evento_pevPrpId", "proposta_evento", ["pevPrpId"])
    op.create_index("ix_proposta_evento_pevPrvId", "proposta_evento", ["pevPrvId"])
    op.create_index("ix_proposta_evento_pevTipo", "proposta_evento", ["pevTipo"])
    op.create_index("ix_proposta_evento_pevDataEvento", "proposta_evento", ["pevDataEvento"])

    empresa_tbl = sa.table("empresa", sa.column("empId", sa.Integer()))
    template_tbl = sa.table(
        "proposta_template",
        sa.column("ptlEmpId", sa.Integer()),
        sa.column("ptlNome", sa.String()),
        sa.column("ptlTipoSolucao", sa.String()),
        sa.column("ptlTipoProposta", sa.String()),
        sa.column("ptlPadrao", sa.Boolean()),
        sa.column("ptlSchemaJson", sa.JSON()),
        sa.column("ptlConfigJson", sa.JSON()),
        sa.column("ptlAtivo", sa.Boolean()),
        sa.column("ptlDataCriacao", sa.DateTime(timezone=True)),
        sa.column("ptlDataAtualizacao", sa.DateTime(timezone=True)),
    )
    emp_ids = [row.empId for row in bind.execute(sa.select(empresa_tbl.c.empId))]
    now = datetime.utcnow()
    rows: list[dict] = []
    for emp_id in emp_ids:
        rows.extend(
            [
                {
                    "ptlEmpId": emp_id,
                    "ptlNome": "Template Projeto Smart Data",
                    "ptlTipoSolucao": "geral",
                    "ptlTipoProposta": "projeto",
                    "ptlPadrao": True,
                    "ptlSchemaJson": {"versao": 1, "modo": "projeto"},
                    "ptlConfigJson": {"blocos": ["hero", "apresentacao", "metodologia", "escopo_inicial", "valores_projeto", "clientes", "cta_final"]},
                    "ptlAtivo": True,
                    "ptlDataCriacao": now,
                    "ptlDataAtualizacao": now,
                },
                {
                    "ptlEmpId": emp_id,
                    "ptlNome": "Template Planos Smart Data",
                    "ptlTipoSolucao": "geral",
                    "ptlTipoProposta": "planos",
                    "ptlPadrao": True,
                    "ptlSchemaJson": {"versao": 1, "modo": "planos"},
                    "ptlConfigJson": {"blocos": ["hero", "apresentacao", "metodologia", "escopo_inicial", "valores_planos", "clientes", "cta_final"]},
                    "ptlAtivo": True,
                    "ptlDataCriacao": now,
                    "ptlDataAtualizacao": now,
                },
                {
                    "ptlEmpId": emp_id,
                    "ptlNome": "Template Híbrido Smart Data",
                    "ptlTipoSolucao": "geral",
                    "ptlTipoProposta": "hibrida",
                    "ptlPadrao": True,
                    "ptlSchemaJson": {"versao": 1, "modo": "hibrida"},
                    "ptlConfigJson": {"blocos": ["hero", "apresentacao", "metodologia", "escopo_inicial", "valores_projeto", "valores_planos", "clientes", "cta_final"]},
                    "ptlAtivo": True,
                    "ptlDataCriacao": now,
                    "ptlDataAtualizacao": now,
                },
            ]
        )
    if rows:
        bind.execute(template_tbl.insert(), rows)


def downgrade() -> None:
    op.drop_index("ix_proposta_evento_pevDataEvento", table_name="proposta_evento")
    op.drop_index("ix_proposta_evento_pevTipo", table_name="proposta_evento")
    op.drop_index("ix_proposta_evento_pevPrvId", table_name="proposta_evento")
    op.drop_index("ix_proposta_evento_pevPrpId", table_name="proposta_evento")
    op.drop_index("ix_proposta_evento_pevEmpId", table_name="proposta_evento")
    op.drop_table("proposta_evento")

    op.drop_index("ix_proposta_bloco_pblOrdem", table_name="proposta_bloco")
    op.drop_index("ix_proposta_bloco_pblTipo", table_name="proposta_bloco")
    op.drop_index("ix_proposta_bloco_pblPrpId", table_name="proposta_bloco")
    op.drop_index("ix_proposta_bloco_pblEmpId", table_name="proposta_bloco")
    op.drop_table("proposta_bloco")

    op.drop_index("ix_proposta_versao_prvDataCriacao", table_name="proposta_versao")
    op.drop_index("ix_proposta_versao_prvPublicada", table_name="proposta_versao")
    op.drop_index("ix_proposta_versao_prvPrpId", table_name="proposta_versao")
    op.drop_index("ix_proposta_versao_prvEmpId", table_name="proposta_versao")
    op.drop_table("proposta_versao")

    op.drop_index("ix_proposta_prpDataCriacao", table_name="proposta")
    op.drop_index("ix_proposta_prpUsuResponsavelId", table_name="proposta")
    op.drop_index("ix_proposta_prpTokenPublico", table_name="proposta")
    op.drop_index("ix_proposta_prpStatus", table_name="proposta")
    op.drop_index("ix_proposta_prpTipo", table_name="proposta")
    op.drop_index("ix_proposta_prpOpoId", table_name="proposta")
    op.drop_index("ix_proposta_prpEmpId", table_name="proposta")
    op.drop_table("proposta")

    op.drop_index("ix_proposta_template_ptlTipoProposta", table_name="proposta_template")
    op.drop_index("ix_proposta_template_ptlTipoSolucao", table_name="proposta_template")
    op.drop_index("ix_proposta_template_ptlEmpId", table_name="proposta_template")
    op.drop_table("proposta_template")

    bind = op.get_bind()
    inspector = inspect(bind)
    usuario_columns = {column["name"] for column in inspector.get_columns("usuario")}
    if "usuWhatsapp" in usuario_columns:
        op.drop_column("usuario", "usuWhatsapp")

