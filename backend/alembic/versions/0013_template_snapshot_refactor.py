"""refatora templates para snapshot de proposta

Revision ID: 0013_template_snapshot_refactor
Revises: 0012_empresa_logo
Create Date: 2026-03-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0013_template_snapshot_refactor"
down_revision: str | None = "0012_empresa_logo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("proposta_template", sa.Column("ptlPrpOrigemId", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_proposta_template_ptlPrpOrigemId",
        "proposta_template",
        "proposta",
        ["ptlPrpOrigemId"],
        ["prpId"],
        ondelete="SET NULL",
    )
    op.create_index("ix_proposta_template_ptlPrpOrigemId", "proposta_template", ["ptlPrpOrigemId"])

    op.create_table(
        "template_bloco",
        sa.Column("tblId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tblEmpId", sa.Integer(), nullable=False),
        sa.Column("tblPtlId", sa.Integer(), nullable=False),
        sa.Column("tblTipo", sa.String(length=60), nullable=False),
        sa.Column("tblTitulo", sa.String(length=200), nullable=True),
        sa.Column("tblSubtitulo", sa.String(length=300), nullable=True),
        sa.Column("tblOrdem", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("tblVisivel", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("tblDadosJson", sa.JSON(), nullable=True),
        sa.Column("tblAtivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("tblDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tblDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tblEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tblPtlId"], ["proposta_template.ptlId"], ondelete="CASCADE"),
    )
    op.create_index("ix_template_bloco_tblEmpId", "template_bloco", ["tblEmpId"])
    op.create_index("ix_template_bloco_tblPtlId", "template_bloco", ["tblPtlId"])
    op.create_index("ix_template_bloco_tblTipo", "template_bloco", ["tblTipo"])
    op.create_index("ix_template_bloco_tblOrdem", "template_bloco", ["tblOrdem"])


def downgrade() -> None:
    op.drop_index("ix_template_bloco_tblOrdem", table_name="template_bloco")
    op.drop_index("ix_template_bloco_tblTipo", table_name="template_bloco")
    op.drop_index("ix_template_bloco_tblPtlId", table_name="template_bloco")
    op.drop_index("ix_template_bloco_tblEmpId", table_name="template_bloco")
    op.drop_table("template_bloco")

    op.drop_index("ix_proposta_template_ptlPrpOrigemId", table_name="proposta_template")
    op.drop_constraint("fk_proposta_template_ptlPrpOrigemId", "proposta_template", type_="foreignkey")
    op.drop_column("proposta_template", "ptlPrpOrigemId")
