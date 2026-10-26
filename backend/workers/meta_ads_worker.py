"""
Worker da sincronizacao diaria do Meta Ads: task asyncio iniciada no lifespan, no mesmo
modelo do webhook_worker (processo unico, trabalho pesado na threadpool).

Dois lacos: a rodada diaria (sync + alertas diarios) e a avaliacao de hora em hora dos
alertas "parado" e "sem contato". O "Sincronizar agora" da tela roda em BackgroundTasks do
FastAPI, com a trava pega na propria requisicao.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from starlette.concurrency import run_in_threadpool

from ..config import settings

logger = logging.getLogger(__name__)

FUSO = ZoneInfo("America/Sao_Paulo")

_parar = asyncio.Event()
_tasks: list[asyncio.Task] = []


def segundos_ate_proxima(agora: datetime, hora: int) -> float:
    """`agora` com fuso. Proxima ocorrencia de hora:00 em Sao Paulo, sempre no futuro."""
    local = agora.astimezone(FUSO)
    alvo = local.replace(hour=hora, minute=0, second=0, microsecond=0)
    if alvo <= local:
        alvo += timedelta(days=1)
    return (alvo - local).total_seconds()


def segundos_ate_proxima_hora(agora: datetime) -> float:
    """Segundos ate a proxima hora cheia (hh:00:00), sempre no futuro."""
    alvo = agora.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return (alvo - agora).total_seconds()


def _ciclo() -> None:
    from ..services.meta_ads import alertas, sincronizacao

    rodadas = sincronizacao.sincronizar_todas_agendadas()
    logger.info("Meta Ads: rodada diaria concluida (%s contas)", rodadas)
    empresas = alertas.avaliar_diarios_todas(datetime.now(FUSO).date())
    logger.info("Meta Ads: alertas diarios avaliados (%s empresas)", empresas)


def _ciclo_horario() -> None:
    from ..services.meta_ads import alertas

    empresas = alertas.avaliar_horarios_todas(datetime.now(timezone.utc))
    logger.info("Meta Ads: alertas de hora em hora avaliados (%s empresas)", empresas)


async def _loop_horario() -> None:
    while not _parar.is_set():
        espera = segundos_ate_proxima_hora(datetime.now(timezone.utc))
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(_parar.wait(), timeout=espera)
        if _parar.is_set():
            break
        try:
            await run_in_threadpool(_ciclo_horario)
        except Exception:
            logger.exception("Falha na avaliacao de hora em hora dos alertas Meta Ads")


async def _loop_principal() -> None:
    logger.info("Worker Meta Ads iniciado (rodada diaria as %sh)", settings.META_ADS_SYNC_HORA)
    while not _parar.is_set():
        espera = segundos_ate_proxima(datetime.now(timezone.utc), settings.META_ADS_SYNC_HORA)
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(_parar.wait(), timeout=espera)
        if _parar.is_set():
            break
        try:
            await run_in_threadpool(_ciclo)
        except Exception:
            logger.exception("Falha na rodada diaria do Meta Ads")
    logger.info("Worker Meta Ads encerrado")


async def iniciar() -> None:
    if not settings.META_ADS_SYNC_ENABLED:
        logger.info("Worker Meta Ads desabilitado por configuracao")
        return
    _parar.clear()
    _tasks.extend([asyncio.create_task(_loop_principal()), asyncio.create_task(_loop_horario())])


async def parar() -> None:
    if not _tasks:
        return
    _parar.set()
    for task in _tasks:
        with contextlib.suppress(asyncio.TimeoutError, asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=10)
    _tasks.clear()
