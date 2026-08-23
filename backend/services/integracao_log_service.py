"""
Log das requisições à superfície externa (/api/v1/*).

Grava também o que nunca chega ao service: 401 levantado na dependency e 422 do
Pydantic. Nada aqui pode derrubar a requisição -- uma falha de log jamais deve
custar um lead.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.tempo import utcnow
from ..database import SessionLocal
from ..models.integracao_requisicao_log import IntegracaoRequisicaoLog

logger = logging.getLogger(__name__)

# Allowlist, não denylist. É isso que impede que alguém que cole um token num campo
# inesperado do corpo acabe tendo esse token persistido no log.
CAMPOS_PERMITIDOS = (
    "source",
    "external_id",
    "name",
    "company",
    "email",
    "phone",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "notes",
    "owner_email",
    "value",
    "origem",
    "nome",
    "empresa",
    "telefone",
    "observacoes",
)

LIMITE_PAYLOAD_BYTES = 8192
LIMITE_NOTES = 2000
LIMITE_USER_AGENT = 600

_SO_DIGITOS = re.compile(r"\D+")


def _mascarar_email(valor: str) -> str:
    local, _, dominio = valor.partition("@")
    if not dominio:
        return (local[:2] + "***") if local else "***"
    return f"{local[:2]}***@{dominio}"


def _mascarar_telefone(valor: str) -> str:
    digitos = _SO_DIGITOS.sub("", valor)
    if len(digitos) <= 4:
        return "*" * len(digitos)
    return "*" * (len(digitos) - 4) + digitos[-4:]


def redigir_payload(dados: Any) -> dict | None:
    """
    Reduz o corpo recebido ao que pode ser guardado: só campos da allowlist, com
    e-mail e telefone mascarados. Os valores reais já vivem na oportunidade, e
    irlOpoId aponta para lá -- este log existe para depurar integração, não para
    virar uma segunda base de contatos.
    """
    if not isinstance(dados, dict):
        return {"_tipo_invalido": type(dados).__name__} if dados is not None else None

    completo = bool(settings.INTEGRACAO_LOG_PAYLOAD_COMPLETO)
    saida: dict[str, Any] = {}
    extras: list[str] = []

    for chave, valor in dados.items():
        if chave not in CAMPOS_PERMITIDOS:
            extras.append(str(chave)[:60])
            continue
        if valor is None:
            continue
        if isinstance(valor, str):
            texto = valor.strip()
            if not texto:
                continue
            if not completo and chave in ("email", "owner_email"):
                texto = _mascarar_email(texto)
            elif not completo and chave in ("phone", "telefone"):
                texto = _mascarar_telefone(texto)
            elif chave in ("notes", "observacoes"):
                texto = texto[:LIMITE_NOTES]
            saida[chave] = texto[:500] if chave not in ("notes", "observacoes") else texto
        else:
            saida[chave] = valor

    if extras:
        # Só os NOMES das chaves desconhecidas, nunca os valores.
        saida["_extras"] = sorted(set(extras))[:30]

    serializado = json.dumps(saida, ensure_ascii=False, default=str)
    if len(serializado.encode("utf-8")) > LIMITE_PAYLOAD_BYTES:
        saida = {"_truncado": True, "_bytes": len(serializado.encode("utf-8"))}
    return saida or None


def registrar(
    db: Session,
    *,
    rota: str,
    metodo: str,
    status_http: int,
    resultado: str,
    emp_id: Optional[int] = None,
    ich_id: Optional[int] = None,
    prefixo_informado: Optional[str] = None,
    origem_sistema: Optional[str] = None,
    external_id: Optional[str] = None,
    opo_id: Optional[int] = None,
    payload: Any = None,
    erro: Any = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    duracao_ms: Optional[int] = None,
) -> None:
    """
    Grava uma linha de log com commit próprio, separado do commit de negócio.

    Envolvido em try/except de propósito: uma indisponibilidade da tabela de log não
    pode transformar um 201 em 500 nem desfazer o lead que acabou de entrar.
    """
    try:
        linha = IntegracaoRequisicaoLog(
            irlEmpId=emp_id,
            irlIchId=ich_id,
            irlPrefixoInformado=(prefixo_informado or None),
            irlRota=rota[:120],
            irlMetodo=metodo[:10],
            irlOrigemSistema=(origem_sistema or None),
            irlExternalId=(external_id or None),
            irlStatusHttp=status_http,
            irlResultado=resultado[:20],
            irlOpoId=opo_id,
            irlPayloadJson=redigir_payload(payload),
            irlErroJson=erro,
            irlIp=(ip or None),
            irlUserAgent=(user_agent or None) and user_agent[:LIMITE_USER_AGENT],
            irlDuracaoMs=duracao_ms,
            irlDataCriacao=utcnow(),
        )
        db.add(linha)
        db.commit()
    except Exception:
        logger.exception("Falha ao registrar log de integração (requisição preservada)")
        try:
            db.rollback()
        except Exception:
            pass


def registrar_isolado(**kwargs) -> None:
    """
    Versão para quem não tem uma Session à mão -- em especial o exception handler de
    422, que roda depois de o `get_db` da rota já ter sido encerrado.
    """
    try:
        with SessionLocal() as db:
            registrar(db, **kwargs)
    except Exception:
        logger.exception("Falha ao registrar log isolado de integração")


def listar(
    db: Session,
    *,
    company_id: Optional[int] = None,
    resultado: Optional[str] = None,
    ich_id: Optional[int] = None,
    origem: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[IntegracaoRequisicaoLog], int]:
    stmt = select(IntegracaoRequisicaoLog)
    if company_id is not None:
        stmt = stmt.where(IntegracaoRequisicaoLog.irlEmpId == company_id)
    if resultado:
        stmt = stmt.where(IntegracaoRequisicaoLog.irlResultado == resultado)
    if ich_id is not None:
        stmt = stmt.where(IntegracaoRequisicaoLog.irlIchId == ich_id)
    if origem:
        stmt = stmt.where(IntegracaoRequisicaoLog.irlOrigemSistema == origem)
    stmt = stmt.order_by(IntegracaoRequisicaoLog.irlDataCriacao.desc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt).all()), total


def expurgar(db: Session, dias: Optional[int] = None) -> int:
    """Remove logs além da retenção. O log guarda PII de lead -- a retenção é o controle."""
    from datetime import timedelta

    limite = dias if dias is not None else settings.INTEGRACAO_LOG_RETENCAO_DIAS
    corte = utcnow() - timedelta(days=int(limite))
    resultado = db.execute(
        delete(IntegracaoRequisicaoLog).where(IntegracaoRequisicaoLog.irlDataCriacao < corte)
    )
    db.commit()
    return int(resultado.rowcount or 0)
