"""
Indicadores das campanhas: investimento do Meta cruzado com os leads do CRM.

Um lead "e do Meta" quando esta ligado a uma campanha (opoMcgId) ou, sem campanha, quando
sua origem esta mapeada numa conta ativa. Leads, vendas, MRR e Projeto usam as MESMAS
condicoes de periodo da aba Fontes do Dashboard (condicoes_periodo), para os numeros baterem.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, case, false, func, or_, select
from sqlalchemy.orm import Session

from ...exceptions import BadRequestError, NotFoundError
from ...models.meta_ads_campanha import MetaAdsCampanha
from ...models.meta_ads_conta import MetaAdsConta
from ...models.meta_ads_conta_origem import MetaAdsContaOrigem
from ...models.meta_ads_insight_diario import MetaAdsInsightDiario
from ...models.oportunidade import Oportunidade
from ...schemas.meta_ads import (
    MetaAdsCampanhaDetalheResponse,
    MetaAdsCampanhaOpcao,
    MetaAdsCampanhaOpcoesResponse,
    MetaAdsContaOpcao,
    MetaAdsContaOpcoesResponse,
    MetaAdsLeadItem,
    MetaAdsLinha,
    MetaAdsPainelResponse,
    MetaAdsResumoResponse,
    MetaAdsSerieDia,
    OportunidadeCampanhaMetaResponse,
)
# Helpers "privados" do dashboard reusados de proposito: e a garantia de que as regras
# de MRR/Projeto e de periodo sao exatamente as mesmas da aba Fontes.
from ..crm_dashboard_service import (
    _between_dates,
    _mrr_incremental_expr,
    _valor_projeto_expr,
    condicoes_periodo,
)

NOME_NAO_IDENTIFICADA = "Meta — campanha não identificada"
GASTO_ZERO = {"investimento": 0.0, "impressoes": 0, "cliques": 0, "leadsMeta": 0}
LEADS_ZERO = {"leadsCrm": 0, "vendas": 0, "mrr": 0.0, "projeto": 0.0}


@dataclass(frozen=True)
class FiltroPainel:
    data_inicial: date | None
    data_final: date | None
    mac_id: int | None = None
    somente_ativas: bool = False


def _dividir(a: float, b: float) -> float | None:
    return round(a / b, 2) if b else None


def calcular_derivados(
    *, investimento: float, leads: int, vendas: int, mrr: float, projeto: float, impressoes: int, cliques: int
) -> dict:
    return {
        "ctr": round(cliques / impressoes * 100, 2) if impressoes else None,
        "cpc": _dividir(investimento, cliques),
        "cpl": _dividir(investimento, leads),
        "cac": _dividir(investimento, vendas),
        "retorno": _dividir(mrr * 12 + projeto, investimento),
    }


def _linha(mcg_id, nome, status, mac_id, gasto: dict, leads: dict) -> MetaAdsLinha:
    investimento = round(gasto["investimento"], 2)
    return MetaAdsLinha(
        mcgId=mcg_id,
        nome=nome,
        status=status,
        macId=mac_id,
        investimento=investimento,
        impressoes=gasto["impressoes"],
        cliques=gasto["cliques"],
        leadsMeta=gasto["leadsMeta"],
        leadsCrm=leads["leadsCrm"],
        vendas=leads["vendas"],
        mrr=round(leads["mrr"], 2),
        projeto=round(leads["projeto"], 2),
        **calcular_derivados(
            investimento=investimento,
            leads=leads["leadsCrm"],
            vendas=leads["vendas"],
            mrr=leads["mrr"],
            projeto=leads["projeto"],
            impressoes=gasto["impressoes"],
            cliques=gasto["cliques"],
        ),
    )


def _tem_movimento(gasto: dict, leads: dict) -> bool:
    return bool(
        gasto["investimento"] or gasto["leadsMeta"] or leads["leadsCrm"] or leads["vendas"] or leads["mrr"] or leads["projeto"]
    )


def tem_conta(db: Session, emp_id: int) -> bool:
    return (
        db.execute(
            select(MetaAdsConta.macId)
            .where(MetaAdsConta.macEmpId == emp_id, MetaAdsConta.macAtivo.is_(True))
            .limit(1)
        ).first()
        is not None
    )


def _origens_meta(db: Session, emp_id: int, mac_id: int | None) -> list[int]:
    stmt = (
        select(MetaAdsContaOrigem.mcoCcoId)
        .join(MetaAdsConta, MetaAdsConta.macId == MetaAdsContaOrigem.mcoMacId)
        .where(MetaAdsConta.macEmpId == emp_id, MetaAdsConta.macAtivo.is_(True))
    )
    if mac_id is not None:
        stmt = stmt.where(MetaAdsConta.macId == mac_id)
    return sorted(set(db.execute(stmt).scalars()))


def _condicao_lead_meta(db: Session, emp_id: int, mac_id: int | None):
    if mac_id is None:
        ligada = Oportunidade.opoMcgId.isnot(None)
    else:
        ligada = Oportunidade.opoMcgId.in_(
            select(MetaAdsCampanha.mcgId).where(MetaAdsCampanha.mcgMacId == mac_id)
        )
    origens = _origens_meta(db, emp_id, mac_id)
    sem_campanha = (
        and_(Oportunidade.opoMcgId.is_(None), Oportunidade.opoCcoId.in_(origens))
        if origens
        else false()
    )
    return or_(ligada, sem_campanha)


def _gastos(db: Session, emp_id: int, filtro: FiltroPainel) -> dict[int, dict]:
    m = MetaAdsInsightDiario
    conds = [m.midEmpId == emp_id]
    periodo = _between_dates(m.midData, filtro.data_inicial, filtro.data_final)
    if periodo is not None:
        conds.append(periodo)
    if filtro.mac_id is not None:
        conds.append(m.midMacId == filtro.mac_id)
    stmt = (
        select(
            m.midMcgId,
            func.coalesce(func.sum(m.midInvestimento), 0).label("inv"),
            func.coalesce(func.sum(m.midImpressoes), 0).label("imp"),
            func.coalesce(func.sum(m.midCliques), 0).label("cli"),
            func.coalesce(func.sum(m.midLeadsMeta), 0).label("lm"),
        )
        .where(*conds)
        .group_by(m.midMcgId)
    )
    return {
        r.midMcgId: {
            "investimento": float(r.inv),
            "impressoes": int(r.imp),
            "cliques": int(r.cli),
            "leadsMeta": int(r.lm),
        }
        for r in db.execute(stmt)
    }


def _leads(db: Session, emp_id: int, filtro: FiltroPainel) -> dict[int | None, dict]:
    cond = condicoes_periodo(filtro.data_inicial, filtro.data_final)
    stmt = (
        select(
            Oportunidade.opoMcgId,
            func.coalesce(func.sum(case((cond.recebidas, 1), else_=0)), 0).label("rec"),
            func.coalesce(func.sum(case((cond.ganhas, 1), else_=0)), 0).label("gan"),
            func.coalesce(func.sum(_mrr_incremental_expr()), 0).label("mrr"),
            func.coalesce(func.sum(_valor_projeto_expr()), 0).label("proj"),
        )
        .where(
            Oportunidade.opoEmpId == emp_id,
            _condicao_lead_meta(db, emp_id, filtro.mac_id),
            cond.escopo,
        )
        .group_by(Oportunidade.opoMcgId)
    )
    return {
        r.opoMcgId: {
            "leadsCrm": int(r.rec),
            "vendas": int(r.gan),
            "mrr": float(r.mrr),
            "projeto": float(r.proj),
        }
        for r in db.execute(stmt)
    }


def _somar(linhas: list[MetaAdsLinha]) -> MetaAdsLinha:
    gasto = {k: sum(getattr(l, k) for l in linhas) for k in GASTO_ZERO}
    leads = {k: sum(getattr(l, k) for l in linhas) for k in LEADS_ZERO}
    return _linha(None, "Total", None, None, gasto, leads)


def painel(db: Session, emp_id: int, filtro: FiltroPainel) -> MetaAdsPainelResponse:
    gastos = _gastos(db, emp_id, filtro)
    leads = _leads(db, emp_id, filtro)
    ids = {i for i in set(gastos) | set(leads) if i is not None}
    campanhas = {
        c.mcgId: c
        for c in db.execute(select(MetaAdsCampanha).where(MetaAdsCampanha.mcgId.in_(ids))).scalars()
    } if ids else {}

    linhas: list[MetaAdsLinha] = []
    for mcg_id, camp in campanhas.items():
        if camp.mcgEmpId != emp_id:
            continue
        if filtro.somente_ativas and camp.mcgStatus != "ACTIVE":
            continue
        gasto = gastos.get(mcg_id, GASTO_ZERO)
        lead = leads.get(mcg_id, LEADS_ZERO)
        if _tem_movimento(gasto, lead):
            linhas.append(_linha(mcg_id, camp.mcgNome, camp.mcgStatus, camp.mcgMacId, gasto, lead))
    linhas.sort(key=lambda l: (l.investimento, l.leadsCrm), reverse=True)

    nao_identificada = None
    if None in leads and _tem_movimento(GASTO_ZERO, leads[None]):
        nao_identificada = _linha(None, NOME_NAO_IDENTIFICADA, None, None, GASTO_ZERO, leads[None])

    total = _somar(linhas + ([nao_identificada] if nao_identificada else []))
    return MetaAdsPainelResponse(
        temConta=tem_conta(db, emp_id), total=total, campanhas=linhas, naoIdentificada=nao_identificada
    )


def _campanha_da_empresa(db: Session, emp_id: int, mcg_id: int) -> MetaAdsCampanha:
    camp = db.get(MetaAdsCampanha, mcg_id)
    if camp is None or camp.mcgEmpId != emp_id:
        raise NotFoundError("Campanha não encontrada")
    return camp


def detalhe_campanha(
    db: Session, emp_id: int, mcg_id: int, data_inicial: date | None, data_final: date | None
) -> MetaAdsCampanhaDetalheResponse:
    camp = _campanha_da_empresa(db, emp_id, mcg_id)
    filtro = FiltroPainel(data_inicial, data_final, mac_id=camp.mcgMacId)
    linha = next(
        (l for l in painel(db, emp_id, filtro).campanhas if l.mcgId == mcg_id),
        _linha(mcg_id, camp.mcgNome, camp.mcgStatus, camp.mcgMacId, GASTO_ZERO, LEADS_ZERO),
    )

    m = MetaAdsInsightDiario
    conds = [m.midMcgId == mcg_id, m.midEmpId == emp_id]
    periodo = _between_dates(m.midData, data_inicial, data_final)
    if periodo is not None:
        conds.append(periodo)
    dias: dict[date, dict] = {}
    for r in db.execute(
        select(m.midData, m.midInvestimento, m.midLeadsMeta).where(*conds)
    ):
        dias[r.midData] = {"investimento": float(r.midInvestimento), "leadsMeta": r.midLeadsMeta, "leadsCrm": 0}

    cond = condicoes_periodo(data_inicial, data_final)
    for r in db.execute(
        select(Oportunidade.opoDataRecebimento, func.count(Oportunidade.opoId).label("n"))
        .where(
            Oportunidade.opoMcgId == mcg_id, Oportunidade.opoEmpId == emp_id, cond.recebidas
        )
        .group_by(Oportunidade.opoDataRecebimento)
    ):
        dia = dias.setdefault(r.opoDataRecebimento, {"investimento": 0.0, "leadsMeta": 0, "leadsCrm": 0})
        dia["leadsCrm"] = int(r.n)
    serie = [MetaAdsSerieDia(data=d, **v) for d, v in sorted(dias.items())]

    oportunidades = db.execute(
        select(Oportunidade)
        .where(
            Oportunidade.opoMcgId == mcg_id,
            Oportunidade.opoEmpId == emp_id,
            or_(cond.recebidas, cond.ganhas, cond.perdidas),
        )
        .order_by(Oportunidade.opoDataRecebimento.desc(), Oportunidade.opoId.desc())
        .limit(500)
    ).scalars()
    leads = [
        MetaAdsLeadItem(
            opoId=o.opoId,
            opoTitulo=o.opoTitulo,
            opoNomeContato=o.opoNomeContato,
            opoDataRecebimento=o.opoDataRecebimento,
            opoStatusFechamento=o.opoStatusFechamento,
            opoValorFechado=float(o.opoValorFechado) if o.opoValorFechado is not None else None,
        )
        for o in oportunidades
    ]
    return MetaAdsCampanhaDetalheResponse(campanha=linha, serie=serie, leads=leads)


def resumo(db: Session, emp_id: int, data_inicial: date | None, data_final: date | None) -> MetaAdsResumoResponse:
    p = painel(db, emp_id, FiltroPainel(data_inicial, data_final))
    t = p.total
    return MetaAdsResumoResponse(
        temConta=p.temConta,
        investimento=t.investimento,
        leadsCrm=t.leadsCrm,
        vendas=t.vendas,
        cpl=t.cpl,
        cac=t.cac,
        retorno=t.retorno,
    )


def opcoes_campanhas(db: Session, emp_id: int) -> MetaAdsCampanhaOpcoesResponse:
    linhas = db.execute(
        select(MetaAdsCampanha, MetaAdsConta.macNome)
        .join(MetaAdsConta, MetaAdsConta.macId == MetaAdsCampanha.mcgMacId)
        .where(MetaAdsCampanha.mcgEmpId == emp_id)
        .order_by(case((MetaAdsCampanha.mcgStatus == "ACTIVE", 0), else_=1), MetaAdsCampanha.mcgNome)
    ).all()
    return MetaAdsCampanhaOpcoesResponse(
        items=[
            MetaAdsCampanhaOpcao(mcgId=c.mcgId, nome=c.mcgNome, conta=nome_conta, status=c.mcgStatus)
            for c, nome_conta in linhas
        ]
    )


def opcoes_contas(db: Session, emp_id: int) -> MetaAdsContaOpcoesResponse:
    linhas = db.execute(
        select(MetaAdsConta.macId, MetaAdsConta.macNome)
        .where(MetaAdsConta.macEmpId == emp_id, MetaAdsConta.macAtivo.is_(True))
        .order_by(MetaAdsConta.macNome)
    ).all()
    return MetaAdsContaOpcoesResponse(items=[MetaAdsContaOpcao(macId=i, macNome=n) for i, n in linhas])


def definir_campanha_oportunidade(
    db: Session, emp_id: int, opo_id: int, mcg_id: int | None
) -> OportunidadeCampanhaMetaResponse:
    opo = db.get(Oportunidade, opo_id)
    if opo is None or opo.opoEmpId != emp_id or not opo.opoAtivo:
        raise NotFoundError("Oportunidade não encontrada")
    if mcg_id is not None:
        camp = db.get(MetaAdsCampanha, mcg_id)
        if camp is None or camp.mcgEmpId != emp_id:
            raise BadRequestError("Campanha inválida para esta empresa")
    opo.opoMcgId = mcg_id
    opo.opoMcgManual = True
    db.commit()
    return OportunidadeCampanhaMetaResponse(opoId=opo.opoId, opoMcgId=opo.opoMcgId, opoMcgManual=True)
