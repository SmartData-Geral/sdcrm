from typing import Optional

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..schemas.reuniao_analise import ReuniaoAnaliseListResponse, ReuniaoAnaliseResponse
from ..services import reuniao_analise_service

router = APIRouter(tags=["analises-reuniao"])


@router.get("/api/oportunidades/{opo_id}/analises-reuniao", response_model=ReuniaoAnaliseListResponse)
def listar_analises_reuniao(
    opo_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ReuniaoAnaliseListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return reuniao_analise_service.list_reuniao_analises(db, opo_id, company_id, page, page_size)


@router.get("/api/analises-reuniao/{ran_id}", response_model=ReuniaoAnaliseResponse)
def obter_analise_reuniao(
    ran_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ReuniaoAnaliseResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return reuniao_analise_service.get_reuniao_analise(db, ran_id, company_id)


@router.post("/api/oportunidades/{opo_id}/analises-reuniao", response_model=ReuniaoAnaliseResponse, status_code=status.HTTP_201_CREATED)
async def criar_analise_reuniao(
    opo_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    ranTranscricao: Optional[str] = Form(default=None),
    arquivo_transcricao: UploadFile | None = File(default=None),
    files: list[UploadFile] | None = File(default=None),
) -> ReuniaoAnaliseResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    upload_files = files if files is not None else []
    return await reuniao_analise_service.create_reuniao_analise(
        db=db,
        opo_id=opo_id,
        company_id=company_id,
        usu_id=current_user.usuId,
        transcricao=ranTranscricao,
        transcricao_arquivo=arquivo_transcricao,
        files=upload_files,
    )


@router.post("/api/analises-reuniao/{ran_id}/processar", response_model=ReuniaoAnaliseResponse)
def processar_analise_reuniao(
    ran_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ReuniaoAnaliseResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return reuniao_analise_service.process_reuniao_analise(db, ran_id, company_id)


@router.patch("/api/analises-reuniao/{ran_id}/aplicar-observacoes", response_model=ReuniaoAnaliseResponse)
def aplicar_observacoes(
    ran_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ReuniaoAnaliseResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return reuniao_analise_service.apply_observacoes(db, ran_id, company_id)


@router.patch("/api/analises-reuniao/{ran_id}/aplicar-dores-oportunidades", response_model=ReuniaoAnaliseResponse)
def aplicar_dores_oportunidades(
    ran_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ReuniaoAnaliseResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return reuniao_analise_service.apply_dores_oportunidades(db, ran_id, company_id)


@router.patch("/api/analises-reuniao/{ran_id}/aplicar-lead-score", response_model=ReuniaoAnaliseResponse)
def aplicar_lead_score(
    ran_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ReuniaoAnaliseResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return reuniao_analise_service.apply_lead_score(db, ran_id, company_id)


@router.patch("/api/analises-reuniao/{ran_id}/aplicar-temperatura", response_model=ReuniaoAnaliseResponse)
def aplicar_temperatura(
    ran_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ReuniaoAnaliseResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return reuniao_analise_service.apply_temperatura(db, ran_id, company_id)
