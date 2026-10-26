"""Funil por oportunidade: datas de MQL, oportunidade e contrato, e primeira interacao humana.

Premissas de tempo (America/Sao_Paulo):
- `oehData` e gravado pelo app como UTC naive (`utcnow`) ou aware. Valor naive e tratado como
  UTC; a data do evento e a data LOCAL em America/Sao_Paulo (22:00 do dia 5 em SP = 01:00 UTC
  do dia 6 conta como dia 5).
- `primeira_interacao` devolve datetimes em UTC naive (mesma convencao do app). O
  fechamento "as 00:00" e a meia-noite LOCAL da data de fechamento, convertida para UTC.
- Entrada em um estagio conta para o estagio configurado e para qualquer estagio ativo do
  mesmo pipeline com `etkOrdem` estritamente maior; estagios de mesma ordem nao contam.
  Voltar de estagio nao desfaz a primeira chegada.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any, Callable
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ...models.etapa_kanban import EtapaKanban
from ...models.oportunidade import Oportunidade
from ...models.oportunidade_etapa_historico import OportunidadeEtapaHistorico
from ...models.oportunidade_historico import OportunidadeHistorico
from ..crm_dashboard_service import _mrr_incremental_expr, _valor_projeto_expr
from .config_monitor import obter_config

FUSO = ZoneInfo("America/Sao_Paulo")
_UTC = timezone.utc


def _parse(valor: Any) -> datetime:
    """Funcoes de agregacao no SQLite devolvem texto; normaliza para datetime."""
    if isinstance(valor, datetime):
        return valor
    return datetime.fromisoformat(str(valor))


def _para_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(_UTC).replace(tzinfo=None)


def _data_local(dt: datetime) -> date:
    aware = dt.replace(tzinfo=_UTC) if dt.tzinfo is None else dt
    return aware.astimezone(FUSO).date()


def _meia_noite_local_utc(dia: date) -> datetime:
    return _para_utc_naive(datetime.combine(dia, time.min, tzinfo=FUSO))


def estagios_que_contam(db: Session, etk_id: int) -> list[int]:
    """O proprio estagio + estagios ativos do mesmo pipeline/empresa com ordem maior."""
    base = db.execute(select(EtapaKanban).where(EtapaKanban.etkId == etk_id)).scalar_one_or_none()
    if base is None:
        return [etk_id]
    maiores = db.execute(
        select(EtapaKanban.etkId).where(
            EtapaKanban.etkEmpId == base.etkEmpId,
            EtapaKanban.etkPipeline == base.etkPipeline,
            EtapaKanban.etkAtivo.is_(True),
            EtapaKanban.etkOrdem > base.etkOrdem,
        )
    ).scalars().all()
    return [etk_id, *[i for i in maiores if i != etk_id]]


def primeiras_datas(db: Session, emp_id: int, etk_id: int | None) -> dict[int, date]:
    """Por oportunidade, a data local da primeira chegada ao estagio (ou posterior)."""
    if etk_id is None:
        return {}
    estagios = estagios_que_contam(db, etk_id)
    linhas = db.execute(
        select(OportunidadeEtapaHistorico.oehOpoId, func.min(OportunidadeEtapaHistorico.oehData))
        .join(Oportunidade, Oportunidade.opoId == OportunidadeEtapaHistorico.oehOpoId)
        .where(
            Oportunidade.opoEmpId == emp_id,
            Oportunidade.opoAtivo.is_(True),
            OportunidadeEtapaHistorico.oehEtkIdPara.in_(estagios),
        )
        .group_by(OportunidadeEtapaHistorico.oehOpoId)
    ).all()
    datas: dict[int, date] = {}
    for opo_id, primeira in linhas:
        if primeira is not None:
            datas[opo_id] = _data_local(_parse(primeira))

    ganhas = db.execute(
        select(Oportunidade.opoId, Oportunidade.opoDataFechamento).where(
            Oportunidade.opoEmpId == emp_id,
            Oportunidade.opoAtivo.is_(True),
            Oportunidade.opoStatusFechamento == "ganho",
            Oportunidade.opoDataFechamento.is_not(None),
        )
    ).all()
    for opo_id, fechamento in ganhas:
        datas.setdefault(opo_id, fechamento)
    return datas


def _menor(alvo: dict[int, datetime], opo_id: int, dt: datetime) -> None:
    dt = _para_utc_naive(dt)
    atual = alvo.get(opo_id)
    if atual is None or dt < atual:
        alvo[opo_id] = dt


def primeira_interacao(db: Session, emp_id: int) -> dict[int, datetime]:
    """Por oportunidade, o primeiro contato humano (UTC naive).

    Menor entre: primeira transicao partindo de um estagio (nao e a criacao); primeiro
    historico ativo com usuario (registros automaticos tem `ophUsuId` nulo); fechamento 00:00.
    """
    res: dict[int, datetime] = {}

    for opo_id, quando in db.execute(
        select(OportunidadeEtapaHistorico.oehOpoId, func.min(OportunidadeEtapaHistorico.oehData))
        .join(Oportunidade, Oportunidade.opoId == OportunidadeEtapaHistorico.oehOpoId)
        .where(
            Oportunidade.opoEmpId == emp_id,
            Oportunidade.opoAtivo.is_(True),
            OportunidadeEtapaHistorico.oehEtkIdDe.is_not(None),
        )
        .group_by(OportunidadeEtapaHistorico.oehOpoId)
    ).all():
        if quando is not None:
            _menor(res, opo_id, _parse(quando))

    for opo_id, quando in db.execute(
        select(OportunidadeHistorico.ophOpoId, func.min(OportunidadeHistorico.ophDataRegistro))
        .join(Oportunidade, Oportunidade.opoId == OportunidadeHistorico.ophOpoId)
        .where(
            Oportunidade.opoEmpId == emp_id,
            Oportunidade.opoAtivo.is_(True),
            OportunidadeHistorico.ophAtivo.is_(True),
            OportunidadeHistorico.ophUsuId.is_not(None),
        )
        .group_by(OportunidadeHistorico.ophOpoId)
    ).all():
        if quando is not None:
            _menor(res, opo_id, _parse(quando))

    for opo_id, fechamento in db.execute(
        select(Oportunidade.opoId, Oportunidade.opoDataFechamento).where(
            Oportunidade.opoEmpId == emp_id,
            Oportunidade.opoAtivo.is_(True),
            Oportunidade.opoDataFechamento.is_not(None),
        )
    ).all():
        _menor(res, opo_id, _meia_noite_local_utc(fechamento))
    return res


@dataclass
class FunilLead:
    opo_id: int
    mcg_id: int | None
    man_id: int | None
    recebido: date | None
    mql: date | None
    oportunidade: date | None
    contrato: date | None
    mrr: float
    projeto: float
    horas_primeiro_contato: float | None


def _horas(interacao: datetime | None, criacao: datetime | None, recebido: date | None) -> float | None:
    if interacao is None:
        return None
    if criacao is not None:
        inicio = _para_utc_naive(criacao)
    elif recebido is not None:
        inicio = _meia_noite_local_utc(recebido)
    else:
        return None
    return max((interacao - inicio).total_seconds() / 3600, 0.0)


def carregar_funil(db: Session, emp_id: int, condicao_meta) -> list[FunilLead]:
    """Leads ativos da empresa que satisfazem `condicao_meta`, com as datas do funil."""
    cfg = obter_config(db, emp_id)
    mqls = primeiras_datas(db, emp_id, cfg.mmcEtkMqlId)
    oportunidades = primeiras_datas(db, emp_id, cfg.mmcEtkOportunidadeId)
    interacoes = primeira_interacao(db, emp_id)

    linhas = db.execute(
        select(
            Oportunidade.opoId,
            Oportunidade.opoMcgId,
            Oportunidade.opoManId,
            Oportunidade.opoDataRecebimento,
            Oportunidade.opoDataCriacao,
            Oportunidade.opoStatusFechamento,
            Oportunidade.opoDataFechamento,
            _mrr_incremental_expr().label("mrr"),
            _valor_projeto_expr().label("projeto"),
        ).where(and_(Oportunidade.opoEmpId == emp_id, Oportunidade.opoAtivo.is_(True), condicao_meta))
    ).all()

    leads: list[FunilLead] = []
    for r in linhas:
        ganho = r.opoStatusFechamento == "ganho" and r.opoDataFechamento is not None
        leads.append(
            FunilLead(
                opo_id=r.opoId,
                mcg_id=r.opoMcgId,
                man_id=r.opoManId,
                recebido=r.opoDataRecebimento,
                mql=mqls.get(r.opoId),
                oportunidade=oportunidades.get(r.opoId),
                contrato=r.opoDataFechamento if ganho else None,
                mrr=float(r.mrr or 0) if ganho else 0.0,
                projeto=float(r.projeto or 0) if ganho else 0.0,
                horas_primeiro_contato=_horas(
                    interacoes.get(r.opoId), r.opoDataCriacao, r.opoDataRecebimento
                ),
            )
        )
    return leads


def _no_periodo(dia: date | None, inicio: date | None, fim: date | None) -> bool:
    if dia is None:
        return False
    return (inicio is None or dia >= inicio) and (fim is None or dia <= fim)


def contar(
    funil: list[FunilLead],
    inicio: date | None,
    fim: date | None,
    chave: Callable[[FunilLead], Any],
) -> dict:
    """Agrupa por `chave(lead)`; cada etapa e contada pela propria data dentro do periodo."""
    grupos: dict[Any, dict] = defaultdict(
        lambda: {
            "leadsCrm": 0, "mqls": 0, "oportunidades": 0, "contratos": 0,
            "mrr": 0.0, "projeto": 0.0, "_horas": [],
        }
    )
    for lead in funil:
        g = grupos[chave(lead)]
        if _no_periodo(lead.recebido, inicio, fim):
            g["leadsCrm"] += 1
            if lead.horas_primeiro_contato is not None:
                g["_horas"].append(lead.horas_primeiro_contato)
        if _no_periodo(lead.mql, inicio, fim):
            g["mqls"] += 1
        if _no_periodo(lead.oportunidade, inicio, fim):
            g["oportunidades"] += 1
        if _no_periodo(lead.contrato, inicio, fim):
            g["contratos"] += 1
            g["mrr"] += lead.mrr
            g["projeto"] += lead.projeto

    resultado: dict = {}
    for k, g in grupos.items():
        horas = g.pop("_horas")
        g["horasPrimeiroContatoMedia"] = sum(horas) / len(horas) if horas else None
        resultado[k] = g
    return resultado
