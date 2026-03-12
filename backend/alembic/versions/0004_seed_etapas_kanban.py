"""seed etapas padrao kanban para empresa 1

Revision ID: 0004_seed_etapas
Revises: 0003_crm
Create Date: 2026-03-09

"""

from collections.abc import Sequence
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision: str = "0004_seed_etapas"
down_revision: str | None = "0003_crm"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ETAPAS_PADRAO = [
    ("Novo Lead", "#6b7280"),
    ("Agendar Reunião", "#3b82f6"),
    ("Reunião Realizada", "#8b5cf6"),
    ("Enviar Proposta", "#f59e0b"),
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
    result = conn.execute(sa.select(sa.func.count()).select_from(etk).where(etk.c.etkEmpId == 1))
    if (result.scalar() or 0) > 0:
        return
    now = datetime.now(timezone.utc)
    for ordem, (nome, cor) in enumerate(ETAPAS_PADRAO, start=1):
        conn.execute(
            etk.insert().values(
                etkEmpId=1,
                etkNome=nome,
                etkOrdem=ordem,
                etkPipeline="default",
                etkCor=cor,
                etkAtivo=True,
                etkDataCriacao=now,
                etkDataAtualizacao=None,
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM etapa_kanban WHERE etkEmpId = 1"))
