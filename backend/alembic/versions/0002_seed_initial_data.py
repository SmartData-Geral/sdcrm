"""seed initial empresa, admin user and vinculo

Revision ID: 0002_seed_initial_data
Revises: 0001_initial
Create Date: 2026-03-09
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

from backend.auth import get_password_hash


revision: str = "0002_seed_initial_data"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    empresa_table = sa.table(
        "empresa",
        sa.column("empId", sa.Integer),
        sa.column("empNome", sa.String),
        sa.column("empAtivo", sa.Boolean),
        sa.column("empDataCriacao", sa.DateTime(timezone=True)),
        sa.column("empDataAtualizacao", sa.DateTime(timezone=True)),
    )

    usuario_table = sa.table(
        "usuario",
        sa.column("usuId", sa.Integer),
        sa.column("usuNome", sa.String),
        sa.column("usuEmail", sa.String),
        sa.column("usuSenhaHash", sa.String),
        sa.column("usuAdmin", sa.Boolean),
        sa.column("usuPerfil", sa.String),
        sa.column("usuAtivo", sa.Boolean),
        sa.column("usuDataCriacao", sa.DateTime(timezone=True)),
        sa.column("usuDataAtualizacao", sa.DateTime(timezone=True)),
    )

    usuario_empresa_table = sa.table(
        "usuario_empresa",
        sa.column("useId", sa.Integer),
        sa.column("useUsuId", sa.Integer),
        sa.column("useEmpId", sa.Integer),
    )

    conn = op.get_bind()

    result = conn.execute(sa.select(sa.func.count()).select_from(empresa_table))
    if (result.scalar() or 0) > 0:
        return

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    conn.execute(
        empresa_table.insert().values(
            empId=1,
            empNome="Empresa Padrão",
            empAtivo=True,
            empDataCriacao=now,
            empDataAtualizacao=None,
        )
    )

    admin_password_hash = get_password_hash("admin123")

    conn.execute(
        usuario_table.insert().values(
            usuId=1,
            usuNome="Administrador",
            usuEmail="admin@smartdata.local",
            usuSenhaHash=admin_password_hash,
            usuAdmin=True,
            usuPerfil="admin",
            usuAtivo=True,
            usuDataCriacao=now,
            usuDataAtualizacao=None,
        )
    )

    conn.execute(
        usuario_empresa_table.insert().values(
            useId=1,
            useUsuId=1,
            useEmpId=1,
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM usuario_empresa WHERE useId = 1"))
    conn.execute(sa.text("DELETE FROM usuario WHERE usuId = 1"))
    conn.execute(sa.text("DELETE FROM empresa WHERE empId = 1"))

