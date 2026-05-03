from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..schemas.crm_dashboard import (
    CrmDashboardFiltroParams,
    CrmDashboardOportunidadesFiltroParams,
    CrmDashboardOportunidadesListResponse,
    CrmDashboardResponse,
)
from ..services import crm_dashboard_service

router = APIRouter(prefix="/api/crm", tags=["crm-dashboard"])


def _parse_serie_anos_csv(raw: str | None) -> list[int] | None:
    if not raw or not str(raw).strip():
        return None
    out: list[int] = []
    for part in str(raw).split(","):
        p = part.strip()
        if p.isdigit():
            y = int(p)
            if 1990 <= y <= 2100:
                out.append(y)
    return sorted(set(out)) or None


def _parse_dashboard_oportunidades_params(
    data_inicial: Annotated[Optional[date], Query(description="Data inicial (filtro global)")] = None,
    data_final: Annotated[Optional[date], Query(description="Data final (filtro global)")] = None,
    responsavel_id: Annotated[Optional[int], Query(description="Responsável (filtro global)")] = None,
    status: Annotated[
        Optional[str],
        Query(description="todas|ganhas|perdidas|ativas"),
    ] = "todas",
    fonte: Annotated[Optional[str], Query(description="Recorte: nome da fonte")] = None,
    solucao: Annotated[Optional[str], Query(description="Recorte: solução")] = None,
    motivo_perda: Annotated[Optional[str], Query(description="Recorte: motivo de perda")] = None,
    periodo: Annotated[Optional[str], Query(description="Recorte: YYYY-MM")] = None,
    metrica: Annotated[Optional[str], Query(description="recebidas|ganhas|perdidas|ativas|mrrIncremental")] = None,
) -> CrmDashboardOportunidadesFiltroParams:
    st = status or "todas"
    if st not in ("todas", "ganhas", "perdidas", "ativas"):
        st = "todas"
    if metrica and metrica not in ("recebidas", "ganhas", "perdidas", "ativas", "mrrIncremental"):
        raise HTTPException(status_code=422, detail="metrica inválida")
    return CrmDashboardOportunidadesFiltroParams(
        data_inicial=data_inicial,
        data_final=data_final,
        responsavel_id=responsavel_id,
        status=st,
        fonte=fonte,
        solucao=solucao,
        motivo_perda=motivo_perda,
        periodo=periodo,
        metrica=metrica,
    )


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
    serie_anos: Annotated[
        Optional[str],
        Query(
            description="Anos da série mensal/meta, CSV (ex.: 2024,2025). Quando informado, não usa o período global nestes gráficos.",
        ),
    ] = None,
) -> CrmDashboardResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    filtros = CrmDashboardFiltroParams(
        data_inicial=data_inicial,
        data_final=data_final,
        responsavel_id=responsavel_id,
        status=status,
        serie_anos=_parse_serie_anos_csv(serie_anos),
    )
    return crm_dashboard_service.get_dashboard(db, company_id=company_id, filtros=filtros)


@router.get("/dashboard/oportunidades", response_model=CrmDashboardOportunidadesListResponse)
def listar_oportunidades_dashboard(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    filtros: Annotated[CrmDashboardOportunidadesFiltroParams, Depends(_parse_dashboard_oportunidades_params)],
) -> CrmDashboardOportunidadesListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return crm_dashboard_service.list_dashboard_oportunidades(db, company_id=company_id, filtros=filtros)

