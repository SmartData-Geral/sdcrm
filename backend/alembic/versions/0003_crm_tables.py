"""crm tables: como_conheceu, motivo_cancelamento, produto, etapa_kanban, oportunidade, oportunidade_historico

Revision ID: 0003_crm
Revises: 0002_seed_initial_data
Create Date: 2026-03-09

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_crm"
down_revision: str | None = "0002_seed_initial_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "como_conheceu",
        sa.Column("ccoId", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ccoEmpId", sa.Integer, nullable=False),
        sa.Column("ccoNome", sa.String(length=200), nullable=False),
        sa.Column("ccoAtivo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("ccoDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ccoDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ccoEmpId"], ["empresa.empId"], ondelete="CASCADE"),
    )
    op.create_index("ix_como_conheceu_ccoEmpId", "como_conheceu", ["ccoEmpId"])

    op.create_table(
        "motivo_cancelamento",
        sa.Column("mcaId", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("mcaEmpId", sa.Integer, nullable=False),
        sa.Column("mcaNome", sa.String(length=200), nullable=False),
        sa.Column("mcaAtivo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("mcaDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mcaDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["mcaEmpId"], ["empresa.empId"], ondelete="CASCADE"),
    )
    op.create_index("ix_motivo_cancelamento_mcaEmpId", "motivo_cancelamento", ["mcaEmpId"])

    op.create_table(
        "produto",
        sa.Column("proId", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("proEmpId", sa.Integer, nullable=False),
        sa.Column("proNome", sa.String(length=200), nullable=False),
        sa.Column("proAtivo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("proDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("proDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["proEmpId"], ["empresa.empId"], ondelete="CASCADE"),
    )
    op.create_index("ix_produto_proEmpId", "produto", ["proEmpId"])

    op.create_table(
        "etapa_kanban",
        sa.Column("etkId", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("etkEmpId", sa.Integer, nullable=False),
        sa.Column("etkNome", sa.String(length=100), nullable=False),
        sa.Column("etkOrdem", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("etkPipeline", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("etkCor", sa.String(length=20), nullable=True),
        sa.Column("etkAtivo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("etkDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("etkDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["etkEmpId"], ["empresa.empId"], ondelete="CASCADE"),
    )
    op.create_index("ix_etapa_kanban_etkEmpId", "etapa_kanban", ["etkEmpId"])
    op.create_index("ix_etapa_kanban_etkOrdem", "etapa_kanban", ["etkOrdem"])

    op.create_table(
        "oportunidade",
        sa.Column("opoId", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("opoEmpId", sa.Integer, nullable=False),
        sa.Column("opoTitulo", sa.String(length=300), nullable=False),
        sa.Column("opoNomeContato", sa.String(length=200), nullable=True),
        sa.Column("opoEmpresaContato", sa.String(length=200), nullable=True),
        sa.Column("opoEmail", sa.String(length=255), nullable=True),
        sa.Column("opoTelefone", sa.String(length=50), nullable=True),
        sa.Column("opoSolucao", sa.String(length=500), nullable=True),
        sa.Column("opoProId", sa.Integer, nullable=True),
        sa.Column("opoEtkId", sa.Integer, nullable=True),
        sa.Column("opoUsuResponsavelId", sa.Integer, nullable=True),
        sa.Column("opoCcoId", sa.Integer, nullable=True),
        sa.Column("opoMcaId", sa.Integer, nullable=True),
        sa.Column("opoLeadScore", sa.Integer, nullable=True),
        sa.Column("opoTemperatura", sa.String(length=20), nullable=True),
        sa.Column("opoReuniaoConfirmada", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("opoPropostaEnviada", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("opoDataRecebimento", sa.Date(), nullable=True),
        sa.Column("opoDataUltimoContato", sa.Date(), nullable=True),
        sa.Column("opoDataFechamento", sa.Date(), nullable=True),
        sa.Column("opoStatusFechamento", sa.String(length=20), nullable=True),
        sa.Column("opoDoresMotivadores", sa.Text(), nullable=True),
        sa.Column("opoComentarios", sa.Text(), nullable=True),
        sa.Column("opoAtivo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("opoDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("opoDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["opoEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opoProId"], ["produto.proId"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opoEtkId"], ["etapa_kanban.etkId"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opoUsuResponsavelId"], ["usuario.usuId"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opoCcoId"], ["como_conheceu.ccoId"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opoMcaId"], ["motivo_cancelamento.mcaId"], ondelete="SET NULL"),
    )
    op.create_index("ix_oportunidade_opoEmpId", "oportunidade", ["opoEmpId"])
    op.create_index("ix_oportunidade_opoEtkId", "oportunidade", ["opoEtkId"])
    op.create_index("ix_oportunidade_opoUsuResponsavelId", "oportunidade", ["opoUsuResponsavelId"])
    op.create_index("ix_oportunidade_opoAtivo", "oportunidade", ["opoAtivo"])
    op.create_index("ix_oportunidade_opoDataUltimoContato", "oportunidade", ["opoDataUltimoContato"])
    op.create_index("ix_oportunidade_opoStatusFechamento", "oportunidade", ["opoStatusFechamento"])

    op.create_table(
        "oportunidade_historico",
        sa.Column("ophId", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ophEmpId", sa.Integer, nullable=False),
        sa.Column("ophOpoId", sa.Integer, nullable=False),
        sa.Column("ophUsuId", sa.Integer, nullable=True),
        sa.Column("ophDataRegistro", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ophConteudo", sa.Text(), nullable=True),
        sa.Column("ophAtivo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("ophDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ophDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ophEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ophOpoId"], ["oportunidade.opoId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ophUsuId"], ["usuario.usuId"], ondelete="SET NULL"),
    )
    op.create_index("ix_oportunidade_historico_ophEmpId", "oportunidade_historico", ["ophEmpId"])
    op.create_index("ix_oportunidade_historico_ophOpoId", "oportunidade_historico", ["ophOpoId"])
    op.create_index("ix_oportunidade_historico_ophUsuId", "oportunidade_historico", ["ophUsuId"])


def downgrade() -> None:
    op.drop_index("ix_oportunidade_historico_ophUsuId", table_name="oportunidade_historico")
    op.drop_index("ix_oportunidade_historico_ophOpoId", table_name="oportunidade_historico")
    op.drop_index("ix_oportunidade_historico_ophEmpId", table_name="oportunidade_historico")
    op.drop_table("oportunidade_historico")

    op.drop_index("ix_oportunidade_opoStatusFechamento", table_name="oportunidade")
    op.drop_index("ix_oportunidade_opoDataUltimoContato", table_name="oportunidade")
    op.drop_index("ix_oportunidade_opoAtivo", table_name="oportunidade")
    op.drop_index("ix_oportunidade_opoUsuResponsavelId", table_name="oportunidade")
    op.drop_index("ix_oportunidade_opoEtkId", table_name="oportunidade")
    op.drop_index("ix_oportunidade_opoEmpId", table_name="oportunidade")
    op.drop_table("oportunidade")

    op.drop_index("ix_etapa_kanban_etkOrdem", table_name="etapa_kanban")
    op.drop_index("ix_etapa_kanban_etkEmpId", table_name="etapa_kanban")
    op.drop_table("etapa_kanban")

    op.drop_index("ix_produto_proEmpId", table_name="produto")
    op.drop_table("produto")

    op.drop_index("ix_motivo_cancelamento_mcaEmpId", table_name="motivo_cancelamento")
    op.drop_table("motivo_cancelamento")

    op.drop_index("ix_como_conheceu_ccoEmpId", table_name="como_conheceu")
    op.drop_table("como_conheceu")
