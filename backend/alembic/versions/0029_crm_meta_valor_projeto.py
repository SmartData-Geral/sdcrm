"""CRM: meta mensal de valor de projeto (venda pontual)

Revision ID: 0029_crm_meta_valor_projeto
Revises: 0028_webhooks_saida
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0029_crm_meta_valor_projeto"
down_revision: str | None = "0028_webhooks_saida"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "crm_meta_mensal",
        sa.Column("cmmValorProjeto", sa.Numeric(14, 2), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("crm_meta_mensal", "cmmValorProjeto")
