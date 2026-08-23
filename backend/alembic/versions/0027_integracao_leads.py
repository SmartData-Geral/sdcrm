"""Integracao de entrada de leads: chaves de API, log de requisicoes e rastreio de origem

Revision ID: 0027_integracao_leads
Revises: 0026_smart_agente_msg
"""

from collections.abc import Sequence
import re
import unicodedata

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0027_integracao_leads"
down_revision: str | None = "0026_smart_agente_msg"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABELA_CHAVE = "integracao_chave"
TABELA_LOG = "integracao_requisicao_log"

COLUNAS_OPORTUNIDADE = [
    ("opoOrigemSistema", sa.String(length=60)),
    ("opoOrigemExternalId", sa.String(length=120)),
    ("opoUtmSource", sa.String(length=100)),
    ("opoUtmMedium", sa.String(length=100)),
    ("opoUtmCampaign", sa.String(length=150)),
    ("opoUtmContent", sa.String(length=150)),
    ("opoUtmTerm", sa.String(length=150)),
    ("opoEmailNormalizado", sa.String(length=255)),
    ("opoTelefoneNormalizado", sa.String(length=20)),
    ("opoIchId", sa.Integer()),
    ("opoOpoAnteriorId", sa.Integer()),
]


# ---------------------------------------------------------------------------------
# Normalizacao copiada de backend/services/lead_normalizacao.py DE PROPOSITO.
# Uma migration precisa produzir sempre o mesmo resultado; se importasse o service,
# o backfill mudaria de comportamento junto com a regra de negocio.
# ---------------------------------------------------------------------------------
_SO_DIGITOS = re.compile(r"\D+")
_EMAIL_BASICO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_INICIAIS_CELULAR = frozenset("6789")
DDI_BRASIL = "55"


def _norm_email(valor):
    if valor is None:
        return None
    texto = unicodedata.normalize("NFKC", str(valor)).strip().lower()
    if not texto or len(texto) > 255 or not _EMAIL_BASICO.match(texto):
        return None
    return texto


def _canonizar_nacional(nacional):
    ddd, assinante = nacional[:2], nacional[2:]
    if not ddd.isdigit() or int(ddd) < 11:
        return None
    if not assinante or assinante[0] == "0":
        return None
    if len(assinante) == 8 and assinante[0] in _INICIAIS_CELULAR:
        assinante = "9" + assinante
    return ddd + assinante


def _norm_telefone(valor):
    if valor is None:
        return None
    bruto = str(valor).strip()
    if not bruto:
        return None
    internacional = bruto.startswith("+")
    digitos = _SO_DIGITOS.sub("", bruto)
    if not digitos:
        return None
    if digitos.startswith("00") and len(digitos) > 12:
        digitos = digitos[2:]
        internacional = True
    if internacional and not digitos.startswith(DDI_BRASIL):
        return digitos[:20] if 8 <= len(digitos) <= 20 else None
    if len(digitos) in (10, 11):
        nacional = digitos
    elif len(digitos) in (12, 13) and digitos.startswith(DDI_BRASIL):
        nacional = digitos[2:]
    else:
        return None
    canonico = _canonizar_nacional(nacional)
    return None if canonico is None else DDI_BRASIL + canonico


def _indices(insp, tabela):
    try:
        return {i["name"] for i in insp.get_indexes(tabela)}
    except Exception:
        return set()


def _fks(insp, tabela):
    try:
        return {f["name"] for f in insp.get_foreign_keys(tabela) if f.get("name")}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tabelas = set(insp.get_table_names())

    # 1) Chaves de API. Precisa existir antes de oportunidade.opoIchId referencia-la.
    if TABELA_CHAVE not in tabelas:
        op.create_table(
            TABELA_CHAVE,
            sa.Column("ichId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("ichEmpId", sa.Integer(), nullable=False),
            sa.Column("ichNome", sa.String(length=120), nullable=False),
            sa.Column("ichDescricao", sa.String(length=300), nullable=True),
            sa.Column("ichPrefixo", sa.String(length=32), nullable=False),
            sa.Column("ichHashSecret", sa.String(length=64), nullable=False),
            sa.Column(
                "ichEscopos",
                sa.String(length=255),
                nullable=False,
                server_default="leads:write",
            ),
            sa.Column("ichUsuResponsavelPadraoId", sa.Integer(), nullable=True),
            sa.Column("ichUltimoUsoEm", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ichExpiraEm", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ichRevogadaEm", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ichRevogadaUsuId", sa.Integer(), nullable=True),
            sa.Column("ichCriadaUsuId", sa.Integer(), nullable=True),
            sa.Column("ichAtivo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("ichDataCriacao", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ichDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("ichId"),
            sa.ForeignKeyConstraint(["ichEmpId"], ["empresa.empId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["ichUsuResponsavelPadraoId"], ["usuario.usuId"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(["ichRevogadaUsuId"], ["usuario.usuId"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["ichCriadaUsuId"], ["usuario.usuId"], ondelete="SET NULL"),
        )

    insp = inspect(bind)
    idx = _indices(insp, TABELA_CHAVE)
    if "uq_integracao_chave_prefixo" not in idx:
        op.create_index("uq_integracao_chave_prefixo", TABELA_CHAVE, ["ichPrefixo"], unique=True)
    if "ix_integracao_chave_ichEmpId" not in idx:
        op.create_index("ix_integracao_chave_ichEmpId", TABELA_CHAVE, ["ichEmpId"])

    # 2) Colunas de rastreio de origem em oportunidade.
    cols = {c["name"] for c in insp.get_columns("oportunidade")}
    for nome, tipo in COLUNAS_OPORTUNIDADE:
        if nome not in cols:
            op.add_column("oportunidade", sa.Column(nome, tipo, nullable=True))

    fks = _fks(inspect(bind), "oportunidade")
    if "fk_oportunidade_opoIchId" not in fks:
        op.create_foreign_key(
            "fk_oportunidade_opoIchId",
            "oportunidade",
            TABELA_CHAVE,
            ["opoIchId"],
            ["ichId"],
            ondelete="SET NULL",
        )
    if "fk_oportunidade_opoOpoAnteriorId" not in fks:
        op.create_foreign_key(
            "fk_oportunidade_opoOpoAnteriorId",
            "oportunidade",
            "oportunidade",
            ["opoOpoAnteriorId"],
            ["opoId"],
            ondelete="SET NULL",
        )

    # Indices de dedup. NAO-UNICOS de proposito: quando um lead retorna depois de a
    # oportunidade ter sido fechada, a regra e abrir uma NOVA -- um indice unico em
    # (empresa, origem, external_id) bloquearia exatamente esse caso.
    idx = _indices(inspect(bind), "oportunidade")
    if "ix_oportunidade_dedup_email" not in idx:
        op.create_index(
            "ix_oportunidade_dedup_email", "oportunidade", ["opoEmpId", "opoEmailNormalizado"]
        )
    if "ix_oportunidade_dedup_telefone" not in idx:
        op.create_index(
            "ix_oportunidade_dedup_telefone",
            "oportunidade",
            ["opoEmpId", "opoTelefoneNormalizado"],
        )
    if "ix_oportunidade_origem_externa" not in idx:
        op.create_index(
            "ix_oportunidade_origem_externa",
            "oportunidade",
            ["opoEmpId", "opoOrigemSistema", "opoOrigemExternalId"],
        )

    # 3) Log de requisicoes da API.
    if TABELA_LOG not in set(inspect(bind).get_table_names()):
        op.create_table(
            TABELA_LOG,
            sa.Column("irlId", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("irlEmpId", sa.Integer(), nullable=True),
            sa.Column("irlIchId", sa.Integer(), nullable=True),
            sa.Column("irlPrefixoInformado", sa.String(length=40), nullable=True),
            sa.Column("irlRota", sa.String(length=120), nullable=False),
            sa.Column("irlMetodo", sa.String(length=10), nullable=False),
            sa.Column("irlOrigemSistema", sa.String(length=60), nullable=True),
            sa.Column("irlExternalId", sa.String(length=120), nullable=True),
            sa.Column("irlStatusHttp", sa.Integer(), nullable=False),
            sa.Column("irlResultado", sa.String(length=20), nullable=False),
            sa.Column("irlOpoId", sa.Integer(), nullable=True),
            sa.Column("irlPayloadJson", sa.JSON(), nullable=True),
            sa.Column("irlErroJson", sa.JSON(), nullable=True),
            sa.Column("irlIp", sa.String(length=64), nullable=True),
            sa.Column("irlUserAgent", sa.String(length=600), nullable=True),
            sa.Column("irlDuracaoMs", sa.Integer(), nullable=True),
            sa.Column("irlAtivo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("irlDataCriacao", sa.DateTime(timezone=True), nullable=False),
            sa.Column("irlDataAtualizacao", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("irlId"),
            sa.ForeignKeyConstraint(["irlEmpId"], ["empresa.empId"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["irlIchId"], ["integracao_chave.ichId"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["irlOpoId"], ["oportunidade.opoId"], ondelete="SET NULL"),
        )

    idx = _indices(inspect(bind), TABELA_LOG)
    for nome, colunas in (
        ("ix_integracao_requisicao_log_emp_data", ["irlEmpId", "irlDataCriacao"]),
        ("ix_integracao_requisicao_log_ich_data", ["irlIchId", "irlDataCriacao"]),
        ("ix_integracao_requisicao_log_res_data", ["irlResultado", "irlDataCriacao"]),
        ("ix_integracao_requisicao_log_irlOpoId", ["irlOpoId"]),
    ):
        if nome not in idx:
            op.create_index(nome, TABELA_LOG, colunas)

    # 4) Backfill das colunas normalizadas.
    #    NAO e opcional: sem ele, o primeiro lead recebido para um contato que ja
    #    existe no CRM criaria uma duplicata, derrubando o criterio de aceite
    #    "mesmo lead 2x = 1 registro" logo no primeiro dia.
    _backfill_normalizados(bind)


def _backfill_normalizados(bind) -> None:
    linhas = bind.execute(
        sa.text(
            "SELECT opoId, opoEmail, opoTelefone FROM oportunidade "
            "WHERE opoEmail IS NOT NULL OR opoTelefone IS NOT NULL"
        )
    ).fetchall()

    atualizacoes = []
    for opo_id, email, telefone in linhas:
        email_norm = _norm_email(email)
        telefone_norm = _norm_telefone(telefone)
        if email_norm is not None or telefone_norm is not None:
            atualizacoes.append({"pid": opo_id, "e": email_norm, "t": telefone_norm})

    stmt = sa.text(
        "UPDATE oportunidade SET opoEmailNormalizado = :e, opoTelefoneNormalizado = :t "
        "WHERE opoId = :pid"
    )
    for params in atualizacoes:
        bind.execute(stmt, params)

    print(
        "[0027] backfill: {} oportunidade(s) normalizada(s) de {} com contato".format(
            len(atualizacoes), len(linhas)
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    tabelas = set(inspect(bind).get_table_names())

    if TABELA_LOG in tabelas:
        op.drop_table(TABELA_LOG)

    if "oportunidade" in tabelas:
        idx = _indices(inspect(bind), "oportunidade")
        for nome in (
            "ix_oportunidade_origem_externa",
            "ix_oportunidade_dedup_telefone",
            "ix_oportunidade_dedup_email",
        ):
            if nome in idx:
                op.drop_index(nome, table_name="oportunidade")

        fks = _fks(inspect(bind), "oportunidade")
        for nome in ("fk_oportunidade_opoOpoAnteriorId", "fk_oportunidade_opoIchId"):
            if nome in fks:
                op.drop_constraint(nome, "oportunidade", type_="foreignkey")

        cols = {c["name"] for c in inspect(bind).get_columns("oportunidade")}
        for nome, _tipo in reversed(COLUNAS_OPORTUNIDADE):
            if nome in cols:
                op.drop_column("oportunidade", nome)

    if TABELA_CHAVE in set(inspect(bind).get_table_names()):
        op.drop_table(TABELA_CHAVE)
