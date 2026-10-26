"""Configuracao do monitoramento de campanhas Meta (uma por empresa)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...core.tempo import utcnow
from ...exceptions import BadRequestError
from ...models.etapa_kanban import EtapaKanban
from ...models.meta_ads_monitor_config import MetaAdsMonitorConfig
from ...schemas.meta_ads import (
    ALERTAS_MONITOR,
    MetaAdsMonitorConfigResponse,
    MetaAdsMonitorConfigUpdate,
)

PIPELINE_PADRAO = "default"
NOME_ETAPA_MQL = "reunião de levantamento"
NOME_ETAPA_OPORTUNIDADE = "reunião de vendas"

_COLUNA_ALERTA = {
    "cpl": "mmcAlertaCpl",
    "gasto": "mmcAlertaGasto",
    "frequencia": "mmcAlertaFrequencia",
    "ctr": "mmcAlertaCtr",
    "parado": "mmcAlertaParado",
    "semContato": "mmcAlertaSemContato",
}

# campo do schema -> (coluna, converter para Decimal?)
_NUMERICOS = {
    "cplFator": ("mmcCplFator", True),
    "gastoSemLead": ("mmcGastoSemLead", True),
    "frequenciaMax": ("mmcFrequenciaMax", True),
    "gastoMinRanking": ("mmcGastoMinRanking", True),
    "quedaCtrPct": ("mmcQuedaCtrPct", False),
    "horasSemContato": ("mmcHorasSemContato", False),
    "horaResumo": ("mmcHoraResumo", False),
}


def _etapa_por_nome(db: Session, emp_id: int, nome: str) -> int | None:
    etapas = db.execute(
        select(EtapaKanban)
        .where(
            EtapaKanban.etkEmpId == emp_id,
            EtapaKanban.etkPipeline == PIPELINE_PADRAO,
            EtapaKanban.etkAtivo.is_(True),
        )
        .order_by(EtapaKanban.etkOrdem, EtapaKanban.etkId)
    ).scalars()
    for etapa in etapas:
        if " ".join(etapa.etkNome.split()).lower() == nome:
            return etapa.etkId
    return None


def _buscar(db: Session, emp_id: int) -> MetaAdsMonitorConfig | None:
    return db.execute(
        select(MetaAdsMonitorConfig).where(MetaAdsMonitorConfig.mmcEmpId == emp_id)
    ).scalar_one_or_none()


def obter_config(db: Session, emp_id: int) -> MetaAdsMonitorConfig:
    """Config da empresa; cria com os padroes (e as etapas achadas por nome) no primeiro acesso."""
    cfg = _buscar(db, emp_id)
    if cfg is not None:
        return cfg
    cfg = MetaAdsMonitorConfig(
        mmcEmpId=emp_id,
        mmcEtkMqlId=_etapa_por_nome(db, emp_id, NOME_ETAPA_MQL),
        mmcEtkOportunidadeId=_etapa_por_nome(db, emp_id, NOME_ETAPA_OPORTUNIDADE),
        mmcCplFator=Decimal("1.5"),
        mmcGastoSemLead=Decimal("150"),
        mmcFrequenciaMax=Decimal("3"),
        mmcQuedaCtrPct=30,
        mmcHorasSemContato=24,
        mmcGastoMinRanking=Decimal("50"),
        mmcHoraResumo=8,
        mmcSemContatoDesde=utcnow(),
    )
    db.add(cfg)
    try:
        db.commit()
    except IntegrityError:
        # Outra requisicao criou a config da empresa primeiro (mmcEmpId e unico).
        db.rollback()
        existente = _buscar(db, emp_id)
        if existente is None:
            raise
        return existente
    return cfg


def _resposta(cfg: MetaAdsMonitorConfig) -> MetaAdsMonitorConfigResponse:
    return MetaAdsMonitorConfigResponse(
        etapaMqlId=cfg.mmcEtkMqlId,
        etapaOportunidadeId=cfg.mmcEtkOportunidadeId,
        cplFator=float(cfg.mmcCplFator),
        gastoSemLead=float(cfg.mmcGastoSemLead),
        frequenciaMax=float(cfg.mmcFrequenciaMax),
        quedaCtrPct=cfg.mmcQuedaCtrPct,
        horasSemContato=cfg.mmcHorasSemContato,
        gastoMinRanking=float(cfg.mmcGastoMinRanking),
        horaResumo=cfg.mmcHoraResumo,
        alertas={chave: bool(getattr(cfg, _COLUNA_ALERTA[chave])) for chave in ALERTAS_MONITOR},
    )


def config_resposta(db: Session, emp_id: int) -> MetaAdsMonitorConfigResponse:
    return _resposta(obter_config(db, emp_id))


def _validar_etapa(db: Session, emp_id: int, etk_id: int | None) -> None:
    if etk_id is None:
        return
    existe = db.execute(
        select(EtapaKanban.etkId).where(
            EtapaKanban.etkId == etk_id,
            EtapaKanban.etkEmpId == emp_id,
            EtapaKanban.etkPipeline == PIPELINE_PADRAO,
            EtapaKanban.etkAtivo.is_(True),
        )
    ).first()
    if existe is None:
        raise BadRequestError("Estágio inválido para esta empresa")


def atualizar_config(
    db: Session, emp_id: int, data: MetaAdsMonitorConfigUpdate
) -> MetaAdsMonitorConfigResponse:
    cfg = obter_config(db, emp_id)
    enviados = data.model_fields_set

    # Valida tudo antes de alterar o objeto, para um erro nao deixar meia atualizacao.
    if "etapaMqlId" in enviados:
        _validar_etapa(db, emp_id, data.etapaMqlId)
    if "etapaOportunidadeId" in enviados:
        _validar_etapa(db, emp_id, data.etapaOportunidadeId)

    if "etapaMqlId" in enviados:
        cfg.mmcEtkMqlId = data.etapaMqlId
    if "etapaOportunidadeId" in enviados:
        cfg.mmcEtkOportunidadeId = data.etapaOportunidadeId

    for campo, (coluna, como_decimal) in _NUMERICOS.items():
        valor = getattr(data, campo)
        if valor is not None:
            setattr(cfg, coluna, Decimal(str(valor)) if como_decimal else valor)

    for chave, ligado in (data.alertas or {}).items():
        if chave == "semContato" and ligado and not cfg.mmcAlertaSemContato:
            cfg.mmcSemContatoDesde = utcnow()
        setattr(cfg, _COLUNA_ALERTA[chave], ligado)

    db.commit()
    return _resposta(cfg)
