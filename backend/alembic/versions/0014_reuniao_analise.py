"""cria tabela de analise de reuniao comercial

Revision ID: 0014_reuniao_analise
Revises: 0013_template_snapshot_refactor
Create Date: 2026-03-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0014_reuniao_analise"
down_revision: str | None = "0013_template_snapshot_refactor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reuniao_analise",
        sa.Column("ranId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ranEmpId", sa.Integer(), nullable=False),
        sa.Column("ranOpoId", sa.Integer(), nullable=False),
        sa.Column("ranUsuId", sa.Integer(), nullable=True),
        sa.Column("ranTranscricao", sa.Text(), nullable=True),
        sa.Column("ranArquivosResumo", sa.JSON(), nullable=True),
        sa.Column("ranResumo", sa.Text(), nullable=True),
        sa.Column("ranFeedbackIa", sa.Text(), nullable=True),
        sa.Column("ranLeadScoreSugerido", sa.Integer(), nullable=True),
        sa.Column("ranTemperaturaSugerida", sa.String(length=20), nullable=True),
        sa.Column("ranDoresOportunidadesSugeridas", sa.Text(), nullable=True),
        sa.Column("ranObservacoesSugeridas", sa.Text(), nullable=True),
        sa.Column("ranProximosPassosSugeridos", sa.Text(), nullable=True),
        sa.Column("ranPromptUtilizado", sa.Text(), nullable=True),
        sa.Column("ranRespostaJson", sa.JSON(), nullable=True),
        sa.Column("ranModeloIa", sa.String(length=80), nullable=True),
        sa.Column("ranProcessadoEm", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ranStatus", sa.String(length=20), nullable=False, server_default="pendente"),
        sa.Column("ranAtivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ranDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ranDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ranEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ranOpoId"], ["oportunidade.opoId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ranUsuId"], ["usuario.usuId"], ondelete="SET NULL"),
    )
    op.create_index("ix_reuniao_analise_ranEmpId", "reuniao_analise", ["ranEmpId"])
    op.create_index("ix_reuniao_analise_ranOpoId", "reuniao_analise", ["ranOpoId"])
    op.create_index("ix_reuniao_analise_ranUsuId", "reuniao_analise", ["ranUsuId"])
    op.create_index("ix_reuniao_analise_ranStatus", "reuniao_analise", ["ranStatus"])


def downgrade() -> None:
    op.drop_index("ix_reuniao_analise_ranStatus", table_name="reuniao_analise")
    op.drop_index("ix_reuniao_analise_ranUsuId", table_name="reuniao_analise")
    op.drop_index("ix_reuniao_analise_ranOpoId", table_name="reuniao_analise")
    op.drop_index("ix_reuniao_analise_ranEmpId", table_name="reuniao_analise")
    op.drop_table("reuniao_analise")
