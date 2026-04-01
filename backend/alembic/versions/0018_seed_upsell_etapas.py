"""seed etapas padrao upsell para empresa 1

Revision ID: 0018_seed_upsell_etapas
Revises: 0017_contratos_defaults
Create Date: 2026-04-01

"""

from collections.abc import Sequence
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision: str = "0018_seed_upsell_etapas"
down_revision: str | None = "0017_contratos_defaults"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ETAPAS_UPSELL = [
    ("Base de Clientes", "#0ea5e9"),
    ("Contato Inicial", "#3b82f6"),
    ("Diagnóstico", "#8b5cf6"),
    ("Oferta Complementar", "#f59e0b"),
    ("Follow-Up", "#10b981"),
    ("Negociação", "#ec4899"),
    ("Fechado Ganho", "#22c55e"),
    ("Fechado Perdido", "#ef4444"),
]


def upgrade() -> None:
    conn = op.get_bind()
    etk = sa.table(
        "etapa_kanban",
        sa.column("etkId", sa.Integer),
        sa.column("etkEmpId", sa.Integer),
        sa.column("etkNome", sa.String),
        sa.column("etkOrdem", sa.Integer),
        sa.column("etkPipeline", sa.String),
        sa.column("etkCor", sa.String),
        sa.column("etkAtivo", sa.Boolean),
        sa.column("etkDataCriacao", sa.DateTime(timezone=True)),
        sa.column("etkDataAtualizacao", sa.DateTime(timezone=True)),
    )
    result = conn.execute(
        sa.select(sa.func.count()).select_from(etk).where(etk.c.etkEmpId == 1, etk.c.etkPipeline == "upsell")
    )
    if (result.scalar() or 0) > 0:
        return
    now = datetime.now(timezone.utc)
    for ordem, (nome, cor) in enumerate(ETAPAS_UPSELL, start=1):
        conn.execute(
            etk.insert().values(
                etkEmpId=1,
                etkNome=nome,
                etkOrdem=ordem,
                etkPipeline="upsell",
                etkCor=cor,
                etkAtivo=True,
                etkDataCriacao=now,
                etkDataAtualizacao=None,
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM etapa_kanban WHERE etkEmpId = 1 AND etkPipeline = 'upsell'"))
