from fastapi import APIRouter

from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..schemas.llm_agente import LlmAgenteListResponse, LlmAgenteResponse, LlmAgenteUpdate
from ..services import llm_agente_service

router = APIRouter(tags=["llm-agentes"])


@router.get("/api/llm-agentes", response_model=LlmAgenteListResponse)
def listar_llm_agentes(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> LlmAgenteListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return llm_agente_service.list_llm_agentes(db, company_id)


@router.put("/api/llm-agentes/{agn_id}", response_model=LlmAgenteResponse)
def atualizar_llm_agente(
    agn_id: int,
    data: LlmAgenteUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> LlmAgenteResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return llm_agente_service.update_llm_agente(db, agn_id, data, company_id)
