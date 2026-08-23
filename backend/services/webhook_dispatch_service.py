"""
Dispatcher: transforma eventos do outbox em entregas e as envia.

Sincrono de ponta a ponta -- SQLAlchemy e httpx sincronos, igual ao resto do projeto.
Quem chama e responsavel por rodar isto FORA do event loop (ver workers/webhook_worker).
"""

from __future__ import annotations

import json
import logging
import os
import socket
from datetime import timedelta

import httpx
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from ..config import settings
from ..core.tempo import utcnow
from ..database import SessionLocal
from ..models.webhook_assinatura import WebhookAssinatura
from ..models.webhook_entrega import WebhookEntrega
from ..models.webhook_evento import WebhookEvento
from . import webhook_assinatura_service, webhook_payload, webhook_signature

logger = logging.getLogger(__name__)

IDENTIDADE = socket.gethostname()[:60] + ":" + str(os.getpid())
LIMITE_RESPOSTA = 2000


def processar_lote() -> dict:
    """Um ciclo completo. Devolve contadores para o log do worker."""
    resultado = {"fanout": 0, "enviadas": 0, "falhas": 0}
    with SessionLocal() as db:
        resultado["fanout"] = _fan_out(db)
        _recuperar_claims_orfas(db)
    entregas = _reivindicar_entregas()
    for wen_id in entregas:
        with SessionLocal() as db:
            if _entregar(db, wen_id):
                resultado["enviadas"] += 1
            else:
                resultado["falhas"] += 1
    return resultado


def _fan_out(db: Session) -> int:
    """
    Cria uma entrega por (evento x assinatura inscrita).

    Separar o fan-out do envio garante que uma assinatura criada hoje nao receba eventos
    antigos, e que um endpoint lento nao trave a distribuicao dos demais.
    """
    eventos = list(
        db.scalars(
            select(WebhookEvento)
            .where(WebhookEvento.wevStatus == "pendente")
            .order_by(WebhookEvento.wevDataCriacao.asc())
            .limit(settings.WEBHOOK_BATCH_SIZE)
            .with_for_update(skip_locked=True)
        ).all()
    )
    if not eventos:
        return 0

    criadas = 0
    for evento in eventos:
        assinaturas = list(
            db.scalars(
                select(WebhookAssinatura).where(
                    WebhookAssinatura.whaEmpId == evento.wevEmpId,
                    WebhookAssinatura.whaAtivo.is_(True),
                )
            ).all()
        )
        for assinatura in assinaturas:
            if evento.wevTipo not in (assinatura.whaEventosJson or []):
                continue
            db.add(
                WebhookEntrega(
                    wenEmpId=evento.wevEmpId,
                    wenWevId=evento.wevId,
                    wenWhaId=assinatura.whaId,
                    wenStatus="pendente",
                    wenProximaTentativaEm=utcnow(),
                )
            )
            criadas += 1
        evento.wevStatus = "processado"
        evento.wevProcessadoEm = utcnow()
        db.add(evento)
    db.commit()
    return criadas


def _recuperar_claims_orfas(db: Session) -> None:
    """Devolve a fila as entregas reivindicadas por um processo que morreu."""
    corte = utcnow() - timedelta(minutes=settings.WEBHOOK_CLAIM_TIMEOUT_MINUTOS)
    db.execute(
        text(
            "UPDATE webhook_entrega SET wenClaimedPor = NULL, wenClaimedEm = NULL "
            "WHERE wenClaimedEm IS NOT NULL AND wenClaimedEm < :corte "
            "AND wenStatus IN ('pendente', 'retentando')"
        ),
        {"corte": corte},
    )
    db.commit()


def _reivindicar_entregas() -> list:
    """
    Marca um lote como nosso e devolve os ids.

    SKIP LOCKED (MySQL 8) torna N workers concorrentes corretos -- no maximo um pouco
    redundantes -- caso um dia rodem varias replicas.
    """
    agora = utcnow()
    with SessionLocal() as db:
        linhas = list(
            db.scalars(
                select(WebhookEntrega)
                .where(
                    WebhookEntrega.wenStatus.in_(("pendente", "retentando")),
                    WebhookEntrega.wenProximaTentativaEm <= agora,
                    WebhookEntrega.wenClaimedPor.is_(None),
                )
                .order_by(WebhookEntrega.wenProximaTentativaEm.asc())
                .limit(settings.WEBHOOK_BATCH_SIZE)
                .with_for_update(skip_locked=True)
            ).all()
        )
        ids = []
        for linha in linhas:
            linha.wenClaimedPor = IDENTIDADE
            linha.wenClaimedEm = agora
            db.add(linha)
            ids.append(linha.wenId)
        db.commit()
        return ids


def _retry_after(resposta) -> int | None:
    valor = (resposta.headers.get("retry-after") or "").strip() if resposta is not None else ""
    if valor.isdigit():
        return int(valor)
    return None


def _entregar(db: Session, wen_id: int) -> bool:
    entrega = db.get(WebhookEntrega, wen_id)
    if entrega is None or entrega.wenStatus in ("entregue", "falha_permanente", "cancelada"):
        return False
    assinatura = db.get(WebhookAssinatura, entrega.wenWhaId)
    evento = db.get(WebhookEvento, entrega.wenWevId)
    if assinatura is None or evento is None:
        entrega.wenStatus = "cancelada"
        entrega.wenUltimoErro = "Assinatura ou evento removido."
        entrega.wenClaimedPor = None
        db.add(entrega)
        db.commit()
        return False

    envelope = webhook_payload.montar_envelope(
        evento.wevId, evento.wevTipo, evento.wevEmpId, evento.wevDataCriacao, evento.wevPayloadJson
    )
    # Serializa UMA vez e assina exatamente estes bytes. Reserializar entre assinar e
    # enviar mudaria ordem de chaves ou espacos e quebraria todos os consumidores.
    corpo = json.dumps(envelope, ensure_ascii=False, default=str).encode("utf-8")
    agora = utcnow()
    timestamp = int(agora.timestamp())

    cabecalhos = {
        "Content-Type": "application/json",
        "User-Agent": "SDCRM-Webhooks/1.0",
        "X-SDCRM-Event": evento.wevTipo,
        "X-SDCRM-Event-Id": envelope["id"],
        "X-SDCRM-Delivery-Id": "dlv_" + str(entrega.wenId).zfill(6),
        "X-SDCRM-Timestamp": str(timestamp),
        "X-SDCRM-Signature": webhook_signature.cabecalho_assinatura(
            assinatura.whaSegredo, timestamp, corpo
        ),
    }
    for chave, valor in (assinatura.whaHeadersJson or {}).items():
        cabecalhos.setdefault(str(chave), str(valor))

    entrega.wenTentativas += 1
    entrega.wenUltimaTentativaEm = agora
    status_http = None
    houve_excecao = False
    erro = None
    resposta = None
    inicio = utcnow()

    try:
        # Revalida o destino a cada envio: o DNS pode ter mudado desde o cadastro.
        webhook_assinatura_service.validar_url_destino(assinatura.whaUrl)
        with httpx.Client(
            timeout=httpx.Timeout(settings.WEBHOOK_TIMEOUT_SECONDS, connect=5.0),
            follow_redirects=False,  # 3xx e vetor de exfiltracao do payload assinado
        ) as cliente:
            resposta = cliente.post(assinatura.whaUrl, content=corpo, headers=cabecalhos)
        status_http = resposta.status_code
        entrega.wenRespostaTrecho = (resposta.text or "")[:LIMITE_RESPOSTA]
    except Exception as exc:
        houve_excecao = True
        erro = type(exc).__name__ + ": " + str(exc)[:400]

    entrega.wenDuracaoMs = int((utcnow() - inicio).total_seconds() * 1000)
    entrega.wenUltimoStatusHttp = status_http
    entrega.wenUltimoErro = erro
    entrega.wenClaimedPor = None
    entrega.wenClaimedEm = None

    historico = list(entrega.wenHistoricoJson or [])
    historico.append(
        {
            "tentativa": entrega.wenTentativas,
            "em": agora.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": status_http,
            "ms": entrega.wenDuracaoMs,
            "erro": erro,
        }
    )
    entrega.wenHistoricoJson = historico[-20:]

    sucesso = status_http is not None and 200 <= status_http < 300
    assinatura.whaUltimaEntregaEm = agora
    assinatura.whaUltimoStatusHttp = status_http

    if sucesso:
        entrega.wenStatus = "entregue"
        entrega.wenDataEntrega = agora
        entrega.wenProximaTentativaEm = None
        assinatura.whaFalhasConsecutivas = 0
    else:
        assinatura.whaFalhasConsecutivas = (assinatura.whaFalhasConsecutivas or 0) + 1
        if not webhook_signature.deve_retentar(status_http, houve_excecao):
            # 4xx (fora 408/429) e 3xx: contrato quebrado do consumidor, retentar nao resolve.
            entrega.wenStatus = "falha_permanente"
            entrega.wenProximaTentativaEm = None
        else:
            proxima = webhook_signature.proxima_tentativa(
                entrega.wenTentativas, agora, _retry_after(resposta)
            )
            if proxima is None:
                entrega.wenStatus = "falha_permanente"
                entrega.wenProximaTentativaEm = None
            else:
                entrega.wenStatus = "retentando"
                entrega.wenProximaTentativaEm = proxima
        if assinatura.whaFalhasConsecutivas >= settings.WEBHOOK_MAX_FALHAS_DESATIVAR:
            webhook_assinatura_service.desativar_por_falhas(db, assinatura)

    db.add(entrega)
    db.add(assinatura)
    db.commit()  # commit por linha: uma entrega ruim nao pode perder o lote inteiro
    return sucesso


def expurgar(db: Session) -> int:
    corte = utcnow() - timedelta(days=settings.WEBHOOK_RETENCAO_DIAS)
    removidas = db.execute(
        delete(WebhookEntrega).where(
            WebhookEntrega.wenStatus == "entregue", WebhookEntrega.wenDataCriacao < corte
        )
    ).rowcount
    db.execute(
        delete(WebhookEvento).where(
            WebhookEvento.wevStatus == "processado", WebhookEvento.wevDataCriacao < corte
        )
    )
    db.commit()
    return int(removidas or 0)
