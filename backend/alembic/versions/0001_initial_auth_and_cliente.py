"""initial auth and cliente tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-09
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "empresa",
        sa.Column("empId", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("empNome", sa.String(length=200), nullable=False),
        sa.Column("empAtivo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("empDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("empDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "usuario",
        sa.Column("usuId", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("usuNome", sa.String(length=200), nullable=False),
        sa.Column("usuEmail", sa.String(length=255), nullable=False),
        sa.Column("usuSenhaHash", sa.String(length=255), nullable=False),
        sa.Column("usuAdmin", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("usuPerfil", sa.String(length=50), nullable=True),
        sa.Column("usuAtivo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("usuDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usuDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("usuEmail", name="uq_usuario_email"),
    )
    op.create_index("ix_usuario_email", "usuario", ["usuEmail"])

    op.create_table(
        "usuario_empresa",
        sa.Column("useId", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("useUsuId", sa.Integer, nullable=False),
        sa.Column("useEmpId", sa.Integer, nullable=False),
        sa.ForeignKeyConstraint(["useUsuId"], ["usuario.usuId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["useEmpId"], ["empresa.empId"], ondelete="CASCADE"),
    )
    op.create_index("ix_usuario_empresa_useUsuId", "usuario_empresa", ["useUsuId"])
    op.create_index("ix_usuario_empresa_useEmpId", "usuario_empresa", ["useEmpId"])

    op.create_table(
        "cliente",
        sa.Column("cliId", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("cliEmpId", sa.Integer, nullable=True),
        sa.Column("cliNome", sa.String(length=200), nullable=False),
        sa.Column("cliEmail", sa.String(length=255), nullable=True),
        sa.Column("cliTelefone", sa.String(length=50), nullable=True),
        sa.Column("cliAtivo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("cliDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cliDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["cliEmpId"], ["empresa.empId"], ondelete="SET NULL"),
    )
    op.create_index("ix_cliente_cliEmpId", "cliente", ["cliEmpId"])


def downgrade() -> None:
    op.drop_index("ix_cliente_cliEmpId", table_name="cliente")
    op.drop_table("cliente")

    op.drop_index("ix_usuario_empresa_useEmpId", table_name="usuario_empresa")
    op.drop_index("ix_usuario_empresa_useUsuId", table_name="usuario_empresa")
    op.drop_table("usuario_empresa")

    op.drop_index("ix_usuario_email", table_name="usuario")
    op.drop_table("usuario")

    op.drop_table("empresa")

