"""Monta o corpo `data` dos eventos. Chaves em ingles, igual ao contrato de entrada."""

from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

VERSAO_API = "2026-08-01"


def _iso(valor) -> Optional[str]:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        # Os datetimes do banco sao naive em UTC; marcamos o Z explicitamente para o
        # consumidor nao supor horario local.
        return valor.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor)


def _num(valor) -> Optional[float]:
    if valor is None:
        return None
    if isinstance(valor, Decimal):
        return float(valor)
    return float(valor)


def _url_oportunidade(opo_id: int) -> Optional[str]:
    base = (os.getenv("VITE_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if not base or not urlparse(base).scheme:
        return None
    return base + "/oportunidades/" + str(opo_id)


def montar_deal(db: Session, oportunidade, anterior: Optional[dict] = None) -> dict:
    """
    Snapshot da oportunidade no momento do evento.

    Congelado de proposito: uma entrega retentada horas depois precisa reportar o que
    aconteceu, nao o estado atual do registro.
    """
    from ..models.etapa_kanban import EtapaKanban
    from ..models.usuario import Usuario

    etapa = db.get(EtapaKanban, oportunidade.opoEtkId) if oportunidade.opoEtkId else None
    dono = (
        db.get(Usuario, oportunidade.opoUsuResponsavelId)
        if oportunidade.opoUsuResponsavelId
        else None
    )

    dados: dict[str, Any] = {
        "object": "deal",
        "lead_id": "ld_" + str(oportunidade.opoId),
        "deal_id": oportunidade.opoId,
        "title": oportunidade.opoTitulo,
        "contact": {
            "name": oportunidade.opoNomeContato,
            "email": oportunidade.opoEmail,
            "phone": oportunidade.opoTelefone,
        },
        "company_name": oportunidade.opoEmpresaContato,
        "stage": (
            {
                "id": etapa.etkId,
                "name": etapa.etkNome,
                "pipeline": etapa.etkPipeline,
                "order": etapa.etkOrdem,
            }
            if etapa
            else None
        ),
        "status": oportunidade.opoStatusFechamento,
        "value": _num(oportunidade.opoValorOportunidade),
        "closed_value": _num(oportunidade.opoValorFechado),
        "recurring": not bool(oportunidade.opoReceitaPontual),
        "lead_score": oportunidade.opoLeadScore,
        "temperature": oportunidade.opoTemperatura,
        "owner": ({"id": dono.usuId, "name": dono.usuNome, "email": dono.usuEmail} if dono else None),
        "origin": {
            "source": oportunidade.opoOrigemSistema,
            "external_id": oportunidade.opoOrigemExternalId,
            "utm_source": oportunidade.opoUtmSource,
            "utm_medium": oportunidade.opoUtmMedium,
            "utm_campaign": oportunidade.opoUtmCampaign,
            "utm_content": oportunidade.opoUtmContent,
            "utm_term": oportunidade.opoUtmTerm,
        },
        "received_at": _iso(oportunidade.opoDataRecebimento),
        "closed_at": _iso(oportunidade.opoDataFechamento),
        "created_at": _iso(oportunidade.opoDataCriacao),
        "updated_at": _iso(oportunidade.opoDataAtualizacao),
        "url": _url_oportunidade(oportunidade.opoId),
    }
    if anterior:
        dados["previous_attributes"] = anterior
    return dados


def montar_envelope(evento_id: int, tipo: str, emp_id: int, criado_em, data: dict) -> dict:
    return {
        "id": "evt_" + str(evento_id).zfill(6),
        "type": tipo,
        "created_at": _iso(criado_em),
        "api_version": VERSAO_API,
        "company_id": emp_id,
        "data": data,
    }
