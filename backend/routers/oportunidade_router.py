from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..schemas.oportunidade import (
    OportunidadeCreate,
    OportunidadeLeadScoreRequest,
    OportunidadeListResponse,
    OportunidadeMoverEtapaRequest,
    OportunidadeResponse,
    OportunidadeStandByRequest,
    OportunidadeTemperaturaRequest,
    OportunidadeUpdate,
)
from ..schemas.oportunidade_historico import (
    OportunidadeHistoricoCreate,
    OportunidadeHistoricoListResponse,
    OportunidadeHistoricoResponse,
    OportunidadeHistoricoUpdate,
)
from ..services import oportunidade_historico_service
from ..services import oportunidade_service

router = APIRouter(prefix="/api/oportunidades", tags=["oportunidades"])


@router.get("", response_model=OportunidadeListResponse)
def listar(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    titulo: Optional[str] = Query(default=None),
    status: Literal["ativos", "inativos", "todos"] = Query(default="ativos"),
    etapa_id: Optional[int] = Query(default=None),
    responsavel_id: Optional[int] = Query(default=None),
    pro_id: Optional[int] = Query(default=None),
    data_ultimo_contato_inicio: Optional[date] = Query(default=None),
    data_ultimo_contato_fim: Optional[date] = Query(default=None),
    status_fechamento: Optional[Literal["ativo", "ganho", "perdido", "stand-by"]] = Query(default=None),
) -> OportunidadeListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_service.list_oportunidades(
        db,
        company_id=company_id,
        titulo=titulo,
        status=status,
        etapa_id=etapa_id,
        responsavel_id=responsavel_id,
        pro_id=pro_id,
        data_ultimo_contato_inicio=data_ultimo_contato_inicio,
        data_ultimo_contato_fim=data_ultimo_contato_fim,
        status_fechamento=status_fechamento,
        page=page,
        page_size=page_size,
    )


@router.get("/{opo_id}", response_model=OportunidadeResponse)
def obter(
    opo_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_service.get_oportunidade(db, opo_id, company_id)


@router.post("", response_model=OportunidadeResponse, status_code=status.HTTP_201_CREATED)
def criar(
    data: OportunidadeCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_service.create_oportunidade(db, data, company_id)


@router.put("/{opo_id}", response_model=OportunidadeResponse)
def atualizar(
    opo_id: int,
    data: OportunidadeUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_service.update_oportunidade(db, opo_id, data, company_id)


@router.patch("/{opo_id}/ganhar", response_model=OportunidadeResponse)
def ganhar(
    opo_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_service.set_oportunidade_status_fechamento(db, opo_id, "ganho", company_id)


@router.patch("/{opo_id}/perder", response_model=OportunidadeResponse)
def perder(
    opo_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_service.set_oportunidade_status_fechamento(db, opo_id, "perdido", company_id)


@router.patch("/{opo_id}/stand-by", response_model=OportunidadeResponse)
def stand_by(
    opo_id: int,
    data: OportunidadeStandByRequest,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_service.set_oportunidade_stand_by(db, opo_id, data, company_id)


@router.patch("/{opo_id}/mover-etapa", response_model=OportunidadeResponse)
def mover_etapa(
    opo_id: int,
    data: OportunidadeMoverEtapaRequest,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_service.mover_etapa(db, opo_id, data, company_id)


@router.patch("/{opo_id}/lead-score", response_model=OportunidadeResponse)
def lead_score(
    opo_id: int,
    data: OportunidadeLeadScoreRequest,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_service.set_lead_score(db, opo_id, data, company_id)


@router.patch("/{opo_id}/temperatura", response_model=OportunidadeResponse)
def temperatura(
    opo_id: int,
    data: OportunidadeTemperaturaRequest,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_service.set_temperatura(db, opo_id, data, company_id)


@router.patch("/{opo_id}/reuniao-confirmada", response_model=OportunidadeResponse)
def reuniao_confirmada(
    opo_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_service.set_reuniao_confirmada(db, opo_id, True, company_id)


@router.patch("/{opo_id}/proposta-enviada", response_model=OportunidadeResponse)
def proposta_enviada(
    opo_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_service.set_proposta_enviada(db, opo_id, True, company_id)


@router.patch("/{opo_id}/inativar", response_model=OportunidadeResponse)
def inativar(
    opo_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_service.inativar_oportunidade(db, opo_id, company_id)


# Historicos aninhados em /api/oportunidades/{id}/historicos
@router.get("/{opo_id}/historicos", response_model=OportunidadeHistoricoListResponse)
def listar_historicos(
    opo_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Literal["ativos", "inativos", "todos"] = Query(default="ativos"),
) -> OportunidadeHistoricoListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_historico_service.list_historicos(
        db, opo_id, company_id=company_id, status=status, page=page, page_size=page_size
    )


@router.post("/{opo_id}/historicos", response_model=OportunidadeHistoricoResponse, status_code=status.HTTP_201_CREATED)
def criar_historico(
    opo_id: int,
    data: OportunidadeHistoricoCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeHistoricoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_historico_service.create_historico(
        db, opo_id, data, company_id=company_id, usu_id=current_user.usuId
    )


# PUT e PATCH de historico por id em router separado ou prefixo alternativo
# O usuário pediu: PUT /api/historicos-oportunidade/{id} e PATCH /api/historicos-oportunidade/{id}/inativar
# Então precisamos de um router para historicos-oportunidade com prefix /api/historicos-oportunidade
# e rotas {oph_id} e {oph_id}/inativar. Vou criar esse router.