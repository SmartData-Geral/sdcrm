from datetime import date
from typing import Optional

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from ..models.como_conheceu import ComoConheceu
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
    CrmDashboardResponse,
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

    # MRR incremental: oportunidades fechadas com opoFechadoRecorrencia <> 1
    mrr_conditions = list(fechadas_conditions)
    mrr_conditions.append(Oportunidade.opoStatusFechamento == "ganho")
    mrr_conditions.append(
        func.coalesce(Oportunidade.opoFechadoRecorrencia, 0) != 1,
    )

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
                            ),
                            Oportunidade.opoValorFechado,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_mes_corrente"),
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
        ganhas=ganhas_total,
        ganhas12m=ganhas_12m,
        ganhasUltimoMes=ganhas_ultimo_mes,
        ganhasMesCorrente=ganhas_mes_corrente,
        perdidas=perdidas_total,
        perdidas12m=perdidas_12m,
        perdidasUltimoMes=perdidas_ultimo_mes,
        perdidasMesCorrente=perdidas_mes_corrente,
        taxaConversao=round(taxa_conversao, 2),
        ativas=ativas_total,
        valorAtivas=float(round(valor_ativas_total, 2)),
        mrrIncremental=float(round(mrr_total, 2)),
        mrrIncremental12m=float(round(mrr_12m, 2)),
        mrrIncrementalUltimoMes=float(round(mrr_ultimo_mes, 2)),
        mrrIncrementalMesCorrente=float(round(mrr_mes_corrente, 2)),
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
    )

