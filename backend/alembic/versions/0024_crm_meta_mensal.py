"""CRM: tabela meta mensal por empresa

Revision ID: 0024_crm_meta_mensal
Revises: 0023_ctr_drop_pdf_path
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0024_crm_meta_mensal"
down_revision: str | None = "0023_ctr_drop_pdf_path"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crm_meta_mensal",
        sa.Column("cmmId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cmmEmpId", sa.Integer(), nullable=False),
        sa.Column("cmmMesReferencia", sa.Date(), nullable=False),
        sa.Column("cmmQtdRecebimento", sa.Integer(), nullable=False),
        sa.Column("cmmTaxaConversao", sa.Numeric(10, 6), nullable=False),
        sa.Column("cmmMrrMedio", sa.Numeric(12, 2), nullable=False),
        sa.Column("cmmQtdFechamento", sa.Integer(), nullable=False),
        sa.Column("cmmMrrIncremental", sa.Numeric(14, 2), nullable=False),
        sa.Column("cmmDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cmmDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["cmmEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.UniqueConstraint("cmmEmpId", "cmmMesReferencia", name="uq_crm_meta_mensal_empresa_mes"),
    )
    op.create_index("ix_crm_meta_mensal_cmmEmpId", "crm_meta_mensal", ["cmmEmpId"])
    op.create_index("ix_crm_meta_mensal_cmmMesReferencia", "crm_meta_mensal", ["cmmMesReferencia"])


def downgrade() -> None:
    op.drop_index("ix_crm_meta_mensal_cmmMesReferencia", table_name="crm_meta_mensal")
    op.drop_index("ix_crm_meta_mensal_cmmEmpId", table_name="crm_meta_mensal")
    op.drop_table("crm_meta_mensal")
