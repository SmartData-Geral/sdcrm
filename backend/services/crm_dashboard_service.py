from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import Integer, and_, case, func, literal, or_, select, true
from sqlalchemy.orm import Session

from ..models.como_conheceu import ComoConheceu
from ..models.crm_meta_mensal import CrmMetaMensal
from ..models.etapa_kanban import EtapaKanban
from ..models.motivo_cancelamento import MotivoCancelamento
from ..models.oportunidade import Oportunidade
from ..models.produto import Produto
from ..models.usuario import Usuario
from ..schemas.crm_dashboard import (
    CrmDashboardCards,
    CrmDashboardFiltroParams,
    CrmDashboardGraficoAtivasPorResponsavelItem,
    CrmDashboardGraficoPorFonteItem,
    CrmDashboardGraficoPorMesItem,
    CrmDashboardGraficoPorSolucaoItem,
    CrmDashboardGraficosResponse,
    CrmDashboardMotivoPerdaItem,
    CrmDashboardOportunidadeResumoItem,
    CrmDashboardOportunidadesFiltroParams,
    CrmDashboardOportunidadesListResponse,
    CrmDashboardOportunidadesResumo,
    CrmDashboardRankingFonteItem,
    CrmDashboardRankingResponsavelItem,
    CrmDashboardRankingSolucaoItem,
    CrmDashboardRankingsResponse,
    CrmDashboardResumoMetaLinha,
    CrmDashboardResumoMetas,
    CrmDashboardResponse,
    CrmDashboardSerieMensalItem,
)


def _forecast_temperature_multiplier(temperatura: str | None) -> float:
    value = (temperatura or "").strip().lower()
    if value == "quente":
        return 0.75
    if value == "morno":
        return 0.50
    if value == "frio":
        return 0.25
    return 0.0


def _forecast_score_multiplier(score: int | None) -> float:
    if score is None:
        return 0.0
    normalized_score = max(0, min(score, 10))
    return normalized_score / 10


def _calculate_forecast_value(
    valor_oportunidade: float | None,
    temperatura: str | None,
    lead_score: int | None,
) -> float:
    if valor_oportunidade is None or valor_oportunidade <= 0:
        return 0.0
    return (
        float(valor_oportunidade)
        * _forecast_temperature_multiplier(temperatura)
        * _forecast_score_multiplier(lead_score)
    )


def _build_status_filter(status: str | None):
    if status is None or status == "todas":
        return None
    if status == "ganhas":
        return Oportunidade.opoStatusFechamento == "ganho"
    if status == "perdidas":
        return Oportunidade.opoStatusFechamento == "perdido"
    if status == "ativas":
        return Oportunidade.opoStatusFechamento.is_(None)
    return None


def _meta_mes_referencia_conditions(filtros: CrmDashboardFiltroParams) -> list:
    """Filtra metas mensais cujo mês de referência (sempre dia 1) intersecta o período do dashboard."""
    conds = []
    if filtros.data_inicial is not None:
        inicio = date(filtros.data_inicial.year, filtros.data_inicial.month, 1)
        conds.append(CrmMetaMensal.cmmMesReferencia >= inicio)
    if filtros.data_final is not None:
        fim = date(filtros.data_final.year, filtros.data_final.month, 1)
        conds.append(CrmMetaMensal.cmmMesReferencia <= fim)
    return conds


def _meta_valor_efetivo(valor: float | int | None) -> float | None:
    if valor is None:
        return None
    v = float(valor)
    return None if v == 0.0 else v


def _resumo_meta_linha(meta_soma: float | int | None, realizado: float | int) -> CrmDashboardResumoMetaLinha:
    meta = _meta_valor_efetivo(meta_soma)
    real = float(realizado)
    if meta is None:
        return CrmDashboardResumoMetaLinha(meta=None, realizado=real, percentual=None, gap=None)
    pct = round((real / meta) * 100, 2)
    gap = round(real - meta, 2)
    return CrmDashboardResumoMetaLinha(meta=meta, realizado=real, percentual=pct, gap=gap)


def _build_motivos_perda_filters(
    company_id: Optional[int],
    filtros: CrmDashboardFiltroParams,
) -> list:
    """Filtros para perdas: empresa, responsável, período (sem filtro de status do dashboard).

    Data de referência alinhada aos agregados de perdidas do dashboard: coalesce(fechamento, recebimento).
    """
    conditions: list = []
    if company_id is not None:
        conditions.append(Oportunidade.opoEmpId == company_id)
    if filtros.responsavel_id is not None:
        conditions.append(Oportunidade.opoUsuResponsavelId == filtros.responsavel_id)
    data_ref_perdida = func.coalesce(
        Oportunidade.opoDataFechamento,
        Oportunidade.opoDataRecebimento,
    )
    periodo = _between_dates(
        data_ref_perdida,
        filtros.data_inicial,
        filtros.data_final,
    )
    if periodo is not None:
        conditions.append(periodo)
    conditions.append(Oportunidade.opoStatusFechamento == "perdido")
    conditions.append(Oportunidade.opoAtivo.is_(True))
    conditions.append(data_ref_perdida.is_not(None))
    return conditions


def _mrr_perdido_expr():
    """Valor alinhado ao MRR incremental (exclui projeto e receita pontual)."""
    return case(
        (
            and_(
                func.coalesce(Oportunidade.opoFechadoRecorrencia, 0) != 1,
                Oportunidade.opoReceitaPontual.is_(False),
            ),
            func.coalesce(Oportunidade.opoValorOportunidade, 0),
        ),
        else_=0,
    )


def _query_metas_e_resumo(
    db: Session,
    company_id: Optional[int],
    filtros: CrmDashboardFiltroParams,
    cards: CrmDashboardCards,
) -> tuple[bool, CrmDashboardResumoMetas]:
    # Sem X-Company-Id (modo single-tenant / MULTIEMPRESA off), os cards não filtram empresa —
    # metas seguem o mesmo critério (todas as linhas de crm_meta_mensal, respeitando só o período).
    meta_conds: list = []
    if company_id is not None:
        meta_conds.append(CrmMetaMensal.cmmEmpId == company_id)
    meta_conds.extend(_meta_mes_referencia_conditions(filtros))

    stmt = select(
        func.count(CrmMetaMensal.cmmId).label("n_metas"),
        func.coalesce(func.sum(CrmMetaMensal.cmmQtdRecebimento), 0).label("meta_rec"),
        func.coalesce(func.sum(CrmMetaMensal.cmmQtdFechamento), 0).label("meta_fec"),
        func.coalesce(func.sum(CrmMetaMensal.cmmMrrIncremental), 0).label("meta_mrr"),
    )
    if meta_conds:
        stmt = stmt.where(*meta_conds)
    row = db.execute(stmt).first()
    n_metas = int(row.n_metas) if row is not None else 0  # type: ignore[attr-defined]
    tem_meta = n_metas > 0
    meta_rec = float(row.meta_rec) if row is not None else 0.0  # type: ignore[attr-defined]
    meta_fec = float(row.meta_fec) if row is not None else 0.0  # type: ignore[attr-defined]
    meta_mrr = float(row.meta_mrr) if row is not None else 0.0  # type: ignore[attr-defined]

    resumo = CrmDashboardResumoMetas(
        recebimento=_resumo_meta_linha(meta_rec if tem_meta else None, cards.recebidas),
        fechamento=_resumo_meta_linha(meta_fec if tem_meta else None, cards.ganhas),
        mrrIncremental=_resumo_meta_linha(meta_mrr if tem_meta else None, cards.mrrIncremental),
    )
    return tem_meta, resumo


def _query_motivos_perda(
    db: Session,
    company_id: Optional[int],
    filtros: CrmDashboardFiltroParams,
) -> list[CrmDashboardMotivoPerdaItem]:
    conditions = _build_motivos_perda_filters(company_id, filtros)
    mrr_col = _mrr_perdido_expr()
    join_motivo = Oportunidade.opoMcaId == MotivoCancelamento.mcaId
    if company_id is not None:
        join_motivo = and_(join_motivo, MotivoCancelamento.mcaEmpId == company_id)
    motivo_grupo = func.coalesce(MotivoCancelamento.mcaNome, "Não informado")
    stmt = (
        select(
            motivo_grupo.label("motivo"),
            func.count(Oportunidade.opoId).label("qtd"),
            func.coalesce(func.sum(mrr_col), 0).label("mrr"),
        )
        .select_from(Oportunidade)
        .outerjoin(MotivoCancelamento, join_motivo)
        .where(*conditions)
        .group_by(motivo_grupo)
    )
    rows = db.execute(stmt).all()
    if not rows:
        return []
    total_qtd = sum(int(r.qtd) for r in rows)  # type: ignore[attr-defined]
    total_mrr = sum(float(r.mrr) for r in rows)  # type: ignore[attr-defined]
    items: list[CrmDashboardMotivoPerdaItem] = []
    # Ordenação alinhada ao que o gráfico destaca (quantidade); MRR só desempata.
    for r in sorted(
        rows,
        key=lambda x: (int(x.qtd), float(x.mrr)),  # type: ignore[attr-defined]
        reverse=True,
    ):
        q = int(r.qtd)  # type: ignore[attr-defined]
        mrr = float(r.mrr)  # type: ignore[attr-defined]
        pct_q = round((q / total_qtd) * 100, 2) if total_qtd > 0 else 0.0
        pct_m = round((mrr / total_mrr) * 100, 2) if total_mrr > 0 else 0.0
        items.append(
            CrmDashboardMotivoPerdaItem(
                motivo=r.motivo,
                quantidade=q,
                percentualQuantidade=pct_q,
                mrrPerdido=round(mrr, 2),
                percentualMrr=pct_m,
            )
        )
    return items


def _between_dates(column, data_inicial: Optional[date], data_final: Optional[date]):
    conditions = []
    if data_inicial is not None:
        conditions.append(column >= data_inicial)
    if data_final is not None:
        conditions.append(column <= data_final)
    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return and_(*conditions)


def _last_day_of_month(first_day: date) -> date:
    if first_day.month == 12:
        nxt = date(first_day.year + 1, 1, 1)
    else:
        nxt = date(first_day.year, first_day.month + 1, 1)
    return nxt - timedelta(days=1)


def _serie_mensal_month_slots(filtros: CrmDashboardFiltroParams) -> list[tuple[str, str, date, date]]:
    """Meses contínuos no intervalo (ou últimos 12 meses): (periodo YYYY-MM, label mm/aa, 1º dia, último dia).

    Quando ``filtros.serie_anos`` está preenchido, retorna jan–dez de cada ano (ignora data_inicial/data_final).
    """
    if filtros.serie_anos:
        years = sorted({int(y) for y in filtros.serie_anos if y is not None})
        slots: list[tuple[str, str, date, date]] = []
        for y in years:
            for m in range(1, 13):
                first = date(y, m, 1)
                periodo = f"{y:04d}-{m:02d}"
                label = f"{m:02d}/{str(y)[2:]}"
                slots.append((periodo, label, first, _last_day_of_month(first)))
        return slots
    today = date.today()
    primeiro_mes_corrente = today.replace(day=1)
    if filtros.data_inicial is None and filtros.data_final is None:
        ano_12m = primeiro_mes_corrente.year
        mes_12m = primeiro_mes_corrente.month - 11
        while mes_12m <= 0:
            mes_12m += 12
            ano_12m -= 1
        start = date(ano_12m, mes_12m, 1)
        end_month = primeiro_mes_corrente
    else:
        di = filtros.data_inicial or filtros.data_final or today
        df = filtros.data_final or filtros.data_inicial or today
        start = date(di.year, di.month, 1)
        end_month = date(df.year, df.month, 1)
        if start > end_month:
            start, end_month = end_month, start
    slots: list[tuple[str, str, date, date]] = []
    cur = start
    while cur <= end_month:
        periodo = f"{cur.year:04d}-{cur.month:02d}"
        label = f"{cur.month:02d}/{str(cur.year)[2:]}"
        slots.append((periodo, label, cur, _last_day_of_month(cur)))
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return slots


def _build_serie_mensal_emp_resp_filters(company_id: Optional[int], responsavel_id: Optional[int]) -> list:
    conds: list = []
    if company_id is not None:
        conds.append(Oportunidade.opoEmpId == company_id)
    if responsavel_id is not None:
        conds.append(Oportunidade.opoUsuResponsavelId == responsavel_id)
    return conds


def _mrr_incremental_expr():
    return case(
        (
            and_(
                Oportunidade.opoStatusFechamento == "ganho",
                func.coalesce(Oportunidade.opoFechadoRecorrencia, 0) != 1,
                Oportunidade.opoReceitaPontual.is_(False),
            ),
            func.coalesce(Oportunidade.opoValorFechado, 0),
        ),
        else_=0,
    )


def _query_serie_mensal(
    db: Session,
    company_id: Optional[int],
    filtros: CrmDashboardFiltroParams,
) -> list[CrmDashboardSerieMensalItem]:
    slots = _serie_mensal_month_slots(filtros)
    if not slots:
        return []
    global_start = slots[0][2]
    global_end = slots[-1][3]
    base = _build_serie_mensal_emp_resp_filters(company_id, filtros.responsavel_id)
    date_rec = _between_dates(Oportunidade.opoDataRecebimento, global_start, global_end)
    date_fec = _between_dates(Oportunidade.opoDataFechamento, global_start, global_end)
    data_perdida = func.coalesce(Oportunidade.opoDataFechamento, Oportunidade.opoDataRecebimento)
    date_perd = _between_dates(data_perdida, global_start, global_end)

    def _periodo_key(ano: int, mes: int) -> str:
        return f"{int(ano):04d}-{int(mes):02d}"

    # --- Recebidas (mês da data de recebimento)
    cond_rec = [*base, Oportunidade.opoAtivo.is_(True), Oportunidade.opoDataRecebimento.is_not(None)]
    if date_rec is not None:
        cond_rec.append(date_rec)
    y_rec = func.cast(func.extract("year", Oportunidade.opoDataRecebimento), Integer)
    m_rec = func.cast(func.extract("month", Oportunidade.opoDataRecebimento), Integer)
    stmt_rec = (
        select(y_rec.label("ano"), m_rec.label("mes"), func.count(Oportunidade.opoId).label("qtd"))
        .where(*cond_rec)
        .group_by(y_rec, m_rec)
    )
    by_rec: dict[str, int] = {}
    for row in db.execute(stmt_rec).all():
        by_rec[_periodo_key(row.ano, row.mes)] = int(row.qtd)  # type: ignore[attr-defined]

    # --- Ganhas + MRR incremental (mês da data de fechamento)
    cond_g = [
        *base,
        Oportunidade.opoAtivo.is_(True),
        Oportunidade.opoStatusFechamento == "ganho",
        Oportunidade.opoDataFechamento.is_not(None),
    ]
    if date_fec is not None:
        cond_g.append(date_fec)
    y_g = func.cast(func.extract("year", Oportunidade.opoDataFechamento), Integer)
    m_g = func.cast(func.extract("month", Oportunidade.opoDataFechamento), Integer)
    mrr_x = _mrr_incremental_expr()
    stmt_g = (
        select(
            y_g.label("ano"),
            m_g.label("mes"),
            func.count(Oportunidade.opoId).label("qtd"),
            func.coalesce(func.sum(mrr_x), 0).label("mrr"),
        )
        .where(*cond_g)
        .group_by(y_g, m_g)
    )
    by_gan: dict[str, int] = {}
    by_mrr: dict[str, float] = {}
    for row in db.execute(stmt_g).all():
        k = _periodo_key(row.ano, row.mes)  # type: ignore[attr-defined]
        by_gan[k] = int(row.qtd)  # type: ignore[attr-defined]
        by_mrr[k] = float(row.mrr)  # type: ignore[attr-defined]

    # --- Perdidas (mês da referência coalesce fechamento/recebimento)
    cond_p = [*base, Oportunidade.opoAtivo.is_(True), Oportunidade.opoStatusFechamento == "perdido", data_perdida.is_not(None)]
    if date_perd is not None:
        cond_p.append(date_perd)
    y_p = func.cast(func.extract("year", data_perdida), Integer)
    m_p = func.cast(func.extract("month", data_perdida), Integer)
    stmt_p = (
        select(y_p.label("ano"), m_p.label("mes"), func.count(Oportunidade.opoId).label("qtd"))
        .where(*cond_p)
        .group_by(y_p, m_p)
    )
    by_perd: dict[str, int] = {}
    for row in db.execute(stmt_p).all():
        by_perd[_periodo_key(row.ano, row.mes)] = int(row.qtd)  # type: ignore[attr-defined]

    # --- Ativas (snapshot fim de mês): uma leitura, agregação em memória
    cond_atv = [
        *base,
        Oportunidade.opoAtivo.is_(True),
        Oportunidade.opoStatusFechamento.is_(None),
        Oportunidade.opoDataRecebimento.is_not(None),
        Oportunidade.opoDataRecebimento <= global_end,
    ]
    atv_rows = db.execute(
        select(Oportunidade.opoDataRecebimento, Oportunidade.opoDataFechamento).where(*cond_atv),
    ).all()
    by_atv: dict[str, int] = {}
    for periodo, _lbl, _first, last in slots:
        n = 0
        for rec_d, fec_d in atv_rows:
            if rec_d <= last and (fec_d is None or fec_d > last):
                n += 1
        by_atv[periodo] = n

    # --- Metas cadastradas por mês (interseção: janela da série + filtro explícito de meses, se houver)
    by_meta: dict[str, tuple[int, int, float]] = {}
    meta_conds: list = []
    if company_id is not None:
        meta_conds.append(CrmMetaMensal.cmmEmpId == company_id)
    meta_ref_ini = date(global_start.year, global_start.month, 1)
    meta_ref_fim = date(global_end.year, global_end.month, 1)
    meta_conds.append(CrmMetaMensal.cmmMesReferencia >= meta_ref_ini)
    meta_conds.append(CrmMetaMensal.cmmMesReferencia <= meta_ref_fim)
    if not filtros.serie_anos:
        meta_conds.extend(_meta_mes_referencia_conditions(filtros))
    mstmt = select(
        CrmMetaMensal.cmmMesReferencia,
        CrmMetaMensal.cmmQtdRecebimento,
        CrmMetaMensal.cmmQtdFechamento,
        CrmMetaMensal.cmmMrrIncremental,
    ).where(*meta_conds)
    for r in db.execute(mstmt).all():
        d = r.cmmMesReferencia
        pk = f"{d.year:04d}-{d.month:02d}"
        by_meta[pk] = (int(r.cmmQtdRecebimento), int(r.cmmQtdFechamento), float(r.cmmMrrIncremental))  # type: ignore[attr-defined]

    out: list[CrmDashboardSerieMensalItem] = []
    for periodo, label, _first, _last in slots:
        rec = by_rec.get(periodo, 0)
        gan = by_gan.get(periodo, 0)
        perd = by_perd.get(periodo, 0)
        mrr_inc = round(float(by_mrr.get(periodo, 0.0)), 2)
        fechadas_mes = gan + perd
        taxa = round((gan / fechadas_mes) * 100, 2) if fechadas_mes > 0 else 0.0
        mrr_medio = round(mrr_inc / gan, 2) if gan > 0 else 0.0
        taxa_ratio = (gan / fechadas_mes) if fechadas_mes > 0 else 0.0
        atv_m = by_atv.get(periodo, 0)
        forecast = round(float(atv_m) * taxa_ratio * mrr_medio, 2)

        meta_t = by_meta.get(periodo)
        meta_rec = None
        meta_g = None
        meta_m = None
        if meta_t is not None:
            if meta_t[0] != 0:
                meta_rec = float(meta_t[0])
            if meta_t[1] != 0:
                meta_g = float(meta_t[1])
            if float(meta_t[2]) != 0.0:
                meta_m = float(meta_t[2])

        out.append(
            CrmDashboardSerieMensalItem(
                periodo=periodo,
                label=label,
                recebidas=rec,
                ganhas=gan,
                perdidas=perd,
                taxaConversao=taxa,
                mrrIncremental=mrr_inc,
                mrrMedio=mrr_medio,
                forecast=forecast,
                metaRecebidas=meta_rec,
                metaGanhas=meta_g,
                metaMrr=meta_m,
            )
        )
    return out


def _build_base_filters(
    company_id: Optional[int],
    filtros: CrmDashboardFiltroParams,
):
    conditions = []
    if company_id is not None:
        conditions.append(Oportunidade.opoEmpId == company_id)
    if filtros.responsavel_id is not None:
        conditions.append(Oportunidade.opoUsuResponsavelId == filtros.responsavel_id)
    status_filter = _build_status_filter(filtros.status)
    if status_filter is not None:
        conditions.append(status_filter)
    return conditions


def _query_cards(
    db: Session,
    company_id: Optional[int],
    filtros: CrmDashboardFiltroParams,
) -> CrmDashboardCards:
    base_conditions = _build_base_filters(company_id, filtros)

    today = date.today()
    primeiro_dia_mes_corrente = today.replace(day=1)
    inicio_ultimos_7_dias = today - timedelta(days=6)
    if primeiro_dia_mes_corrente.month == 1:
        primeiro_dia_mes_anterior = primeiro_dia_mes_corrente.replace(year=primeiro_dia_mes_corrente.year - 1, month=12)
    else:
        primeiro_dia_mes_anterior = primeiro_dia_mes_corrente.replace(month=primeiro_dia_mes_corrente.month - 1)
    # primeiro dia daqui a 1 mês
    if primeiro_dia_mes_corrente.month == 12:
        primeiro_dia_proximo_mes = primeiro_dia_mes_corrente.replace(year=primeiro_dia_mes_corrente.year + 1, month=1)
    else:
        primeiro_dia_proximo_mes = primeiro_dia_mes_corrente.replace(month=primeiro_dia_mes_corrente.month + 1)
    # janela de 12 meses (incluindo mês corrente)
    ano_12m = primeiro_dia_mes_corrente.year
    mes_12m = primeiro_dia_mes_corrente.month - 11
    while mes_12m <= 0:
        mes_12m += 12
        ano_12m -= 1
    primeiro_dia_12m = primeiro_dia_mes_corrente.replace(year=ano_12m, month=mes_12m)

    # Recebidas: base em opoDataRecebimento
    recebidas_conditions = list(base_conditions)
    recebidas_periodo = _between_dates(
        Oportunidade.opoDataRecebimento,
        filtros.data_inicial,
        filtros.data_final,
    )
    if recebidas_periodo is not None:
        recebidas_conditions.append(recebidas_periodo)

    recebidas_stmt = select(func.count(Oportunidade.opoId)).where(
        *recebidas_conditions,
        Oportunidade.opoAtivo.is_(True),
    )
    recebidas_total = db.scalar(recebidas_stmt) or 0

    # recebidas 12m / último mês / mês corrente (sempre por data de recebimento)
    recebidas_periodos_stmt = (
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Oportunidade.opoDataRecebimento >= primeiro_dia_12m,
                                Oportunidade.opoDataRecebimento < primeiro_dia_proximo_mes,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_12m"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Oportunidade.opoDataRecebimento >= primeiro_dia_mes_anterior,
                                Oportunidade.opoDataRecebimento < primeiro_dia_mes_corrente,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_ultimo_mes"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Oportunidade.opoDataRecebimento >= primeiro_dia_mes_corrente,
                                Oportunidade.opoDataRecebimento < primeiro_dia_proximo_mes,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_mes_corrente"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Oportunidade.opoDataRecebimento >= inicio_ultimos_7_dias,
                                Oportunidade.opoDataRecebimento <= today,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_ultimos_7_dias"),
        )
        .where(
            *[
                c
                for c in base_conditions
            ],
            Oportunidade.opoAtivo.is_(True),
            Oportunidade.opoDataRecebimento.is_not(None),
        )
    )
    recebidas_periodos = db.execute(recebidas_periodos_stmt).first()
    recebidas_12m = int(recebidas_periodos.total_12m) if recebidas_periodos is not None else 0  # type: ignore[attr-defined]
    recebidas_ultimo_mes = int(recebidas_periodos.total_ultimo_mes) if recebidas_periodos is not None else 0  # type: ignore[attr-defined]
    recebidas_mes_corrente = int(recebidas_periodos.total_mes_corrente) if recebidas_periodos is not None else 0  # type: ignore[attr-defined]
    recebidas_ultimos_7_dias = int(recebidas_periodos.total_ultimos_7_dias) if recebidas_periodos is not None else 0  # type: ignore[attr-defined]

    # Ganhas / Perdidas / MRR: oportunidades fechadas no período (data fechamento)
    fechadas_conditions = _build_base_filters(company_id, filtros)
    fechadas_periodo = _between_dates(
        Oportunidade.opoDataFechamento,
        filtros.data_inicial,
        filtros.data_final,
    )
    if fechadas_periodo is not None:
        fechadas_conditions.append(fechadas_periodo)

    ganhas_stmt = select(func.count(Oportunidade.opoId)).where(
        *fechadas_conditions,
        Oportunidade.opoStatusFechamento == "ganho",
        Oportunidade.opoAtivo.is_(True),
    )
    ganhas_total = db.scalar(ganhas_stmt) or 0

    perdidas_stmt = select(func.count(Oportunidade.opoId)).where(
        *fechadas_conditions,
        Oportunidade.opoStatusFechamento == "perdido",
        Oportunidade.opoAtivo.is_(True),
    )
    perdidas_total = db.scalar(perdidas_stmt) or 0

    # Ganhas 12m / último mês / mês corrente (por data de fechamento)
    ganhas_periodos_stmt = (
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Oportunidade.opoDataFechamento >= primeiro_dia_12m,
                                Oportunidade.opoDataFechamento < primeiro_dia_proximo_mes,
                                Oportunidade.opoStatusFechamento == "ganho",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_12m"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Oportunidade.opoDataFechamento >= primeiro_dia_mes_anterior,
                                Oportunidade.opoDataFechamento < primeiro_dia_mes_corrente,
                                Oportunidade.opoStatusFechamento == "ganho",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_ultimo_mes"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Oportunidade.opoDataFechamento >= primeiro_dia_mes_corrente,
                                Oportunidade.opoDataFechamento < primeiro_dia_proximo_mes,
                                Oportunidade.opoStatusFechamento == "ganho",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_mes_corrente"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Oportunidade.opoDataFechamento >= inicio_ultimos_7_dias,
                                Oportunidade.opoDataFechamento <= today,
                                Oportunidade.opoStatusFechamento == "ganho",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_ultimos_7_dias"),
        )
        .where(
            *fechadas_conditions,
            Oportunidade.opoAtivo.is_(True),
            Oportunidade.opoDataFechamento.is_not(None),
        )
    )
    ganhas_periodos = db.execute(ganhas_periodos_stmt).first()
    ganhas_12m = int(ganhas_periodos.total_12m) if ganhas_periodos is not None else 0  # type: ignore[attr-defined]
    ganhas_ultimo_mes = int(ganhas_periodos.total_ultimo_mes) if ganhas_periodos is not None else 0  # type: ignore[attr-defined]
    ganhas_mes_corrente = int(ganhas_periodos.total_mes_corrente) if ganhas_periodos is not None else 0  # type: ignore[attr-defined]
    ganhas_ultimos_7_dias = int(ganhas_periodos.total_ultimos_7_dias) if ganhas_periodos is not None else 0  # type: ignore[attr-defined]

    # Perdidas 12m / último mês / mês corrente
    # Regra solicitada: se não houver data de fechamento, usar data de recebimento (entrada do lead).
    data_referencia_perdida = func.coalesce(
        Oportunidade.opoDataFechamento,
        Oportunidade.opoDataRecebimento,
    )
    perdidas_periodos_stmt = (
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                data_referencia_perdida >= primeiro_dia_12m,
                                data_referencia_perdida < primeiro_dia_proximo_mes,
                                Oportunidade.opoStatusFechamento == "perdido",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_12m"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                data_referencia_perdida >= primeiro_dia_mes_anterior,
                                data_referencia_perdida < primeiro_dia_mes_corrente,
                                Oportunidade.opoStatusFechamento == "perdido",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_ultimo_mes"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                data_referencia_perdida >= primeiro_dia_mes_corrente,
                                data_referencia_perdida < primeiro_dia_proximo_mes,
                                Oportunidade.opoStatusFechamento == "perdido",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_mes_corrente"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                data_referencia_perdida >= inicio_ultimos_7_dias,
                                data_referencia_perdida <= today,
                                Oportunidade.opoStatusFechamento == "perdido",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_ultimos_7_dias"),
        )
        .where(
            *fechadas_conditions,
            Oportunidade.opoAtivo.is_(True),
        )
    )
    perdidas_periodos = db.execute(perdidas_periodos_stmt).first()
    perdidas_12m = int(perdidas_periodos.total_12m) if perdidas_periodos is not None else 0  # type: ignore[attr-defined]
    perdidas_ultimo_mes = int(perdidas_periodos.total_ultimo_mes) if perdidas_periodos is not None else 0  # type: ignore[attr-defined]
    perdidas_mes_corrente = int(perdidas_periodos.total_mes_corrente) if perdidas_periodos is not None else 0  # type: ignore[attr-defined]
    perdidas_ultimos_7_dias = int(perdidas_periodos.total_ultimos_7_dias) if perdidas_periodos is not None else 0  # type: ignore[attr-defined]

    # Ativas e valor das ativas: sempre status ativo (status_fechamento is null)
    ativas_conditions = _build_base_filters(company_id, filtros)
    # força regra de ativos para este card, independentemente do filtro de status
    ativas_conditions = [
        c for c in ativas_conditions if c.left.key != "opoStatusFechamento"  # type: ignore[attr-defined]
    ]
    ativas_conditions.append(Oportunidade.opoStatusFechamento.is_(None))

    ativas_stmt = select(
        func.count(Oportunidade.opoId).label("qtd"),
        func.coalesce(func.sum(Oportunidade.opoValorOportunidade), 0).label("valor"),
    ).where(
        *ativas_conditions,
        Oportunidade.opoAtivo.is_(True),
    )
    ativas_row = db.execute(ativas_stmt).first()
    ativas_total = int(ativas_row.qtd) if ativas_row is not None else 0  # type: ignore[attr-defined]
    valor_ativas_total = float(ativas_row.valor) if ativas_row is not None else 0.0  # type: ignore[attr-defined]
    forecast_stmt = select(
        Oportunidade.opoValorOportunidade,
        Oportunidade.opoTemperatura,
        Oportunidade.opoLeadScore,
    ).where(
        *ativas_conditions,
        Oportunidade.opoAtivo.is_(True),
    )
    forecast_rows = db.execute(forecast_stmt).all()
    forecast_ativas_total = sum(
        _calculate_forecast_value(
            row.opoValorOportunidade,
            row.opoTemperatura,
            row.opoLeadScore,
        )
        for row in forecast_rows
    )

    # MRR incremental: ganhas, não-projeto (opoFechadoRecorrencia <> 1) e não receita pontual
    mrr_conditions = list(fechadas_conditions)
    mrr_conditions.append(Oportunidade.opoStatusFechamento == "ganho")
    mrr_conditions.append(
        func.coalesce(Oportunidade.opoFechadoRecorrencia, 0) != 1,
    )
    mrr_conditions.append(Oportunidade.opoReceitaPontual.is_(False))

    mrr_stmt = select(
        func.coalesce(func.sum(Oportunidade.opoValorFechado), 0),
    ).where(
        *mrr_conditions,
        Oportunidade.opoAtivo.is_(True),
    )
    mrr_total = float(db.scalar(mrr_stmt) or 0)

    mrr_periodos_stmt = (
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Oportunidade.opoDataFechamento >= primeiro_dia_12m,
                                Oportunidade.opoDataFechamento < primeiro_dia_proximo_mes,
                                Oportunidade.opoStatusFechamento == "ganho",
                                func.coalesce(Oportunidade.opoFechadoRecorrencia, 0) != 1,
                                Oportunidade.opoReceitaPontual.is_(False),
                            ),
                            Oportunidade.opoValorFechado,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_12m"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Oportunidade.opoDataFechamento >= primeiro_dia_mes_anterior,
                                Oportunidade.opoDataFechamento < primeiro_dia_mes_corrente,
                                Oportunidade.opoStatusFechamento == "ganho",
                                func.coalesce(Oportunidade.opoFechadoRecorrencia, 0) != 1,
                                Oportunidade.opoReceitaPontual.is_(False),
                            ),
                            Oportunidade.opoValorFechado,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_ultimo_mes"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Oportunidade.opoDataFechamento >= primeiro_dia_mes_corrente,
                                Oportunidade.opoDataFechamento < primeiro_dia_proximo_mes,
                                Oportunidade.opoStatusFechamento == "ganho",
                                func.coalesce(Oportunidade.opoFechadoRecorrencia, 0) != 1,
                                Oportunidade.opoReceitaPontual.is_(False),
                            ),
                            Oportunidade.opoValorFechado,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_mes_corrente"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Oportunidade.opoDataFechamento >= inicio_ultimos_7_dias,
                                Oportunidade.opoDataFechamento <= today,
                                Oportunidade.opoStatusFechamento == "ganho",
                                func.coalesce(Oportunidade.opoFechadoRecorrencia, 0) != 1,
                                Oportunidade.opoReceitaPontual.is_(False),
                            ),
                            Oportunidade.opoValorFechado,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_ultimos_7_dias"),
        )
        .where(
            *base_conditions,
            Oportunidade.opoAtivo.is_(True),
            Oportunidade.opoDataFechamento.is_not(None),
        )
    )
    mrr_periodos = db.execute(mrr_periodos_stmt).first()
    mrr_12m = float(mrr_periodos.total_12m) if mrr_periodos is not None else 0.0  # type: ignore[attr-defined]
    mrr_ultimo_mes = float(mrr_periodos.total_ultimo_mes) if mrr_periodos is not None else 0.0  # type: ignore[attr-defined]
    mrr_mes_corrente = float(mrr_periodos.total_mes_corrente) if mrr_periodos is not None else 0.0  # type: ignore[attr-defined]
    mrr_ultimos_7_dias = float(mrr_periodos.total_ultimos_7_dias) if mrr_periodos is not None else 0.0  # type: ignore[attr-defined]

    # Taxa de conversão
    base_conversao = ganhas_total + perdidas_total
    if base_conversao > 0:
        taxa_conversao = (ganhas_total / base_conversao) * 100
    else:
        taxa_conversao = 0.0

    return CrmDashboardCards(
        recebidas=recebidas_total,
        recebidas12m=recebidas_12m,
        recebidasUltimoMes=recebidas_ultimo_mes,
        recebidasMesCorrente=recebidas_mes_corrente,
        recebidasUltimos7Dias=recebidas_ultimos_7_dias,
        ganhas=ganhas_total,
        ganhas12m=ganhas_12m,
        ganhasUltimoMes=ganhas_ultimo_mes,
        ganhasMesCorrente=ganhas_mes_corrente,
        ganhasUltimos7Dias=ganhas_ultimos_7_dias,
        perdidas=perdidas_total,
        perdidas12m=perdidas_12m,
        perdidasUltimoMes=perdidas_ultimo_mes,
        perdidasMesCorrente=perdidas_mes_corrente,
        perdidasUltimos7Dias=perdidas_ultimos_7_dias,
        taxaConversao=round(taxa_conversao, 2),
        ativas=ativas_total,
        valorAtivas=float(round(valor_ativas_total, 2)),
        forecastAtivas=float(round(forecast_ativas_total, 2)),
        mrrIncremental=float(round(mrr_total, 2)),
        mrrIncremental12m=float(round(mrr_12m, 2)),
        mrrIncrementalUltimoMes=float(round(mrr_ultimo_mes, 2)),
        mrrIncrementalMesCorrente=float(round(mrr_mes_corrente, 2)),
        mrrIncrementalUltimos7Dias=float(round(mrr_ultimos_7_dias, 2)),
    )


def _query_grafico_por_mes(
    db: Session,
    company_id: Optional[int],
    filtros: CrmDashboardFiltroParams,
) -> list[CrmDashboardGraficoPorMesItem]:
    conditions = _build_base_filters(company_id, filtros)

    # últimos 12 meses (incluindo mês corrente) se nenhum período for informado
    if filtros.data_inicial is None and filtros.data_final is None:
        today = date.today()
        primeiro_dia_mes_corrente = today.replace(day=1)
        ano_12m = primeiro_dia_mes_corrente.year
        mes_12m = primeiro_dia_mes_corrente.month - 11
        while mes_12m <= 0:
            mes_12m += 12
            ano_12m -= 1
        primeiro_dia_12m = primeiro_dia_mes_corrente.replace(year=ano_12m, month=mes_12m)
        periodo = _between_dates(
            Oportunidade.opoDataRecebimento,
            primeiro_dia_12m,
            None,
        )
    else:
        periodo = _between_dates(
            Oportunidade.opoDataRecebimento,
            filtros.data_inicial,
            filtros.data_final,
        )
    if periodo is not None:
        conditions.append(periodo)

    stmt = (
        select(
            func.extract("year", Oportunidade.opoDataRecebimento).label("ano"),
            func.extract("month", Oportunidade.opoDataRecebimento).label("mes"),
            func.count(Oportunidade.opoId).label("qtd"),
        )
        .where(
            *conditions,
            Oportunidade.opoAtivo.is_(True),
            Oportunidade.opoDataRecebimento.is_not(None),
        )
        .group_by("ano", "mes")
        .order_by("ano", "mes")
    )
    rows = db.execute(stmt).all()
    return [
        CrmDashboardGraficoPorMesItem(
            ano=int(row.ano),  # type: ignore[arg-type]
            mes=int(row.mes),  # type: ignore[arg-type]
            quantidade=int(row.qtd),
        )
        for row in rows
    ]


def _query_grafico_por_fonte(
    db: Session,
    company_id: Optional[int],
    filtros: CrmDashboardFiltroParams,
) -> list[CrmDashboardGraficoPorFonteItem]:
    conditions = _build_base_filters(company_id, filtros)
    periodo = _between_dates(
        Oportunidade.opoDataRecebimento,
        filtros.data_inicial,
        filtros.data_final,
    )
    if periodo is not None:
        conditions.append(periodo)

    fonte_nome = func.coalesce(ComoConheceu.ccoNome, "Não informado")

    stmt = (
        select(
            fonte_nome.label("fonte"),
            func.count(Oportunidade.opoId).label("qtd"),
        )
        .select_from(Oportunidade)
        .join(
            ComoConheceu,
            Oportunidade.opoCcoId == ComoConheceu.ccoId,
            isouter=True,
        )
        .where(
            *conditions,
            Oportunidade.opoAtivo.is_(True),
        )
        .group_by(fonte_nome)
        .order_by(func.count(Oportunidade.opoId).desc())
    )
    rows = db.execute(stmt).all()
    return [
        CrmDashboardGraficoPorFonteItem(
            fonte=row.fonte,
            quantidade=int(row.qtd),
        )
        for row in rows
    ]


def _query_grafico_por_solucao(
    db: Session,
    company_id: Optional[int],
    filtros: CrmDashboardFiltroParams,
) -> list[CrmDashboardGraficoPorSolucaoItem]:
    conditions = _build_base_filters(company_id, filtros)
    periodo = _between_dates(
        Oportunidade.opoDataRecebimento,
        filtros.data_inicial,
        filtros.data_final,
    )
    if periodo is not None:
        conditions.append(periodo)

    solucao_nome = func.coalesce(
        func.nullif(Produto.proNome, ""),
        func.nullif(Oportunidade.opoSolucao, ""),
        "Não informado",
    )

    stmt = (
        select(
            solucao_nome.label("solucao"),
            func.count(Oportunidade.opoId).label("qtd"),
        )
        .select_from(Oportunidade)
        .join(
            Produto,
            Oportunidade.opoProId == Produto.proId,
            isouter=True,
        )
        .where(
            *conditions,
            Oportunidade.opoAtivo.is_(True),
        )
        .group_by(solucao_nome)
        .order_by(func.count(Oportunidade.opoId).desc())
    )
    rows = db.execute(stmt).all()
    return [
        CrmDashboardGraficoPorSolucaoItem(
            solucao=row.solucao,
            quantidade=int(row.qtd),
        )
        for row in rows
    ]


def _query_grafico_ativas_por_responsavel(
    db: Session,
    company_id: Optional[int],
    filtros: CrmDashboardFiltroParams,
) -> list[CrmDashboardGraficoAtivasPorResponsavelItem]:
    conditions = _build_base_filters(company_id, filtros)
    # força apenas ativas
    conditions = [
        c for c in conditions if c.left.key != "opoStatusFechamento"  # type: ignore[attr-defined]
    ]
    conditions.append(Oportunidade.opoStatusFechamento.is_(None))

    periodo = _between_dates(
        Oportunidade.opoDataRecebimento,
        filtros.data_inicial,
        filtros.data_final,
    )
    if periodo is not None:
        conditions.append(periodo)

    responsavel_nome = func.coalesce(Usuario.usuNome, "Não informado")

    stmt = (
        select(
            responsavel_nome.label("responsavel"),
            func.count(Oportunidade.opoId).label("qtd"),
        )
        .select_from(Oportunidade)
        .join(
            Usuario,
            Oportunidade.opoUsuResponsavelId == Usuario.usuId,
            isouter=True,
        )
        .where(
            *conditions,
            Oportunidade.opoAtivo.is_(True),
        )
        .group_by(responsavel_nome)
    )
    rows = db.execute(stmt).all()
    return [
        CrmDashboardGraficoAtivasPorResponsavelItem(
            responsavel=row.responsavel,
            quantidade=int(row.qtd),
        )
        for row in rows
    ]


def _query_responsaveis(
    db: Session,
    company_id: Optional[int],
) -> list[dict]:
    stmt = (
        select(
            Usuario.usuId.label("id"),
            Usuario.usuNome.label("nome"),
        )
        .join(
            Oportunidade,
            Oportunidade.opoUsuResponsavelId == Usuario.usuId,
        )
        .where(
            Usuario.usuAtivo.is_(True),
        )
        .group_by(Usuario.usuId, Usuario.usuNome)
        .order_by(Usuario.usuNome)
    )
    if company_id is not None:
        stmt = stmt.where(Oportunidade.opoEmpId == company_id)
    rows = db.execute(stmt).all()
    return [{"id": row.id, "nome": row.nome} for row in rows]


def _month_bounds_from_periodo(periodo: str | None) -> tuple[date, date] | None:
    if not periodo or len(periodo) != 7 or periodo[4] != "-":
        return None
    try:
        y = int(periodo[0:4])
        m = int(periodo[5:7])
        if m < 1 or m > 12:
            return None
        first = date(y, m, 1)
        return first, _last_day_of_month(first)
    except ValueError:
        return None


def _intersect_date_range(
    di: Optional[date],
    df: Optional[date],
    m0: date,
    m1: date,
) -> tuple[Optional[date], Optional[date]] | None:
    """Interseção [di,df] com [m0,m1]. Retorna None se vazio."""
    a = di if di is not None else m0
    b = df if df is not None else m1
    lo = max(a, m0)
    hi = min(b, m1)
    if lo > hi:
        return None
    return lo, hi


def _forecast_sql_expr():
    """Replica a lógica de _calculate_forecast_value em SQL (para agregados do drill-down)."""
    valor = func.coalesce(Oportunidade.opoValorOportunidade, 0)
    tnorm = func.lower(func.trim(func.coalesce(Oportunidade.opoTemperatura, "")))
    temp_mul = case(
        (tnorm == "quente", 0.75),
        (tnorm == "morno", 0.50),
        (tnorm == "frio", 0.25),
        else_=0.0,
    )
    score_raw = func.coalesce(Oportunidade.opoLeadScore, 0)
    score_capped = case((score_raw < 0, 0), (score_raw > 10, 10), else_=score_raw)
    score_mul = score_capped / literal(10)
    return case(
        (and_(valor > 0, temp_mul > 0, score_mul > 0), valor * temp_mul * score_mul),
        else_=0.0,
    )


def _oportunidade_mrr_valor_sql():
    return case(
        (
            and_(
                Oportunidade.opoStatusFechamento == "ganho",
                func.coalesce(Oportunidade.opoFechadoRecorrencia, 0) != 1,
                Oportunidade.opoReceitaPontual.is_(False),
            ),
            func.coalesce(Oportunidade.opoValorFechado, 0),
        ),
        else_=0.0,
    )


def _ranking_base_where(company_id: Optional[int], filtros: CrmDashboardFiltroParams) -> list:
    conds: list = []
    if company_id is not None:
        conds.append(Oportunidade.opoEmpId == company_id)
    if filtros.responsavel_id is not None:
        conds.append(Oportunidade.opoUsuResponsavelId == filtros.responsavel_id)
    return conds


def _query_rankings_analiticos(
    db: Session,
    company_id: Optional[int],
    filtros: CrmDashboardFiltroParams,
) -> CrmDashboardRankingsResponse:
    di, df = filtros.data_inicial, filtros.data_final
    bd_rec = _between_dates(Oportunidade.opoDataRecebimento, di, df)
    bd_fec = _between_dates(Oportunidade.opoDataFechamento, di, df)
    perd_ref = func.coalesce(Oportunidade.opoDataFechamento, Oportunidade.opoDataRecebimento)
    bd_perd = _between_dates(perd_ref, di, df)
    rec_date = bd_rec if bd_rec is not None else true()
    fec_date = bd_fec if bd_fec is not None else true()
    perd_date = bd_perd if bd_perd is not None else true()

    rec_cond = and_(
        Oportunidade.opoAtivo.is_(True),
        Oportunidade.opoDataRecebimento.isnot(None),
        rec_date,
    )
    gan_cond = and_(
        Oportunidade.opoAtivo.is_(True),
        Oportunidade.opoStatusFechamento == "ganho",
        Oportunidade.opoDataFechamento.isnot(None),
        fec_date,
    )
    perd_cond = and_(
        Oportunidade.opoAtivo.is_(True),
        Oportunidade.opoStatusFechamento == "perdido",
        perd_ref.isnot(None),
        perd_date,
    )
    atv_cond = and_(Oportunidade.opoAtivo.is_(True), Oportunidade.opoStatusFechamento.is_(None))
    scope = or_(rec_cond, gan_cond, perd_cond, atv_cond)

    base_where = _ranking_base_where(company_id, filtros)

    rid = func.coalesce(Usuario.usuId, literal(-1)).label("rid")
    rname = func.coalesce(Usuario.usuNome, "Não informado").label("rname")
    fonte_nome = func.coalesce(ComoConheceu.ccoNome, "Não informado").label("fonte")
    solucao_nome = func.coalesce(
        func.nullif(Produto.proNome, ""),
        func.nullif(Oportunidade.opoSolucao, ""),
        "Não informado",
    ).label("solucao")

    mrr_expr = _mrr_incremental_expr()

    stmt_resp = (
        select(
            rid,
            rname,
            func.sum(case((rec_cond, 1), else_=0)).label("rec"),
            func.sum(case((gan_cond, 1), else_=0)).label("gan"),
            func.sum(case((perd_cond, 1), else_=0)).label("perd"),
            func.sum(case((atv_cond, 1), else_=0)).label("atv"),
            func.coalesce(func.sum(mrr_expr), 0).label("mrr"),
        )
        .select_from(Oportunidade)
        .join(Usuario, Oportunidade.opoUsuResponsavelId == Usuario.usuId, isouter=True)
        .where(*base_where, scope)
        .group_by(rid, rname)
    )
    rows_resp = db.execute(stmt_resp).all()
    resp_items: list[CrmDashboardRankingResponsavelItem] = []
    for row in rows_resp:
        rec = int(row.rec)  # type: ignore[attr-defined]
        gan = int(row.gan)  # type: ignore[attr-defined]
        perd = int(row.perd)  # type: ignore[attr-defined]
        atv = int(row.atv)  # type: ignore[attr-defined]
        mrr = float(row.mrr)  # type: ignore[attr-defined]
        fech = gan + perd
        taxa = round((gan / fech) * 100, 2) if fech > 0 else 0.0
        ticket = round(mrr / gan, 2) if gan > 0 else 0.0
        rid_v = int(row.rid)  # type: ignore[attr-defined]
        resp_items.append(
            CrmDashboardRankingResponsavelItem(
                responsavelId=None if rid_v < 0 else rid_v,
                responsavel=str(row.rname),
                recebidas=rec,
                ganhas=gan,
                perdidas=perd,
                ativas=atv,
                taxaConversao=taxa,
                mrrIncremental=round(mrr, 2),
                ticketMedio=ticket,
            )
        )
    resp_items.sort(key=lambda x: x.mrrIncremental, reverse=True)
    resp_items = resp_items[:10]

    stmt_fonte = (
        select(
            fonte_nome,
            func.sum(case((rec_cond, 1), else_=0)).label("rec"),
            func.sum(case((gan_cond, 1), else_=0)).label("gan"),
            func.sum(case((perd_cond, 1), else_=0)).label("perd"),
            func.coalesce(func.sum(mrr_expr), 0).label("mrr"),
        )
        .select_from(Oportunidade)
        .join(ComoConheceu, Oportunidade.opoCcoId == ComoConheceu.ccoId, isouter=True)
        .where(*base_where, scope)
        .group_by(fonte_nome)
    )
    rows_fonte = db.execute(stmt_fonte).all()
    fonte_items: list[CrmDashboardRankingFonteItem] = []
    for row in rows_fonte:
        rec = int(row.rec)  # type: ignore[attr-defined]
        gan = int(row.gan)  # type: ignore[attr-defined]
        perd = int(row.perd)  # type: ignore[attr-defined]
        mrr = float(row.mrr)  # type: ignore[attr-defined]
        fech_f = gan + perd
        fonte_items.append(
            CrmDashboardRankingFonteItem(
                fonte=str(row.fonte),
                recebidas=rec,
                ganhas=gan,
                perdidas=perd,
                taxaConversao=round((gan / fech_f) * 100, 2) if fech_f > 0 else 0.0,
                mrrIncremental=round(mrr, 2),
            )
        )
    fonte_items.sort(key=lambda x: x.mrrIncremental, reverse=True)
    fonte_items = fonte_items[:10]

    stmt_sol = (
        select(
            solucao_nome,
            func.sum(case((rec_cond, 1), else_=0)).label("rec"),
            func.sum(case((gan_cond, 1), else_=0)).label("gan"),
            func.sum(case((perd_cond, 1), else_=0)).label("perd"),
            func.coalesce(func.sum(mrr_expr), 0).label("mrr"),
        )
        .select_from(Oportunidade)
        .join(Produto, Oportunidade.opoProId == Produto.proId, isouter=True)
        .where(*base_where, scope)
        .group_by(solucao_nome)
    )
    rows_sol = db.execute(stmt_sol).all()
    sol_items: list[CrmDashboardRankingSolucaoItem] = []
    for row in rows_sol:
        rec = int(row.rec)  # type: ignore[attr-defined]
        gan = int(row.gan)  # type: ignore[attr-defined]
        perd = int(row.perd)  # type: ignore[attr-defined]
        mrr = float(row.mrr)  # type: ignore[attr-defined]
        fech_s = gan + perd
        sol_items.append(
            CrmDashboardRankingSolucaoItem(
                solucao=str(row.solucao),
                recebidas=rec,
                ganhas=gan,
                perdidas=perd,
                taxaConversao=round((gan / fech_s) * 100, 2) if fech_s > 0 else 0.0,
                mrrIncremental=round(mrr, 2),
            )
        )
    sol_items.sort(key=lambda x: x.mrrIncremental, reverse=True)
    sol_items = sol_items[:10]

    return CrmDashboardRankingsResponse(
        responsaveis=resp_items,
        fontes=fonte_items,
        solucoes=sol_items,
    )


def _drill_joins_and_labels(company_id: Optional[int]):
    fonte_nome = func.coalesce(ComoConheceu.ccoNome, "Não informado").label("fonte_nome")
    solucao_nome = func.coalesce(
        func.nullif(Produto.proNome, ""),
        func.nullif(Oportunidade.opoSolucao, ""),
        "Não informado",
    ).label("solucao_nome")
    motivo_nome = func.coalesce(MotivoCancelamento.mcaNome, "Não informado").label("motivo_nome")
    join_motivo = Oportunidade.opoMcaId == MotivoCancelamento.mcaId
    if company_id is not None:
        join_motivo = and_(join_motivo, MotivoCancelamento.mcaEmpId == company_id)
    etk_join = Oportunidade.opoEtkId == EtapaKanban.etkId
    if company_id is not None:
        etk_join = and_(etk_join, EtapaKanban.etkEmpId == company_id)
    return fonte_nome, solucao_nome, motivo_nome, join_motivo, etk_join


def _status_label(status_fech: str | None) -> str:
    if status_fech == "ganho":
        return "Ganha"
    if status_fech == "perdido":
        return "Perdida"
    if status_fech == "stand-by":
        return "Stand-by"
    return "Ativa"


def list_dashboard_oportunidades(
    db: Session,
    company_id: Optional[int],
    filtros: CrmDashboardOportunidadesFiltroParams,
) -> CrmDashboardOportunidadesListResponse:
    fonte_nome, solucao_nome, motivo_nome, join_motivo, etk_join = _drill_joins_and_labels(company_id)

    conditions: list = []
    if company_id is not None:
        conditions.append(Oportunidade.opoEmpId == company_id)
    if filtros.responsavel_id is not None:
        if filtros.responsavel_id < 0:
            conditions.append(Oportunidade.opoUsuResponsavelId.is_(None))
        else:
            conditions.append(Oportunidade.opoUsuResponsavelId == filtros.responsavel_id)

    if filtros.fonte:
        conditions.append(fonte_nome == filtros.fonte.strip())
    if filtros.solucao:
        conditions.append(solucao_nome == filtros.solucao.strip())
    if filtros.motivo_perda:
        mp = filtros.motivo_perda.strip()
        if mp == "Não informado":
            conditions.append(Oportunidade.opoMcaId.is_(None))
        else:
            conditions.append(MotivoCancelamento.mcaNome == mp)

    di_g, df_g = filtros.data_inicial, filtros.data_final
    mb = _month_bounds_from_periodo(filtros.periodo)
    if mb is not None:
        m0, m1 = mb
        inter = _intersect_date_range(di_g, df_g, m0, m1)
        if inter is None:
            return CrmDashboardOportunidadesListResponse(
                itens=[],
                total=0,
                resumo=CrmDashboardOportunidadesResumo(
                    quantidade=0,
                    mrrTotal=0.0,
                    forecastTotal=0.0,
                    ticketMedio=0.0,
                ),
            )
        di_g, df_g = inter

    _m_raw = (filtros.metrica or "").strip().lower()
    if _m_raw == "mrrincremental":
        metrica_eff: str | None = "mrr_incremental"
    elif _m_raw in ("recebidas", "ganhas", "perdidas", "ativas"):
        metrica_eff = _m_raw
    else:
        metrica_eff = None

    if metrica_eff == "mrr_incremental":
        conditions.append(Oportunidade.opoAtivo.is_(True))
        conditions.append(Oportunidade.opoStatusFechamento == "ganho")
        bd = _between_dates(Oportunidade.opoDataFechamento, di_g, df_g)
        if bd is not None:
            conditions.append(bd)
        else:
            conditions.append(Oportunidade.opoDataFechamento.isnot(None))
    elif metrica_eff == "recebidas":
        conditions.append(Oportunidade.opoAtivo.is_(True))
        conditions.append(Oportunidade.opoDataRecebimento.isnot(None))
        bd = _between_dates(Oportunidade.opoDataRecebimento, di_g, df_g)
        if bd is not None:
            conditions.append(bd)
    elif metrica_eff == "ganhas":
        conditions.append(Oportunidade.opoAtivo.is_(True))
        conditions.append(Oportunidade.opoStatusFechamento == "ganho")
        bd = _between_dates(Oportunidade.opoDataFechamento, di_g, df_g)
        if bd is not None:
            conditions.append(bd)
        else:
            conditions.append(Oportunidade.opoDataFechamento.isnot(None))
    elif metrica_eff == "perdidas":
        conditions.append(Oportunidade.opoAtivo.is_(True))
        conditions.append(Oportunidade.opoStatusFechamento == "perdido")
        perd_ref = func.coalesce(Oportunidade.opoDataFechamento, Oportunidade.opoDataRecebimento)
        conditions.append(perd_ref.isnot(None))
        bd = _between_dates(perd_ref, di_g, df_g)
        if bd is not None:
            conditions.append(bd)
    elif metrica_eff == "ativas":
        conditions.append(Oportunidade.opoAtivo.is_(True))
        conditions.append(Oportunidade.opoStatusFechamento.is_(None))
        if mb is not None:
            bd = _between_dates(Oportunidade.opoDataRecebimento, di_g, df_g)
            if bd is not None:
                conditions.append(bd)
    else:
        sf = _build_status_filter(filtros.status)
        if sf is not None:
            conditions.append(sf)
        conditions.append(Oportunidade.opoAtivo.is_(True))
        if metrica_eff is None and (filtros.status or "todas") == "todas":
            or_parts = []
            b1 = _between_dates(Oportunidade.opoDataRecebimento, di_g, df_g)
            if b1 is not None:
                or_parts.append(b1)
            b2 = _between_dates(Oportunidade.opoDataFechamento, di_g, df_g)
            if b2 is not None:
                or_parts.append(b2)
            if or_parts:
                conditions.append(or_(*or_parts))

    mrr_sql = _oportunidade_mrr_valor_sql()
    mrr_agg_sql = _mrr_perdido_expr() if metrica_eff == "perdidas" else mrr_sql
    forecast_sql = _forecast_sql_expr()
    forecast_agg_sql = literal(0) if metrica_eff == "perdidas" else forecast_sql

    def _drill_from(q):
        return (
            q.select_from(Oportunidade)
            .join(Usuario, Oportunidade.opoUsuResponsavelId == Usuario.usuId, isouter=True)
            .join(ComoConheceu, Oportunidade.opoCcoId == ComoConheceu.ccoId, isouter=True)
            .join(Produto, Oportunidade.opoProId == Produto.proId, isouter=True)
            .join(MotivoCancelamento, join_motivo, isouter=True)
            .join(EtapaKanban, etk_join, isouter=True)
        )

    agg_stmt = _drill_from(
        select(
            func.count(Oportunidade.opoId).label("tot"),
            func.coalesce(func.sum(mrr_agg_sql), 0).label("mrr_sum"),
            func.coalesce(func.sum(forecast_agg_sql), 0).label("fc_sum"),
        )
    ).where(*conditions)
    agg_row = db.execute(agg_stmt).first()
    total = int(agg_row.tot) if agg_row is not None else 0  # type: ignore[attr-defined]
    mrr_total = float(agg_row.mrr_sum) if agg_row is not None else 0.0  # type: ignore[attr-defined]
    fc_total = float(agg_row.fc_sum) if agg_row is not None else 0.0  # type: ignore[attr-defined]
    ticket = round(mrr_total / total, 2) if total > 0 and metrica_eff in ("perdidas", "ganhas", "mrr_incremental") else 0.0

    valor_row_sql = _mrr_perdido_expr() if metrica_eff == "perdidas" else mrr_sql
    data_ord = func.coalesce(
        Oportunidade.opoDataFechamento,
        Oportunidade.opoDataRecebimento,
        func.date(Oportunidade.opoDataCriacao),
    )
    list_stmt = _drill_from(
        select(
            Oportunidade.opoId,
            Oportunidade.opoTitulo,
            Oportunidade.opoEmpresaContato,
            Usuario.usuNome,
            Oportunidade.opoStatusFechamento,
            fonte_nome,
            solucao_nome,
            motivo_nome,
            valor_row_sql.label("valor_mrr"),
            forecast_sql.label("forecast_v"),
            Oportunidade.opoDataCriacao,
            Oportunidade.opoDataFechamento,
            Oportunidade.opoDataRecebimento,
            EtapaKanban.etkNome,
        )
    ).where(*conditions).order_by(data_ord.desc(), valor_row_sql.desc()).limit(100)
    rows = db.execute(list_stmt).all()

    itens: list[CrmDashboardOportunidadeResumoItem] = []
    for r in rows:
        st = _status_label(r.opoStatusFechamento)  # type: ignore[attr-defined]
        mrr_v = float(r.valor_mrr)  # type: ignore[attr-defined]
        fc_v = float(r.forecast_v)  # type: ignore[attr-defined]
        dc = r.opoDataCriacao  # type: ignore[attr-defined]
        if isinstance(dc, datetime):
            data_cri = dc.date().isoformat()
        elif isinstance(dc, date):
            data_cri = dc.isoformat()
        else:
            data_cri = None
        dfec = r.opoDataFechamento  # type: ignore[attr-defined]
        data_fec = dfec.isoformat() if dfec is not None else None
        itens.append(
            CrmDashboardOportunidadeResumoItem(
                id=int(r.opoId),  # type: ignore[attr-defined]
                nome=str(r.opoTitulo),
                cliente=r.opoEmpresaContato,  # type: ignore[attr-defined]
                responsavel=r.usuNome,  # type: ignore[attr-defined]
                status=st,
                fonte=str(r.fonte_nome),
                solucao=str(r.solucao_nome),
                motivoPerda=None if st != "Perdida" else str(r.motivo_nome),
                valorMrr=round(mrr_v, 2) if mrr_v != 0 else None,
                forecast=round(fc_v, 2) if fc_v > 0 else None,
                dataCriacao=data_cri,
                dataFechamento=data_fec,
                etapa=r.etkNome,  # type: ignore[attr-defined]
            )
        )

    return CrmDashboardOportunidadesListResponse(
        itens=itens,
        total=total,
        resumo=CrmDashboardOportunidadesResumo(
            quantidade=total,
            mrrTotal=round(mrr_total, 2),
            forecastTotal=round(fc_total, 2),
            ticketMedio=ticket,
        ),
    )


def get_dashboard(
    db: Session,
    company_id: Optional[int],
    filtros: CrmDashboardFiltroParams,
) -> CrmDashboardResponse:
    cards = _query_cards(db, company_id, filtros)
    grafico_por_mes = _query_grafico_por_mes(db, company_id, filtros)
    grafico_por_fonte = _query_grafico_por_fonte(db, company_id, filtros)
    grafico_por_solucao = _query_grafico_por_solucao(db, company_id, filtros)
    grafico_ativas_por_responsavel = _query_grafico_ativas_por_responsavel(
        db,
        company_id,
        filtros,
    )
    responsaveis = _query_responsaveis(db, company_id)
    tem_meta, resumo_metas = _query_metas_e_resumo(db, company_id, filtros, cards)
    motivos_perda = _query_motivos_perda(db, company_id, filtros)
    serie_mensal = _query_serie_mensal(db, company_id, filtros)
    rankings = _query_rankings_analiticos(db, company_id, filtros)

    graficos = CrmDashboardGraficosResponse(
        porMes=grafico_por_mes,
        porFonte=grafico_por_fonte,
        porSolucao=grafico_por_solucao,
        ativasPorResponsavel=grafico_ativas_por_responsavel,
    )

    return CrmDashboardResponse(
        cards=cards,
        graficos=graficos,
        filtros={"responsaveis": responsaveis},
        temMeta=tem_meta,
        resumoMetas=resumo_metas,
        motivosPerda=motivos_perda,
        serieMensal=serie_mensal,
        rankings=rankings,
    )

