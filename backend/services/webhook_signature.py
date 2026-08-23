"""
Assinatura HMAC das entregas e politica de retry.

Tudo aqui e funcao pura: nenhuma sessao de banco, nenhum I/O. E o que permite testar a
assinatura contra um vetor conhecido e o backoff contra uma tabela.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

PREFIXO_SEGREDO = "whsec_"
TOLERANCIA_REPLAY_SEGUNDOS = 300

# 7 tentativas, cobrindo ~31 horas.
BACKOFF_SEGUNDOS: tuple[int, ...] = (30, 120, 600, 3600, 21600, 86400)

# 3xx nao e seguido: um redirect e vetor de exfiltracao do payload assinado.
STATUS_RETENTAVEIS = frozenset({408, 429, 500, 502, 503, 504, 507, 509})


def gerar_segredo() -> str:
    return PREFIXO_SEGREDO + secrets.token_urlsafe(32)


def assinar(segredo: str, timestamp: int, corpo: bytes) -> str:
    """
    Esquema do Stripe: HMAC-SHA256 sobre "<timestamp>." + corpo bruto.

    O corpo tem de ser exatamente os bytes que serao enviados. Serializar de novo entre
    assinar e enviar muda ordem de chaves ou espacos e quebra silenciosamente todos os
    consumidores.
    """
    base = str(timestamp).encode("ascii") + b"." + corpo
    return hmac.new(segredo.encode("utf-8"), base, hashlib.sha256).hexdigest()


def cabecalho_assinatura(segredo: str, timestamp: int, corpo: bytes) -> str:
    return "v1=" + assinar(segredo, timestamp, corpo)


def cabecalho_rotacao(segredo_novo: str, segredo_antigo: str, timestamp: int, corpo: bytes) -> str:
    """Durante a janela de rotacao mandamos as duas; o consumidor aceita qualquer uma."""
    return (
        "v1="
        + assinar(segredo_novo, timestamp, corpo)
        + ",v1="
        + assinar(segredo_antigo, timestamp, corpo)
    )


def verificar_assinatura(
    segredo: str, cabecalho: str, timestamp: int, corpo: bytes, agora: int
) -> bool:
    """
    Referencia para o consumidor -- e o que documentamos em INTEGRACAO_API.md.

    Rejeita fora da janela de tolerancia para impedir replay.
    """
    if abs(agora - timestamp) > TOLERANCIA_REPLAY_SEGUNDOS:
        return False
    esperado = assinar(segredo, timestamp, corpo)
    for parte in (cabecalho or "").split(","):
        parte = parte.strip()
        if parte.startswith("v1=") and hmac.compare_digest(parte[3:], esperado):
            return True
    return False


def deve_retentar(status_http: int | None, houve_excecao: bool) -> bool:
    """Erro de rede e 5xx/429 sao transitorios; 4xx e contrato quebrado do consumidor."""
    if houve_excecao:
        return True
    if status_http is None:
        return True
    if 200 <= status_http < 300:
        return False
    return status_http in STATUS_RETENTAVEIS


def proxima_tentativa(
    tentativa: int, agora: datetime, retry_after_segundos: int | None = None
) -> datetime | None:
    """
    Momento da proxima tentativa, ou None quando o limite foi atingido.

    `tentativa` e quantas ja ocorreram. Honra Retry-After quando ele for MENOR que o
    backoff calculado -- respeitar um valor maior deixaria o consumidor adiar para sempre.
    """
    if tentativa < 1 or tentativa > len(BACKOFF_SEGUNDOS):
        return None
    espera = BACKOFF_SEGUNDOS[tentativa - 1]
    if retry_after_segundos is not None and 0 < retry_after_segundos < espera:
        espera = retry_after_segundos
    return agora + timedelta(seconds=espera)


def esgotou(tentativa: int) -> bool:
    return tentativa > len(BACKOFF_SEGUNDOS)
