from fastapi import APIRouter, Depends

from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..schemas.oportunidade_historico import (
    OportunidadeHistoricoResponse,
    OportunidadeHistoricoUpdate,
)
from ..services import oportunidade_historico_service

router = APIRouter(prefix="/api/historicos-oportunidade", tags=["historicos-oportunidade"])


@router.put("/{oph_id}", response_model=OportunidadeHistoricoResponse)
def atualizar(
    oph_id: int,
    data: OportunidadeHistoricoUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeHistoricoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_historico_service.update_historico(db, oph_id, data, company_id)


@router.patch("/{oph_id}/inativar", response_model=OportunidadeHistoricoResponse)
def inativar(
    oph_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> OportunidadeHistoricoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return oportunidade_historico_service.inativar_historico(db, oph_id, company_id)
