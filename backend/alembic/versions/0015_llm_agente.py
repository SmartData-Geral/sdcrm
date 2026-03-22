"""tabela llm_agente para prompts e modelos configuraveis por empresa

Revision ID: 0015_llm_agente
Revises: 0014_reuniao_analise
Create Date: 2026-03-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0015_llm_agente"
down_revision: str | None = "0014_reuniao_analise"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_agente",
        sa.Column("agnId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agnEmpId", sa.Integer(), nullable=False),
        sa.Column("agnCodigo", sa.String(length=80), nullable=False),
        sa.Column("agnNome", sa.String(length=200), nullable=False),
        sa.Column("agnDescricao", sa.Text(), nullable=True),
        sa.Column("agnSystemPrompt", sa.Text(), nullable=False),
        sa.Column("agnLlmProvider", sa.String(length=40), nullable=False, server_default="openai"),
        sa.Column("agnLlmModel", sa.String(length=120), nullable=True),
        sa.Column("agnRespostaJsonEstruturada", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("agnAvisoEstrutura", sa.Text(), nullable=True),
        sa.Column("agnAtivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("agnDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("agnDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["agnEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.UniqueConstraint("agnEmpId", "agnCodigo", name="uq_llm_agente_emp_codigo"),
    )
    op.create_index("ix_llm_agente_agnEmpId", "llm_agente", ["agnEmpId"])


def downgrade() -> None:
    op.drop_index("ix_llm_agente_agnEmpId", table_name="llm_agente")
    op.drop_table("llm_agente")
