from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..schemas.etapa_kanban import EtapaKanbanCreate, EtapaKanbanListResponse, EtapaKanbanResponse, EtapaKanbanUpdate
from ..services import etapa_kanban_service

router = APIRouter(prefix="/api/etapas-kanban", tags=["etapas-kanban"])


@router.get("", response_model=EtapaKanbanListResponse)
def listar(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    nome: Optional[str] = Query(default=None),
    status: Literal["ativos", "inativos", "todos"] = Query(default="ativos"),
) -> EtapaKanbanListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return etapa_kanban_service.list_etapas_kanban(
        db, company_id=company_id, nome=nome, status=status, page=page, page_size=page_size
    )


@router.get("/{etk_id}", response_model=EtapaKanbanResponse)
def obter(
    etk_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> EtapaKanbanResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return etapa_kanban_service.get_etapa_kanban(db, etk_id, company_id)


@router.post("", response_model=EtapaKanbanResponse, status_code=status.HTTP_201_CREATED)
def criar(
    data: EtapaKanbanCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> EtapaKanbanResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return etapa_kanban_service.create_etapa_kanban(db, data, company_id)


@router.put("/{etk_id}", response_model=EtapaKanbanResponse)
def atualizar(
    etk_id: int,
    data: EtapaKanbanUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> EtapaKanbanResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return etapa_kanban_service.update_etapa_kanban(db, etk_id, data, company_id)


@router.patch("/{etk_id}/ativar", response_model=EtapaKanbanResponse)
def ativar(
    etk_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> EtapaKanbanResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return etapa_kanban_service.set_etapa_kanban_ativo(db, etk_id, True, company_id)


@router.patch("/{etk_id}/inativar", response_model=EtapaKanbanResponse)
def inativar(
    etk_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> EtapaKanbanResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return etapa_kanban_service.set_etapa_kanban_ativo(db, etk_id, False, company_id)
