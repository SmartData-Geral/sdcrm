"""
Banco SQLite em memoria com o schema completo, para testes de servico que precisam de SQL
de verdade (sincronizacao, vinculo, indicadores). Os demais testes seguem com mocks.
"""

import os

os.environ.setdefault("API_KEY_PEPPER", "pepper-de-teste")

from datetime import date  # noqa: E402

from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import backend.models  # noqa: E402,F401  (registra todas as tabelas no metadata)
from backend.core.cripto import cifrar  # noqa: E402
from backend.database import Base  # noqa: E402
from backend.models.como_conheceu import ComoConheceu  # noqa: E402
from backend.models.empresa import Empresa  # noqa: E402
from backend.models.meta_ads_campanha import MetaAdsCampanha  # noqa: E402
from backend.models.meta_ads_conta import MetaAdsConta  # noqa: E402
from backend.models.meta_ads_conta_origem import MetaAdsContaOrigem  # noqa: E402
from backend.models.meta_ads_insight_diario import MetaAdsInsightDiario  # noqa: E402
from backend.models.oportunidade import Oportunidade  # noqa: E402


def nova_sessao() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _ligar_fks(conexao, _registro):
        conexao.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    # Mesmas opcoes do SessionLocal de producao (expire_on_commit padrao = True).
    return sessionmaker(bind=engine, autoflush=False)()


def criar_empresa(db: Session, nome: str = "Acme") -> Empresa:
    emp = Empresa(empNome=nome)
    db.add(emp)
    db.commit()
    return emp


def criar_origem(db: Session, emp_id: int, nome: str) -> ComoConheceu:
    cco = ComoConheceu(ccoEmpId=emp_id, ccoNome=nome)
    db.add(cco)
    db.commit()
    return cco


def criar_oportunidade(db: Session, emp_id: int, **campos) -> Oportunidade:
    base = dict(opoEmpId=emp_id, opoTitulo="Lead", opoDataRecebimento=date(2026, 10, 1))
    base.update(campos)
    opo = Oportunidade(**base)
    db.add(opo)
    db.commit()
    return opo


def criar_conta(
    db: Session,
    emp_id: int,
    *,
    act: str = "act_111",
    nome: str = "Conta",
    token: str = "EAAB-token-de-teste-1234",
    origens=(),
) -> MetaAdsConta:
    conta = MetaAdsConta(
        macEmpId=emp_id,
        macNome=nome,
        macContaExterna=act,
        macToken=cifrar(token),
        macTokenFinal=token[-4:],
    )
    db.add(conta)
    db.flush()
    for cco_id in origens:
        db.add(MetaAdsContaOrigem(mcoMacId=conta.macId, mcoCcoId=cco_id))
    db.commit()
    return conta


def criar_campanha(
    db: Session, conta: MetaAdsConta, externa: str, nome: str, status: str = "ACTIVE"
) -> MetaAdsCampanha:
    camp = MetaAdsCampanha(
        mcgEmpId=conta.macEmpId,
        mcgMacId=conta.macId,
        mcgCampanhaExterna=externa,
        mcgNome=nome,
        mcgNomeNormalizado=" ".join(nome.split()).lower(),
        mcgStatus=status,
    )
    db.add(camp)
    db.commit()
    return camp


def criar_insight(
    db: Session,
    campanha: MetaAdsCampanha,
    dia: date,
    investimento: float,
    *,
    impressoes: int = 1000,
    cliques: int = 50,
    leads: int = 0,
) -> MetaAdsInsightDiario:
    linha = MetaAdsInsightDiario(
        midEmpId=campanha.mcgEmpId,
        midMacId=campanha.mcgMacId,
        midMcgId=campanha.mcgId,
        midData=dia,
        midInvestimento=investimento,
        midImpressoes=impressoes,
        midCliques=cliques,
        midAlcance=0,
        midLeadsMeta=leads,
    )
    db.add(linha)
    db.commit()
    return linha
