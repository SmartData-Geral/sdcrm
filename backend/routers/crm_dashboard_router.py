from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..schemas.crm_dashboard import CrmDashboardFiltroParams, CrmDashboardResponse
from ..services import crm_dashboard_service

router = APIRouter(prefix="/api/crm", tags=["crm-dashboard"])


@router.get("/dashboard", response_model=CrmDashboardResponse)
def obter_dashboard(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    data_inicial: Optional[date] = Query(default=None),
    data_final: Optional[date] = Query(default=None),
    responsavel_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(
        default="todas",
        pattern="^(todas|ganhas|perdidas|ativas)$",
    ),
) -> CrmDashboardResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    filtros = CrmDashboardFiltroParams(
        data_inicial=data_inicial,
        data_final=data_final,
        responsavel_id=responsavel_id,
        status=status,
    )
    return crm_dashboard_service.get_dashboard(db, company_id=company_id, filtros=filtros)

