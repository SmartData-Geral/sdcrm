"""
Meta Ads: configuracao das contas (admin) e, na Task 8, indicadores das campanhas.

Rotas internas em portugues, JWT + X-Company-Id. Toda rota exige empresa selecionada.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Query, status

from ..dependencies import (
    CompanyIdDep,
    CurrentUserDep,
    DbSessionDep,
    require_admin,
    require_user_in_company,
)
from ..exceptions import BadRequestError, ConflictError
from ..schemas.meta_ads import (
    MetaAdsAlertaListResponse,
    MetaAdsAlertaResponse,
    MetaAdsCampanhaDetalheResponse,
    MetaAdsCampanhaOpcoesResponse,
    MetaAdsCockpitResponse,
    MetaAdsContaOpcoesResponse,
    MetaAdsMonitorConfigResponse,
    MetaAdsMonitorConfigUpdate,
    MetaAdsPainelResponse,
    MetaAdsResumoDiarioListResponse,
    MetaAdsResumoDiarioResponse,
    MetaAdsResumoResponse,
    OportunidadeCampanhaMetaRequest,
    OportunidadeCampanhaMetaResponse,
    MetaAdsContaCreate,
    MetaAdsContaListResponse,
    MetaAdsContaResponse,
    MetaAdsContaUpdate,
    MetaAdsSyncIniciadaResponse,
    MetaAdsSyncLogListResponse,
    MetaAdsSyncPeriodoRequest,
    MetaAdsTesteResponse,
)
from ..services.meta_ads import alertas, cockpit as cockpit_servico, config_monitor, contas, indicadores, resumo as resumo_diario, sincronizacao

router = APIRouter(prefix="/api/meta-ads", tags=["meta-ads"])


def empresa_obrigatoria(db, current_user, company_id) -> int:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    if company_id is None:
        raise BadRequestError("Selecione uma empresa")
    return company_id


def _admin(db, current_user, company_id) -> int:
    require_admin(current_user)
    return empresa_obrigatoria(db, current_user, company_id)


@router.get("/contas", response_model=MetaAdsContaListResponse)
def listar_contas(
    db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> MetaAdsContaListResponse:
    return contas.listar_contas(db, _admin(db, current_user, company_id))


@router.post("/contas", response_model=MetaAdsContaResponse, status_code=status.HTTP_201_CREATED)
def criar_conta(
    data: MetaAdsContaCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> MetaAdsContaResponse:
    return contas.criar_conta(db, _admin(db, current_user, company_id), data)


@router.put("/contas/{mac_id}", response_model=MetaAdsContaResponse)
def atualizar_conta(
    mac_id: int,
    data: MetaAdsContaUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> MetaAdsContaResponse:
    return contas.atualizar_conta(db, _admin(db, current_user, company_id), mac_id, data)


@router.post("/contas/{mac_id}/testar", response_model=MetaAdsTesteResponse)
def testar_conta(
    mac_id: int, db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> MetaAdsTesteResponse:
    return contas.testar_conta(db, _admin(db, current_user, company_id), mac_id)


@router.post(
    "/contas/{mac_id}/sincronizar",
    response_model=MetaAdsSyncIniciadaResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def sincronizar_conta(
    mac_id: int,
    tarefas: BackgroundTasks,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> MetaAdsSyncIniciadaResponse:
    conta = contas.obter_conta_da_empresa(db, _admin(db, current_user, company_id), mac_id)
    if not sincronizacao.reivindicar(db, conta.macId):
        raise ConflictError("Sincronização já em andamento para esta conta (ou conta inativa)")
    tarefas.add_task(sincronizacao.executar_em_sessao_propria, conta.macId, "manual")
    return MetaAdsSyncIniciadaResponse(contas=[conta.macId], mensagem="Sincronização iniciada")


@router.post(
    "/sincronizar-periodo",
    response_model=MetaAdsSyncIniciadaResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def sincronizar_periodo(
    data: MetaAdsSyncPeriodoRequest,
    tarefas: BackgroundTasks,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> MetaAdsSyncIniciadaResponse:
    emp_id = _admin(db, current_user, company_id)
    disparadas: list[int] = []
    for mac_id in contas.ids_contas_ativas(db, emp_id, data.macId):
        if sincronizacao.reivindicar(db, mac_id):
            tarefas.add_task(
                sincronizacao.executar_em_sessao_propria,
                mac_id,
                "periodo",
                data.data_inicial,
                data.data_final,
            )
            disparadas.append(mac_id)
    if not disparadas:
        raise ConflictError("Nenhuma conta ativa livre para sincronizar agora")
    return MetaAdsSyncIniciadaResponse(contas=disparadas, mensagem="Reprocessamento iniciado")


@router.get("/contas/{mac_id}/logs", response_model=MetaAdsSyncLogListResponse)
def listar_logs(
    mac_id: int, db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> MetaAdsSyncLogListResponse:
    return contas.listar_logs(db, _admin(db, current_user, company_id), mac_id)


@router.get("/painel", response_model=MetaAdsPainelResponse)
def painel(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    data_inicial: date | None = Query(default=None),
    data_final: date | None = Query(default=None),
    mac_id: int | None = Query(default=None, alias="macId"),
    somente_ativas: bool = Query(default=False),
) -> MetaAdsPainelResponse:
    emp_id = empresa_obrigatoria(db, current_user, company_id)
    return indicadores.painel(
        db, emp_id, indicadores.FiltroPainel(data_inicial, data_final, mac_id, somente_ativas)
    )


@router.get("/cockpit", response_model=MetaAdsCockpitResponse)
def cockpit(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    data_inicial: date = Query(),
    data_final: date = Query(),
    mac_id: int | None = Query(default=None, alias="macId"),
    somente_ativas: bool = Query(default=False),
) -> MetaAdsCockpitResponse:
    emp_id = empresa_obrigatoria(db, current_user, company_id)
    return cockpit_servico.montar(
        db, emp_id, indicadores.FiltroPainel(data_inicial, data_final, mac_id, somente_ativas)
    )


@router.get("/campanhas-opcoes", response_model=MetaAdsCampanhaOpcoesResponse)
def campanhas_opcoes(
    db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> MetaAdsCampanhaOpcoesResponse:
    return indicadores.opcoes_campanhas(db, empresa_obrigatoria(db, current_user, company_id))


@router.get("/contas-opcoes", response_model=MetaAdsContaOpcoesResponse)
def contas_opcoes(
    db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> MetaAdsContaOpcoesResponse:
    return indicadores.opcoes_contas(db, empresa_obrigatoria(db, current_user, company_id))


@router.get("/campanhas/{mcg_id}", response_model=MetaAdsCampanhaDetalheResponse)
def detalhe_campanha(
    mcg_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    data_inicial: date | None = Query(default=None),
    data_final: date | None = Query(default=None),
) -> MetaAdsCampanhaDetalheResponse:
    emp_id = empresa_obrigatoria(db, current_user, company_id)
    return indicadores.detalhe_campanha(db, emp_id, mcg_id, data_inicial, data_final)


@router.get("/resumo", response_model=MetaAdsResumoResponse)
def resumo(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    data_inicial: date | None = Query(default=None),
    data_final: date | None = Query(default=None),
) -> MetaAdsResumoResponse:
    emp_id = empresa_obrigatoria(db, current_user, company_id)
    return indicadores.resumo(db, emp_id, data_inicial, data_final)


@router.patch("/oportunidades/{opo_id}/campanha", response_model=OportunidadeCampanhaMetaResponse)
def definir_campanha(
    opo_id: int,
    data: OportunidadeCampanhaMetaRequest,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeCampanhaMetaResponse:
    emp_id = empresa_obrigatoria(db, current_user, company_id)
    return indicadores.definir_campanha_oportunidade(db, emp_id, opo_id, data.opoMcgId)


@router.get("/monitoramento/config", response_model=MetaAdsMonitorConfigResponse)
def obter_config_monitoramento(
    db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> MetaAdsMonitorConfigResponse:
    return config_monitor.config_resposta(db, empresa_obrigatoria(db, current_user, company_id))


@router.put("/monitoramento/config", response_model=MetaAdsMonitorConfigResponse)
def atualizar_config_monitoramento(
    data: MetaAdsMonitorConfigUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> MetaAdsMonitorConfigResponse:
    return config_monitor.atualizar_config(db, _admin(db, current_user, company_id), data)


@router.get("/alertas", response_model=MetaAdsAlertaListResponse)
def listar_alertas(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    status_alerta: Literal["aberto", "ciente", "resolvido"] | None = Query(default=None, alias="status"),
) -> MetaAdsAlertaListResponse:
    emp_id = empresa_obrigatoria(db, current_user, company_id)
    return MetaAdsAlertaListResponse(items=alertas.listar(db, emp_id, status_alerta))


@router.post("/alertas/{mal_id}/ciente", response_model=MetaAdsAlertaResponse)
def marcar_alerta_ciente(
    mal_id: int, db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> MetaAdsAlertaResponse:
    return alertas.marcar_ciente(db, empresa_obrigatoria(db, current_user, company_id), mal_id)


def _data_resumo(texto: str, permite_ultimo: bool) -> date | None:
    if permite_ultimo and texto == "ultimo":
        return None
    try:
        return date.fromisoformat(texto)
    except ValueError as exc:
        raise BadRequestError("Data inválida: use AAAA-MM-DD") from exc


@router.get("/resumos", response_model=MetaAdsResumoDiarioListResponse)
def listar_resumos(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    limite: int = Query(default=30, ge=1, le=365),
) -> MetaAdsResumoDiarioListResponse:
    return resumo_diario.listar(db, empresa_obrigatoria(db, current_user, company_id), limite)


@router.get("/resumos/{data}", response_model=MetaAdsResumoDiarioResponse)
def obter_resumo(
    data: str, db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> MetaAdsResumoDiarioResponse:
    emp_id = empresa_obrigatoria(db, current_user, company_id)
    return resumo_diario.obter(db, emp_id, _data_resumo(data, True))


@router.post("/resumos/{data}/gerar", response_model=MetaAdsResumoDiarioResponse)
def gerar_resumo(
    data: str, db: DbSessionDep, current_user: CurrentUserDep, company_id: CompanyIdDep
) -> MetaAdsResumoDiarioResponse:
    emp_id = empresa_obrigatoria(db, current_user, company_id)
    dia = _data_resumo(data, False)
    if dia > resumo_diario.hoje_local():
        raise BadRequestError("Data futura")
    return resumo_diario.gerar(db, emp_id, dia)
