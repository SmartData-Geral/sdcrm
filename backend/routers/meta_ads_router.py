"""
Meta Ads: configuracao das contas (admin) e, na Task 8, indicadores das campanhas.

Rotas internas em portugues, JWT + X-Company-Id. Toda rota exige empresa selecionada.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, status

from ..dependencies import (
    CompanyIdDep,
    CurrentUserDep,
    DbSessionDep,
    require_admin,
    require_user_in_company,
)
from ..exceptions import BadRequestError, ConflictError
from ..schemas.meta_ads import (
    MetaAdsContaCreate,
    MetaAdsContaListResponse,
    MetaAdsContaResponse,
    MetaAdsContaUpdate,
    MetaAdsSyncIniciadaResponse,
    MetaAdsSyncLogListResponse,
    MetaAdsSyncPeriodoRequest,
    MetaAdsTesteResponse,
)
from ..services.meta_ads import contas, sincronizacao

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
