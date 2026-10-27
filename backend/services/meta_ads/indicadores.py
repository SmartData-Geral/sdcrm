"""
Indicadores das campanhas: investimento do Meta cruzado com o funil dos leads do CRM.

Lead "da Meta":
- regra da fase 1 (padrao): ligado a uma campanha (opoMcgId) ou, sem campanha, com a origem
  mapeada numa conta ativa;
- com "Contar so leads com rastreio da Meta" (macExigirRastreio): sem campanha, so conta quem tem
  sinal da Meta (opoMetaLeadId/opoMetaAnuncioId). Os de origem mapeada sem sinal vao para
  `revisaoOrigem` e nao entram em nenhum numero. Com filtro de conta vale a flag daquela conta;
  sem filtro, a regra liga se qualquer conta ativa da empresa tiver a flag.

As contagens (leads CRM, MQL, oportunidade, contrato, MRR/projeto) vem de `funil.contar`: cada
etapa pela propria data no periodo. Leads e vendas usam os mesmos criterios da aba Fontes.

Arvore: campanha (gasto do insight de campanha, funil por opoMcgId) -> conjunto (soma dos
anuncios) -> anuncio (gasto do insight por anuncio, funil por opoManId). Um lead so conta no
anuncio quando o anuncio e da mesma campanha do lead; senao (anuncio nao resolvido ou campanha
manual diferente) conta so na campanha, ou em "campanha nao identificada" sem campanha.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import and_, case, false, func, not_, or_, select, true
from sqlalchemy.orm import Session

from ...exceptions import BadRequestError, NotFoundError
from ...models.meta_ads_anuncio import MetaAdsAnuncio
from ...models.meta_ads_campanha import MetaAdsCampanha
from ...models.meta_ads_conjunto import MetaAdsConjunto
from ...models.meta_ads_conta import MetaAdsConta
from ...models.meta_ads_conta_origem import MetaAdsContaOrigem
from ...models.meta_ads_insight_anuncio_diario import MetaAdsInsightAnuncioDiario
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
    MetaAdsRevisaoItem,
    MetaAdsSerieDia,
    OportunidadeCampanhaMetaResponse,
)
# Helper "privado" do dashboard reusado de proposito: e a garantia de que as regras
# de periodo sao exatamente as mesmas da aba Fontes.
from ..crm_dashboard_service import _between_dates, condicoes_periodo
from .funil import FunilLead, carregar_funil, contar
from .rastreio import tem_sinal_meta

NOME_NAO_IDENTIFICADA = "Meta — campanha não identificada"
GASTO_ZERO = {"investimento": 0.0, "impressoes": 0, "cliques": 0, "leadsMeta": 0}
FUNIL_ZERO = {
    "leadsCrm": 0, "mqls": 0, "oportunidades": 0, "contratos": 0,
    "mrr": 0.0, "projeto": 0.0, "horasPrimeiroContatoMedia": None,
}
_CHAVES_FUNIL = ("leadsCrm", "mqls", "oportunidades", "contratos", "mrr", "projeto")
LIMITE_REVISAO = 500


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
    """`leads` = leads reportados pela Meta (CPL do Gerenciador); `vendas` = contratos."""
    return {
        "ctr": round(cliques / impressoes * 100, 2) if impressoes else None,
        "cpc": _dividir(investimento, cliques),
        "cpl": _dividir(investimento, leads),
        "cac": _dividir(investimento, vendas),
        "retorno": _dividir(mrr * 12 + projeto, investimento),
    }


def _linha(
    nivel: str,
    id_: int | None,
    mcg_id: int | None,
    nome: str,
    status: str | None,
    mac_id: int | None,
    gasto: dict,
    funil: dict,
    filhos: list[MetaAdsLinha] | None = None,
) -> MetaAdsLinha:
    investimento = round(gasto["investimento"], 2)
    horas = funil["horasPrimeiroContatoMedia"]
    return MetaAdsLinha(
        nivel=nivel,
        id=id_,
        mcgId=mcg_id,
        nome=nome,
        status=status,
        macId=mac_id,
        investimento=investimento,
        impressoes=gasto["impressoes"],
        cliques=gasto["cliques"],
        leadsMeta=gasto["leadsMeta"],
        leadsCrm=funil["leadsCrm"],
        mqls=funil["mqls"],
        oportunidades=funil["oportunidades"],
        vendas=funil["contratos"],
        mrr=round(funil["mrr"], 2),
        projeto=round(funil["projeto"], 2),
        custoLeadCrm=_dividir(investimento, funil["leadsCrm"]),
        custoMql=_dividir(investimento, funil["mqls"]),
        custoOportunidade=_dividir(investimento, funil["oportunidades"]),
        horasPrimeiroContato=round(horas, 2) if horas is not None else None,
        filhos=filhos or [],
        **calcular_derivados(
            investimento=investimento,
            leads=gasto["leadsMeta"],
            vendas=funil["contratos"],
            mrr=funil["mrr"],
            projeto=funil["projeto"],
            impressoes=gasto["impressoes"],
            cliques=gasto["cliques"],
        ),
    )


def _tem_movimento(gasto: dict, funil: dict) -> bool:
    return bool(gasto["investimento"] or gasto["leadsMeta"] or any(funil[k] for k in _CHAVES_FUNIL))


def _somar_gasto(linhas: list[MetaAdsLinha]) -> dict:
    return {k: sum(getattr(l, k) for l in linhas) for k in GASTO_ZERO}


def _ordenar(linhas: list[MetaAdsLinha]) -> list[MetaAdsLinha]:
    linhas.sort(key=lambda l: (l.investimento, l.leadsCrm), reverse=True)
    return linhas


def tem_conta(db: Session, emp_id: int) -> bool:
    return (
        db.execute(
            select(MetaAdsConta.macId)
            .where(MetaAdsConta.macEmpId == emp_id, MetaAdsConta.macAtivo.is_(True))
            .limit(1)
        ).first()
        is not None
    )


def exige_rastreio(db: Session, emp_id: int, mac_id: int | None) -> bool:
    """Flag da conta filtrada; sem filtro, True se alguma conta ativa da empresa a tiver."""
    stmt = select(MetaAdsConta.macId).where(
        MetaAdsConta.macEmpId == emp_id,
        MetaAdsConta.macAtivo.is_(True),
        MetaAdsConta.macExigirRastreio.is_(True),
    )
    if mac_id is not None:
        stmt = stmt.where(MetaAdsConta.macId == mac_id)
    return db.execute(stmt.limit(1)).first() is not None


def _origens_meta(db: Session, emp_id: int, mac_id: int | None) -> list[int]:
    stmt = (
        select(MetaAdsContaOrigem.mcoCcoId)
        .join(MetaAdsConta, MetaAdsConta.macId == MetaAdsContaOrigem.mcoMacId)
        .where(MetaAdsConta.macEmpId == emp_id, MetaAdsConta.macAtivo.is_(True))
    )
    if mac_id is not None:
        stmt = stmt.where(MetaAdsConta.macId == mac_id)
    return sorted(set(db.execute(stmt).scalars()))


def _condicao_lead_meta(db: Session, emp_id: int, mac_id: int | None, exigir: bool = False):
    if mac_id is None:
        ligada = Oportunidade.opoMcgId.isnot(None)
    else:
        ligada = Oportunidade.opoMcgId.in_(
            select(MetaAdsCampanha.mcgId).where(MetaAdsCampanha.mcgMacId == mac_id)
        )
    origens = _origens_meta(db, emp_id, mac_id)
    da_origem = Oportunidade.opoCcoId.in_(origens) if origens else false()
    if not exigir:
        return or_(ligada, and_(Oportunidade.opoMcgId.is_(None), da_origem))
    if mac_id is None:
        da_conta = true()
    else:
        # Sem campanha nao ha conta certa: vale o anuncio resolvido da conta ou a origem dela.
        da_conta = or_(
            da_origem,
            Oportunidade.opoManId.in_(
                select(MetaAdsAnuncio.manId).where(MetaAdsAnuncio.manMacId == mac_id)
            ),
        )
    return or_(ligada, and_(Oportunidade.opoMcgId.is_(None), tem_sinal_meta, da_conta))


def _revisao_origem(db: Session, emp_id: int, filtro: FiltroPainel) -> list[MetaAdsRevisaoItem]:
    """Leads recebidos no periodo com origem mapeada como Meta e sem nenhum sinal da Meta."""
    origens = _origens_meta(db, emp_id, filtro.mac_id)
    if not origens:
        return []
    cond = condicoes_periodo(filtro.data_inicial, filtro.data_final)
    linhas = db.execute(
        select(
            Oportunidade.opoId,
            Oportunidade.opoTitulo,
            Oportunidade.opoNomeContato,
            Oportunidade.opoDataRecebimento,
        )
        .where(
            Oportunidade.opoEmpId == emp_id,
            cond.recebidas,
            Oportunidade.opoCcoId.in_(origens),
            not_(tem_sinal_meta),
        )
        .order_by(Oportunidade.opoDataRecebimento.desc(), Oportunidade.opoId.desc())
        .limit(LIMITE_REVISAO)
    ).all()
    return [
        MetaAdsRevisaoItem(
            opoId=r.opoId,
            opoTitulo=r.opoTitulo,
            opoNomeContato=r.opoNomeContato,
            opoDataRecebimento=r.opoDataRecebimento,
        )
        for r in linhas
    ]


def _somar_insights(db: Session, emp_id: int, filtro: FiltroPainel, chave, data, emp, mac, metricas) -> dict:
    """Soma (investimento, impressoes, cliques, leads Meta) por `chave` no periodo/conta do filtro."""
    inv, imp, cli, lm = metricas
    conds = [emp == emp_id]
    periodo = _between_dates(data, filtro.data_inicial, filtro.data_final)
    if periodo is not None:
        conds.append(periodo)
    if filtro.mac_id is not None:
        conds.append(mac == filtro.mac_id)
    stmt = (
        select(
            chave.label("chave"),
            func.coalesce(func.sum(inv), 0).label("inv"),
            func.coalesce(func.sum(imp), 0).label("imp"),
            func.coalesce(func.sum(cli), 0).label("cli"),
            func.coalesce(func.sum(lm), 0).label("lm"),
        )
        .where(*conds)
        .group_by(chave)
    )
    return {
        r.chave: {
            "investimento": float(r.inv),
            "impressoes": int(r.imp),
            "cliques": int(r.cli),
            "leadsMeta": int(r.lm),
        }
        for r in db.execute(stmt)
    }


def _gastos(db: Session, emp_id: int, filtro: FiltroPainel) -> dict[int, dict]:
    """Por campanha, do insight de campanha (conferido com o Gerenciador na fase 1)."""
    m = MetaAdsInsightDiario
    return _somar_insights(
        db, emp_id, filtro, m.midMcgId, m.midData, m.midEmpId, m.midMacId,
        (m.midInvestimento, m.midImpressoes, m.midCliques, m.midLeadsMeta),
    )


def _gastos_anuncios(db: Session, emp_id: int, filtro: FiltroPainel) -> dict[int, dict]:
    m = MetaAdsInsightAnuncioDiario
    return _somar_insights(
        db, emp_id, filtro, m.miaManId, m.miaData, m.miaEmpId, m.miaMacId,
        (m.miaInvestimento, m.miaImpressoes, m.miaCliques, m.miaLeadsMeta),
    )


def _ids_com_anuncio(db: Session, emp_id: int, condicao, filtro: FiltroPainel) -> set[int]:
    """Leads Meta recebidos no periodo com o id do anuncio (base da cobertura de rastreio)."""
    cond = condicoes_periodo(filtro.data_inicial, filtro.data_final)
    return set(
        db.execute(
            select(Oportunidade.opoId).where(
                Oportunidade.opoEmpId == emp_id,
                condicao,
                cond.recebidas,
                Oportunidade.opoMetaAnuncioId.isnot(None),
            )
        ).scalars()
    )


def _recebido_no_periodo(lead: FunilLead, filtro: FiltroPainel) -> bool:
    dia = lead.recebido
    if dia is None:
        return False
    return (filtro.data_inicial is None or dia >= filtro.data_inicial) and (
        filtro.data_final is None or dia <= filtro.data_final
    )


def _por_id(db: Session, modelo, coluna_id, ids: set[int], *conds) -> dict:
    if not ids:
        return {}
    stmt = select(modelo).where(coluna_id.in_(ids), *conds)
    return {getattr(o, coluna_id.key): o for o in db.execute(stmt).scalars()}


@dataclass
class CalculoPainel:
    """Resultado do painel mais os insumos para recortes (ex.: serie por intervalo)."""

    resposta: MetaAdsPainelResponse
    leads_total: list[FunilLead]
    campanhas_incluidas: set[int]
    # Campanhas cujas linhas compoem o gasto do total (as com movimento ou filhos).
    campanhas_com_linha: set[int] = field(default_factory=set)


def painel(db: Session, emp_id: int, filtro: FiltroPainel) -> MetaAdsPainelResponse:
    return calcular_painel(db, emp_id, filtro).resposta


def calcular_painel(db: Session, emp_id: int, filtro: FiltroPainel) -> CalculoPainel:
    ini, fim = filtro.data_inicial, filtro.data_final
    exigir = exige_rastreio(db, emp_id, filtro.mac_id)
    condicao = _condicao_lead_meta(db, emp_id, filtro.mac_id, exigir)
    leads = carregar_funil(db, emp_id, condicao)
    gastos = _gastos(db, emp_id, filtro)
    gastos_anuncio = _gastos_anuncios(db, emp_id, filtro)

    conds_anuncio = [MetaAdsAnuncio.manEmpId == emp_id]
    if filtro.mac_id is not None:
        conds_anuncio.append(MetaAdsAnuncio.manMacId == filtro.mac_id)
    anuncios: dict[int, MetaAdsAnuncio] = _por_id(
        db,
        MetaAdsAnuncio,
        MetaAdsAnuncio.manId,
        set(gastos_anuncio) | {l.man_id for l in leads if l.man_id is not None},
        *conds_anuncio,
    )

    def anuncio_do_lead(lead: FunilLead) -> MetaAdsAnuncio | None:
        anuncio = anuncios.get(lead.man_id) if lead.man_id is not None else None
        if anuncio is None or lead.mcg_id is None or anuncio.manMcgId != lead.mcg_id:
            return None
        return anuncio

    por_campanha = contar(leads, ini, fim, lambda l: l.mcg_id)
    por_anuncio = contar(leads, ini, fim, lambda l: getattr(anuncio_do_lead(l), "manId", None))
    por_conjunto = contar(leads, ini, fim, lambda l: getattr(anuncio_do_lead(l), "manMcjId", None))

    # Anuncios agrupados por conjunto; o conjunto soma o gasto dos seus anuncios.
    anuncios_por_conjunto: dict[int, list[MetaAdsLinha]] = {}
    for a in anuncios.values():
        gasto = gastos_anuncio.get(a.manId, GASTO_ZERO)
        fun = por_anuncio.get(a.manId, FUNIL_ZERO)
        if _tem_movimento(gasto, fun):
            anuncios_por_conjunto.setdefault(a.manMcjId, []).append(
                _linha("anuncio", a.manId, a.manMcgId, a.manNome, a.manStatus, a.manMacId, gasto, fun)
            )
    conjuntos: dict[int, MetaAdsConjunto] = _por_id(
        db, MetaAdsConjunto, MetaAdsConjunto.mcjId, set(anuncios_por_conjunto),
        MetaAdsConjunto.mcjEmpId == emp_id,
    )
    conjuntos_por_campanha: dict[int, list[MetaAdsLinha]] = {}
    for mcj_id, filhos in anuncios_por_conjunto.items():
        conj = conjuntos.get(mcj_id)
        if conj is None:
            continue
        conjuntos_por_campanha.setdefault(conj.mcjMcgId, []).append(
            _linha(
                "conjunto", mcj_id, conj.mcjMcgId, conj.mcjNome, conj.mcjStatus, conj.mcjMacId,
                _somar_gasto(filhos), por_conjunto.get(mcj_id, FUNIL_ZERO), _ordenar(filhos),
            )
        )

    mcg_ids = {i for i in set(gastos) | set(por_campanha) if i is not None}
    mcg_ids |= {a.manMcgId for a in anuncios.values()}
    conds_campanha = [MetaAdsCampanha.mcgEmpId == emp_id]
    if filtro.mac_id is not None:
        conds_campanha.append(MetaAdsCampanha.mcgMacId == filtro.mac_id)
    campanhas: dict[int, MetaAdsCampanha] = _por_id(
        db, MetaAdsCampanha, MetaAdsCampanha.mcgId, mcg_ids, *conds_campanha
    )
    incluidas: set[int] = set()
    linhas: list[MetaAdsLinha] = []
    for mcg_id, camp in campanhas.items():
        if filtro.somente_ativas and camp.mcgStatus != "ACTIVE":
            continue
        incluidas.add(mcg_id)
        gasto = gastos.get(mcg_id, GASTO_ZERO)
        fun = por_campanha.get(mcg_id, FUNIL_ZERO)
        filhos = _ordenar(conjuntos_por_campanha.get(mcg_id, []))
        if _tem_movimento(gasto, fun) or filhos:
            linhas.append(
                _linha("campanha", mcg_id, mcg_id, camp.mcgNome, camp.mcgStatus, camp.mcgMacId, gasto, fun, filhos)
            )
    _ordenar(linhas)

    nao_identificada = None
    fun_sem_campanha = por_campanha.get(None, FUNIL_ZERO)
    if _tem_movimento(GASTO_ZERO, fun_sem_campanha):
        nao_identificada = _linha(
            "nao_identificada", None, None, NOME_NAO_IDENTIFICADA, None, None, GASTO_ZERO, fun_sem_campanha
        )

    # Total: gasto das campanhas mostradas + funil dos seus leads (e dos sem campanha),
    # recontado para a media de horas ate o primeiro contato sair certa.
    no_total = [l for l in leads if l.mcg_id is None or l.mcg_id in incluidas]
    fun_total = contar(no_total, ini, fim, lambda _l: 0).get(0, FUNIL_ZERO)
    total = _linha("total", None, None, "Total", None, None, _somar_gasto(linhas), fun_total)

    cobertura = None
    if fun_total["leadsCrm"]:
        com_anuncio = _ids_com_anuncio(db, emp_id, condicao, filtro)
        rastreados = sum(
            1 for l in no_total if l.opo_id in com_anuncio and _recebido_no_periodo(l, filtro)
        )
        cobertura = round(rastreados / fun_total["leadsCrm"] * 100, 2)

    resposta = MetaAdsPainelResponse(
        temConta=tem_conta(db, emp_id),
        total=total,
        campanhas=linhas,
        naoIdentificada=nao_identificada,
        cobertura=cobertura,
        revisaoOrigem=_revisao_origem(db, emp_id, filtro) if exigir else [],
    )
    return CalculoPainel(resposta=resposta, leads_total=no_total, campanhas_incluidas=incluidas,
        campanhas_com_linha={l.mcgId for l in linhas},
    )


def serie_por_intervalo(
    db: Session,
    emp_id: int,
    filtro: FiltroPainel,
    calculo: CalculoPainel,
    faixas: list[tuple[date, date]],
) -> list[dict]:
    """Um dict por faixa com as mesmas contas do total do painel (a soma das faixas e o total).

    Gasto: insights diarios das campanhas incluidas no total, cada dia na sua faixa.
    Funil: `contar` sobre os leads do total, cada etapa pela propria data dentro da faixa.
    """
    gasto_faixas = [dict(GASTO_ZERO) for _ in faixas]
    incluidas = calculo.campanhas_com_linha  # mesmo conjunto que `_somar_gasto(linhas)` do total
    if incluidas:
        m = MetaAdsInsightDiario
        conds = [m.midEmpId == emp_id, m.midMcgId.in_(incluidas)]
        periodo = _between_dates(m.midData, filtro.data_inicial, filtro.data_final)
        if periodo is not None:
            conds.append(periodo)
        if filtro.mac_id is not None:
            conds.append(m.midMacId == filtro.mac_id)
        stmt = (
            select(
                m.midData.label("dia"),
                func.coalesce(func.sum(m.midInvestimento), 0).label("inv"),
                func.coalesce(func.sum(m.midImpressoes), 0).label("imp"),
                func.coalesce(func.sum(m.midCliques), 0).label("cli"),
                func.coalesce(func.sum(m.midLeadsMeta), 0).label("lm"),
            )
            .where(*conds)
            .group_by(m.midData)
        )
        for r in db.execute(stmt):
            dia = r.dia.date() if hasattr(r.dia, "date") else r.dia
            for (ini, fim), gasto in zip(faixas, gasto_faixas):
                if ini <= dia <= fim:
                    gasto["investimento"] += float(r.inv)
                    gasto["impressoes"] += int(r.imp)
                    gasto["cliques"] += int(r.cli)
                    gasto["leadsMeta"] += int(r.lm)
                    break

    serie: list[dict] = []
    for (ini, fim), gasto in zip(faixas, gasto_faixas):
        fun = contar(calculo.leads_total, ini, fim, lambda _l: 0).get(0, FUNIL_ZERO)
        serie.append({
            "investimento": round(gasto["investimento"], 2),
            "impressoes": gasto["impressoes"],
            "cliques": gasto["cliques"],
            "leadsMeta": gasto["leadsMeta"],
            "leadsCrm": fun["leadsCrm"],
            "mqls": fun["mqls"],
            "oportunidades": fun["oportunidades"],
            "vendas": fun["contratos"],
        })
    return serie


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
        _linha("campanha", mcg_id, mcg_id, camp.mcgNome, camp.mcgStatus, camp.mcgMacId, GASTO_ZERO, FUNIL_ZERO),
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
