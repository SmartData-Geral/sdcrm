"""
Worker da sincronizacao diaria do Meta Ads: task asyncio iniciada no lifespan, no mesmo
modelo do webhook_worker (processo unico, trabalho pesado na threadpool).

So cuida da rodada agendada. O "Sincronizar agora" da tela roda em BackgroundTasks do
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
_task: asyncio.Task | None = None


def segundos_ate_proxima(agora: datetime, hora: int) -> float:
    """`agora` com fuso. Proxima ocorrencia de hora:00 em Sao Paulo, sempre no futuro."""
    local = agora.astimezone(FUSO)
    alvo = local.replace(hour=hora, minute=0, second=0, microsecond=0)
    if alvo <= local:
        alvo += timedelta(days=1)
    return (alvo - local).total_seconds()


def _ciclo() -> None:
    from ..services.meta_ads import sincronizacao

    rodadas = sincronizacao.sincronizar_todas_agendadas()
    logger.info("Meta Ads: rodada diaria concluida (%s contas)", rodadas)


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
    global _task
    if not settings.META_ADS_SYNC_ENABLED:
        logger.info("Worker Meta Ads desabilitado por configuracao")
        return
    _parar.clear()
    _task = asyncio.create_task(_loop_principal())


async def parar() -> None:
    global _task
    if _task is None:
        return
    _parar.set()
    with contextlib.suppress(asyncio.TimeoutError, asyncio.CancelledError):
        await asyncio.wait_for(_task, timeout=10)
    _task = None
