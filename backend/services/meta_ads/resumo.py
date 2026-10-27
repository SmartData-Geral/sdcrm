"""Resumo diario do monitoramento Meta: periodo, ranking de anuncios, dados agregados e leitura por IA.

`dados` guarda so ids, nomes de campanha/anuncio e numeros: nunca `revisaoOrigem`, nome, telefone
ou e-mail de lead (e nem a mensagem dos alertas, que pode ter nome de lead). A IA recebe so as
chaves de `CHAVES_IA` de `dados` (nunca as listas completas de campanhas e anuncios).
Datas do resumo no fuso America/Sao_Paulo.

Comparacao: a media diaria do periodo anterior contra a media diaria dos 7 dias ANTES dele
(`janela_base`), para a base nao conter o proprio periodo. `ultimos7` (hoje-7..ontem) fica para
exibicao e ranking.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.tempo import utcnow
from ...exceptions import NotFoundError
from ...models.meta_ads_alerta import STATUS_ABERTO, MetaAdsAlerta
from ...models.meta_ads_conta import MetaAdsConta
from ...models.meta_ads_resumo import MetaAdsResumo
from ...schemas.meta_ads import (
    MetaAdsLinha,
    MetaAdsResumoDiarioItem,
    MetaAdsResumoDiarioListResponse,
    MetaAdsResumoDiarioResponse,
)
from .config_monitor import obter_config
from .indicadores import FiltroPainel, painel

logger = logging.getLogger(__name__)

FUSO = ZoneInfo("America/Sao_Paulo")
MAX_RANKING = 3
DIAS_ULTIMOS = 7
TOLERANCIA = timedelta(minutes=1)
PREFIXO_AVISO = "Leitura por IA indisponível"

PROMPT_SISTEMA = (
    "Você é um analista de mídia paga. Em até dois parágrafos, diga o que mudou e o que vale olhar. "
    "Use só os números fornecidos. Não sugira ações na conta; recomende o que verificar."
)

_METRICAS_COMPARADAS = ("investimento", "leadsMeta", "leadsCrm", "mqls")
# O que vai para a IA: so agregados e o ranking (o prompt nao cresce com o numero de anuncios).
CHAVES_IA = (
    "periodo", "ultimos7", "comparacao", "melhores", "piores", "cobertura",
    "horasPrimeiroContato", "alertasAbertos",
)


def hoje_local(agora: datetime | None = None) -> date:
    """Data de hoje em America/Sao_Paulo (`agora` naive = UTC)."""
    agora = agora or datetime.now(timezone.utc)
    if agora.tzinfo is None:
        agora = agora.replace(tzinfo=timezone.utc)
    return agora.astimezone(FUSO).date()


def periodo_anterior(hoje: date) -> tuple[date, date]:
    """Segunda-feira cobre sexta a domingo; os demais dias, so ontem."""
    if hoje.weekday() == 0:
        return hoje - timedelta(days=3), hoje - timedelta(days=1)
    ontem = hoje - timedelta(days=1)
    return ontem, ontem


def janela_base(hoje: date) -> tuple[date, date]:
    """Os 7 dias antes do periodo anterior: [ini-7, ini-1] (segunda: ini = sexta)."""
    ini, _ = periodo_anterior(hoje)
    return ini - timedelta(days=DIAS_ULTIMOS), ini - timedelta(days=1)


def _crescente(valor: float | None) -> tuple[int, float]:
    return (1, 0.0) if valor is None else (0, valor)


def _sem_lead(a: MetaAdsLinha) -> bool:
    return a.leadsMeta == 0 and a.leadsCrm == 0


def _chave_custo(a: MetaAdsLinha) -> tuple:
    """Custo por MQL crescente (sem MQL vai depois de todos com MQL), desempate por CPL."""
    return (_crescente(a.custoMql), _crescente(a.cpl))


def ranking(anuncios: list[MetaAdsLinha], gasto_min: float) -> tuple[list[MetaAdsLinha], list[MetaAdsLinha]]:
    """(melhores, piores), no maximo 3 cada, sem repeticao. So entra anuncio com gasto >= gasto_min.

    Melhores: anuncios com MQL ou com lead da Meta, pela `_chave_custo`. Piores: primeiro os sem
    lead (gasto decrescente); depois os com lead pelo inverso da mesma chave (custo por MQL
    decrescente, sem MQL antes de todos com MQL; desempate por CPL decrescente).
    """
    elegiveis = sorted((a for a in anuncios if a.investimento >= gasto_min), key=lambda a: a.id or 0)

    candidatos = [a for a in elegiveis if a.mqls > 0 or a.leadsMeta > 0]
    melhores = sorted(candidatos, key=_chave_custo)[:MAX_RANKING]
    usados = {id(a) for a in melhores}

    restantes = [a for a in elegiveis if id(a) not in usados]
    sem_lead = sorted((a for a in restantes if _sem_lead(a)), key=lambda a: -a.investimento)
    # reverse=True mantem a ordem por id entre empates (sort estavel).
    demais = sorted((a for a in restantes if not _sem_lead(a)), key=_chave_custo, reverse=True)
    piores = (sem_lead + demais)[:MAX_RANKING]
    return melhores, piores


def _totais(l: MetaAdsLinha) -> dict:
    return {
        "investimento": l.investimento,
        "impressoes": l.impressoes,
        "cliques": l.cliques,
        "leadsMeta": l.leadsMeta,
        "leadsCrm": l.leadsCrm,
        "mqls": l.mqls,
        "oportunidades": l.oportunidades,
        "vendas": l.vendas,
        "cpl": l.cpl,
        "custoMql": l.custoMql,
        "ctr": l.ctr,
    }


def _item(l: MetaAdsLinha) -> dict:
    return {"id": l.id, "mcgId": l.mcgId, "nome": l.nome, "status": l.status, **_totais(l)}


def _anuncios_da_arvore(linhas: list[MetaAdsLinha]) -> list[MetaAdsLinha]:
    achados: list[MetaAdsLinha] = []
    for l in linhas:
        if l.nivel == "anuncio":
            achados.append(l)
        achados += _anuncios_da_arvore(l.filhos)
    return achados


def _media_diaria(totais: dict, dias: int) -> dict:
    return {m: round(totais[m] / dias, 2) for m in _METRICAS_COMPARADAS}


def _variacao(atual: float, base: float) -> float | None:
    return round((atual - base) / base * 100, 1) if base else None


def contar_alertas_abertos(db: Session, emp_id: int) -> int:
    return db.execute(
        select(func.count())
        .select_from(MetaAdsAlerta)
        .where(MetaAdsAlerta.malEmpId == emp_id, MetaAdsAlerta.malStatus == STATUS_ABERTO)
    ).scalar_one()


def montar_dados(db: Session, emp_id: int, hoje: date) -> dict:
    ini, fim = periodo_anterior(hoje)
    ini7, fim7 = hoje - timedelta(days=DIAS_ULTIMOS), hoje - timedelta(days=1)
    ini_base, fim_base = janela_base(hoje)
    p_anterior = painel(db, emp_id, FiltroPainel(ini, fim))
    p_7 = painel(db, emp_id, FiltroPainel(ini7, fim7))
    p_base = painel(db, emp_id, FiltroPainel(ini_base, fim_base))

    dias_anterior = (fim - ini).days + 1
    t_anterior, t_7 = _totais(p_anterior.total), _totais(p_7.total)
    media_anterior = _media_diaria(t_anterior, dias_anterior)
    media_7 = _media_diaria(t_7, DIAS_ULTIMOS)
    media_base = _media_diaria(_totais(p_base.total), DIAS_ULTIMOS)

    anuncios = _anuncios_da_arvore(p_7.campanhas)
    gasto_min = float(obter_config(db, emp_id).mmcGastoMinRanking)
    melhores, piores = ranking(anuncios, gasto_min)

    return {
        "periodo": {
            "inicio": ini.isoformat(),
            "fim": fim.isoformat(),
            "dias": dias_anterior,
            **t_anterior,
            "cobertura": p_anterior.cobertura,
        },
        "ultimos7": {"inicio": ini7.isoformat(), "fim": fim7.isoformat(), "dias": DIAS_ULTIMOS, **t_7},
        "comparacao": {
            "base": {"inicio": ini_base.isoformat(), "fim": fim_base.isoformat(), "dias": DIAS_ULTIMOS},
            "mediaDiariaPeriodo": media_anterior,
            "mediaDiariaBase": media_base,
            "mediaDiariaUltimos7": media_7,
            "variacaoPct": {m: _variacao(media_anterior[m], media_base[m]) for m in _METRICAS_COMPARADAS},
        },
        "campanhas": [_item(c) for c in p_7.campanhas],
        "anuncios": [_item(a) for a in anuncios],
        "melhores": [_item(a) for a in melhores],
        "piores": [_item(a) for a in piores],
        "cobertura": p_7.cobertura,
        "horasPrimeiroContato": p_7.total.horasPrimeiroContato,
        "alertasAbertos": contar_alertas_abertos(db, emp_id),
    }


def _motivo(exc: Exception) -> str:
    texto = getattr(exc, "detail", None) or str(exc) or type(exc).__name__
    return " ".join(str(texto).split())[:150]


def _dados_para_ia(dados: dict) -> dict:
    return {k: dados[k] for k in CHAVES_IA if k in dados}


def gerar_leitura(dados: dict, provedor=None) -> tuple[str | None, str | None]:
    """(leitura, aviso). Qualquer falha (sem chave, erro da IA) vira (None, aviso)."""
    try:
        if provedor is None:
            from ..llm.llm_factory import get_scope_provider

            provedor = get_scope_provider()
        texto = provedor.chat_completion(
            [
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": json.dumps(_dados_para_ia(dados), ensure_ascii=False)},
            ],
            temperature=0.3,
        )
        texto = (texto or "").strip()
        if not texto:
            raise ValueError("resposta vazia")
        return texto, None
    except Exception as exc:
        logger.warning("Resumo Meta: leitura por IA indisponivel (%s)", type(exc).__name__)
        return None, f"{PREFIXO_AVISO}: {_motivo(exc)}"


def _resposta(r: MetaAdsResumo) -> MetaAdsResumoDiarioResponse:
    return MetaAdsResumoDiarioResponse(
        mrsId=r.mrsId,
        mrsData=r.mrsData,
        mrsInicio=r.mrsInicio,
        mrsFim=r.mrsFim,
        mrsDados=r.mrsDados,
        mrsLeitura=r.mrsLeitura,
        mrsAviso=r.mrsAviso,
        mrsGeradoEm=r.mrsGeradoEm,
    )


def _buscar(db: Session, emp_id: int, data: date) -> MetaAdsResumo | None:
    return db.execute(
        select(MetaAdsResumo).where(MetaAdsResumo.mrsEmpId == emp_id, MetaAdsResumo.mrsData == data)
    ).scalar_one_or_none()


def gerar(db: Session, emp_id: int, hoje: date, *, provedor=None) -> MetaAdsResumoDiarioResponse:
    """Gera (ou regera, substituindo) o resumo de `hoje` da empresa."""
    ini, fim = periodo_anterior(hoje)
    dados = montar_dados(db, emp_id, hoje)
    leitura, aviso = gerar_leitura(dados, provedor)
    resumo = _buscar(db, emp_id, hoje)
    if resumo is None:
        resumo = MetaAdsResumo(mrsEmpId=emp_id, mrsData=hoje)
        db.add(resumo)
    resumo.mrsInicio, resumo.mrsFim = ini, fim
    resumo.mrsDados = dados
    resumo.mrsLeitura = leitura
    resumo.mrsAviso = aviso
    resumo.mrsGeradoEm = utcnow()
    db.commit()
    return _resposta(resumo)


def _tem_conta_ativa(db: Session, emp_id: int) -> bool:
    return (
        db.execute(
            select(MetaAdsConta.macId)
            .where(MetaAdsConta.macEmpId == emp_id, MetaAdsConta.macAtivo.is_(True))
            .limit(1)
        ).first()
        is not None
    )


def gerar_se_devido(db: Session, emp_id: int, agora: datetime, *, provedor=None) -> bool:
    """Gera o resumo de hoje se for dia util, ja passou da hora configurada e ainda nao existe.

    `agora` com fuso (naive = UTC). O timer horario pode acordar alguns ms antes de hh:00, entao
    vale depois de 1 minuto antes da hora configurada (07:59:00 ainda nao; 07:59:00.001 sim).
    """
    if agora.tzinfo is None:
        agora = agora.replace(tzinfo=timezone.utc)
    local = agora.astimezone(FUSO)
    if local.weekday() > 4:
        return False
    hora = obter_config(db, emp_id).mmcHoraResumo
    alvo = local.replace(hour=hora, minute=0, second=0, microsecond=0)
    if local + TOLERANCIA <= alvo:  # estritamente depois de hh:00 menos 1 minuto
        return False
    hoje = local.date()
    if not _tem_conta_ativa(db, emp_id) or _buscar(db, emp_id, hoje) is not None:
        return False
    gerar(db, emp_id, hoje, provedor=provedor)
    return True


def listar(db: Session, emp_id: int, limite: int = 30) -> MetaAdsResumoDiarioListResponse:
    linhas = db.execute(
        select(MetaAdsResumo)
        .where(MetaAdsResumo.mrsEmpId == emp_id)
        .order_by(MetaAdsResumo.mrsData.desc())
        .limit(limite)
    ).scalars()
    return MetaAdsResumoDiarioListResponse(
        items=[MetaAdsResumoDiarioItem(mrsData=r.mrsData, mrsGeradoEm=r.mrsGeradoEm) for r in linhas]
    )


def obter(db: Session, emp_id: int, data: date | None) -> MetaAdsResumoDiarioResponse:
    """`data` None = o resumo mais recente."""
    if data is None:
        resumo = db.execute(
            select(MetaAdsResumo)
            .where(MetaAdsResumo.mrsEmpId == emp_id)
            .order_by(MetaAdsResumo.mrsData.desc())
            .limit(1)
        ).scalar_one_or_none()
    else:
        resumo = _buscar(db, emp_id, data)
    if resumo is None:
        raise NotFoundError("Resumo não encontrado")
    return _resposta(resumo)
