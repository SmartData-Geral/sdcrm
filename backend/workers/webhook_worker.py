"""
Worker de entrega de webhooks: uma task asyncio iniciada no lifespan do FastAPI.

POR QUE AQUI E NAO NUM CONTAINER SEPARADO: o backend sobe um unico processo uvicorn, sem
--workers (ver backend/Dockerfile), entao nao ha duplicacao. Um segundo container exigiria
mexer no docker-compose e no deploy manual, sem ganho imediato. A flag
WEBHOOK_WORKER_ENABLED existe justamente para permitir essa extracao depois sem tocar em
codigo.

POR QUE run_in_threadpool: o stack ORM deste projeto e SINCRONO. Rodar SQLAlchemy e httpx
sincronos direto no event loop bloquearia TODA requisicao HTTP durante cada envio. O loop
asyncio aqui so cuida do tempo; o trabalho vai para a threadpool.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import timedelta

from starlette.concurrency import run_in_threadpool

from ..config import settings
from ..core.tempo import utcnow

logger = logging.getLogger(__name__)

_parar = asyncio.Event()
_acordar = asyncio.Event()
_task: asyncio.Task | None = None
_loop: asyncio.AbstractEventLoop | None = None
_ultimo_expurgo = None


def acordar() -> None:
    """
    Cutucada best-effort vinda da thread da requisicao.

    call_soon_threadsafe porque quem chama esta numa thread de worker do uvicorn, nao no
    event loop. Se nada estiver rodando, o proximo poll pega a entrega do mesmo jeito --
    a corretude nunca depende disto.
    """
    if _loop is None or _loop.is_closed():
        return
    with contextlib.suppress(RuntimeError):
        _loop.call_soon_threadsafe(_acordar.set)


def _ciclo() -> None:
    from ..database import SessionLocal
    from ..services import integracao_log_service, webhook_dispatch_service

    global _ultimo_expurgo

    resultado = webhook_dispatch_service.processar_lote()
    if any(resultado.values()):
        logger.info("webhooks: %s", resultado)

    agora = utcnow()
    if _ultimo_expurgo is None or agora - _ultimo_expurgo > timedelta(hours=1):
        _ultimo_expurgo = agora
        with SessionLocal() as db:
            removidas = webhook_dispatch_service.expurgar(db)
            removidos_log = integracao_log_service.expurgar(db)
        if removidas or removidos_log:
            logger.info("expurgo: %s entregas, %s logs", removidas, removidos_log)


async def _loop_principal() -> None:
    logger.info("Worker de webhooks iniciado (intervalo %ss)", settings.WEBHOOK_POLL_INTERVAL_SECONDS)
    while not _parar.is_set():
        try:
            await run_in_threadpool(_ciclo)
        except Exception:
            logger.exception("Falha no ciclo do dispatcher de webhooks")
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(
                _acordar.wait(), timeout=settings.WEBHOOK_POLL_INTERVAL_SECONDS
            )
        _acordar.clear()
    logger.info("Worker de webhooks encerrado")


async def iniciar() -> None:
    global _task, _loop
    if not settings.WEBHOOK_WORKER_ENABLED:
        logger.info("Worker de webhooks desabilitado por configuracao")
        return
    _parar.clear()
    _acordar.clear()
    _loop = asyncio.get_running_loop()
    _task = asyncio.create_task(_loop_principal())


async def parar() -> None:
    global _task
    if _task is None:
        return
    _parar.set()
    _acordar.set()
    with contextlib.suppress(asyncio.TimeoutError, asyncio.CancelledError):
        await asyncio.wait_for(_task, timeout=10)
    _task = None
