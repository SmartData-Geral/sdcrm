"""add cadastro de blocos padrao de proposta

Revision ID: 0011_cadastro_bloco_padrao
Revises: 0010_propostas_modulo
Create Date: 2026-03-15
"""

from collections.abc import Sequence
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision: str = "0011_cadastro_bloco_padrao"
down_revision: str | None = "0010_propostas_modulo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "proposta_bloco_padrao",
        sa.Column("pbpId", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pbpEmpId", sa.Integer(), nullable=False),
        sa.Column("pbpPtlId", sa.Integer(), nullable=True),
        sa.Column("pbpTipo", sa.String(length=60), nullable=False),
        sa.Column("pbpTitulo", sa.String(length=200), nullable=True),
        sa.Column("pbpSubtitulo", sa.String(length=300), nullable=True),
        sa.Column("pbpOrdem", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("pbpVisivel", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("pbpDadosJson", sa.JSON(), nullable=True),
        sa.Column("pbpAtivo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("pbpDataCriacao", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pbpDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pbpEmpId"], ["empresa.empId"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pbpPtlId"], ["proposta_template.ptlId"], ondelete="SET NULL"),
    )
    op.create_index("ix_proposta_bloco_padrao_pbpEmpId", "proposta_bloco_padrao", ["pbpEmpId"])
    op.create_index("ix_proposta_bloco_padrao_pbpPtlId", "proposta_bloco_padrao", ["pbpPtlId"])
    op.create_index("ix_proposta_bloco_padrao_pbpTipo", "proposta_bloco_padrao", ["pbpTipo"])
    op.create_index("ix_proposta_bloco_padrao_pbpOrdem", "proposta_bloco_padrao", ["pbpOrdem"])

    bind = op.get_bind()
    empresa_tbl = sa.table("empresa", sa.column("empId", sa.Integer()))
    bloco_tbl = sa.table(
        "proposta_bloco_padrao",
        sa.column("pbpEmpId", sa.Integer()),
        sa.column("pbpPtlId", sa.Integer()),
        sa.column("pbpTipo", sa.String()),
        sa.column("pbpTitulo", sa.String()),
        sa.column("pbpSubtitulo", sa.String()),
        sa.column("pbpOrdem", sa.Integer()),
        sa.column("pbpVisivel", sa.Boolean()),
        sa.column("pbpDadosJson", sa.JSON()),
        sa.column("pbpAtivo", sa.Boolean()),
        sa.column("pbpDataCriacao", sa.DateTime(timezone=True)),
        sa.column("pbpDataAtualizacao", sa.DateTime(timezone=True)),
    )
    emp_ids = [row.empId for row in bind.execute(sa.select(empresa_tbl.c.empId))]
    now = datetime.utcnow()
    rows: list[dict] = []
    base = [
        ("hero", "Hero", None, 1, {"titulo": "Proposta Comercial Smart Data", "subtitulo": "Solução comercial personalizada"}),
        ("apresentacao", "Apresentação", None, 2, {"titulo": "Contexto", "texto": "Resumo do cenário e proposta de valor."}),
        ("metodologia", "Metodologia", None, 3, {"titulo": "Metodologia", "itens": ["Descoberta", "Implementação", "Acompanhamento"]}),
        ("escopo_inicial", "Escopo Inicial", None, 4, {"visivel": True, "cards": []}),
        ("valores_projeto", "Valores Projeto", None, 5, {"visivel": True}),
        ("valores_planos", "Valores Planos", None, 6, {"visivel": False, "planos": []}),
        ("clientes", "Clientes", None, 7, {"titulo": "Clientes", "itens": []}),
        ("cta_final", "CTA Final", None, 8, {"titulo": "Próximo passo", "texto": "Vamos avançar com a proposta?"}),
    ]
    for emp_id in emp_ids:
        for tipo, titulo, subtitulo, ordem, dados in base:
            rows.append(
                {
                    "pbpEmpId": emp_id,
                    "pbpPtlId": None,
                    "pbpTipo": tipo,
                    "pbpTitulo": titulo,
                    "pbpSubtitulo": subtitulo,
                    "pbpOrdem": ordem,
                    "pbpVisivel": True,
                    "pbpDadosJson": dados,
                    "pbpAtivo": True,
                    "pbpDataCriacao": now,
                    "pbpDataAtualizacao": now,
                }
            )
    if rows:
        bind.execute(bloco_tbl.insert(), rows)


def downgrade() -> None:
    op.drop_index("ix_proposta_bloco_padrao_pbpOrdem", table_name="proposta_bloco_padrao")
    op.drop_index("ix_proposta_bloco_padrao_pbpTipo", table_name="proposta_bloco_padrao")
    op.drop_index("ix_proposta_bloco_padrao_pbpPtlId", table_name="proposta_bloco_padrao")
    op.drop_index("ix_proposta_bloco_padrao_pbpEmpId", table_name="proposta_bloco_padrao")
    op.drop_table("proposta_bloco_padrao")

