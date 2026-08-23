"""
Enfileiramento de eventos de saida -- o lado "escrita" do outbox transacional.

REGRA CENTRAL: `enfileirar` faz apenas db.add(). NUNCA commita. Ele e chamado de dentro
das funcoes de negocio, imediatamente antes do db.commit() que elas ja fazem, de modo
que o evento e a mudanca caem na MESMA transacao. Se o processo morrer no meio, ou os
dois existem ou nenhum existe.

POR QUE NAO UM LISTENER GLOBAL DE after_flush: seria tentador (zero call sites), mas
oportunidade_service._reativar_standby_vencidos muta oportunidades e COMMITA durante um
GET -- list_oportunidades e get_oportunidade o chamam. Um listener global passaria a
disparar webhooks a partir de endpoints de leitura. Os pontos de emissao sao explicitos
de proposito; nao "simplifique" isso.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from ..models.webhook_evento import WebhookEvento
from . import webhook_eventos, webhook_payload

logger = logging.getLogger(__name__)

CAMPOS_DE_CONTATO = ("opoNomeContato", "opoEmail", "opoTelefone", "opoEmpresaContato")


def enfileirar(
    db: Session,
    *,
    tipo: str,
    emp_id: int,
    oportunidade,
    anterior: Optional[dict] = None,
    origem: str = "ui",
    chave_idempotencia: Optional[str] = None,
) -> None:
    """Adiciona o evento a sessao corrente. Nao commita -- quem chama controla a transacao."""
    if not webhook_eventos.disponivel(tipo):
        logger.warning("Evento %s nao esta disponivel no catalogo; ignorado", tipo)
        return
    try:
        db.add(
            WebhookEvento(
                wevEmpId=emp_id,
                wevTipo=tipo,
                wevChaveIdempotencia=chave_idempotencia,
                wevOpoId=oportunidade.opoId,
                wevPayloadJson=webhook_payload.montar_deal(db, oportunidade, anterior),
                wevOrigem=origem,
                wevStatus="pendente",
            )
        )
    except Exception:
        # Um problema ao montar o payload nao pode derrubar a operacao de negocio.
        logger.exception("Falha ao enfileirar evento %s da oportunidade %s", tipo, oportunidade.opoId)


def tipo_para_status(status: str) -> Optional[str]:
    return {"ganho": "deal.won", "perdido": "deal.lost", "stand-by": "deal.standby"}.get(status)


def houve_mudanca_de_contato(valores: dict) -> bool:
    return any(campo in valores for campo in CAMPOS_DE_CONTATO)


def acordar_worker() -> None:
    """
    Cutuca o dispatcher para nao esperar o proximo poll.

    Best-effort: se o worker nao estiver rodando, o poll pega a linha do mesmo jeito.
    A corretude nunca depende desta chamada.
    """
    try:
        from ..workers import webhook_worker

        webhook_worker.acordar()
    except Exception:
        logger.debug("Worker de webhook nao esta ativo; entrega ficara para o proximo poll")
