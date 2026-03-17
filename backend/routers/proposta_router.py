from typing import Optional

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import HTMLResponse

from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..schemas.proposta import (
    PropostaBlocoCreate,
    PropostaBlocoPadraoCreate,
    PropostaBlocoPadraoListResponse,
    PropostaBlocoPadraoResponse,
    PropostaBlocoPadraoUpdate,
    PropostaBlocoListResponse,
    PropostaBlocoReordenarRequest,
    PropostaBlocoResponse,
    PropostaBlocoUpdate,
    PropostaBlocoVisibilidadeRequest,
    PropostaCreate,
    PropostaEventoListResponse,
    PropostaEventoPublicoRequest,
    PropostaEventoResponse,
    PropostaListResponse,
    PropostaPublicarRequest,
    PropostaResponse,
    PropostaTemplateCreate,
    PropostaTemplateListResponse,
    PropostaTemplateResponse,
    PropostaTemplateUpdate,
    PropostaUpdate,
    PropostaVersaoCreate,
    PropostaVersaoListResponse,
    PropostaVersaoResponse,
)
from ..services import proposta_service

router = APIRouter(tags=["propostas"])


@router.get("/api/propostas", response_model=PropostaListResponse)
def listar_propostas(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    oportunidade_id: Optional[int] = Query(default=None),
    status_filtro: Optional[str] = Query(default=None, alias="status"),
    tipo: Optional[str] = Query(default=None),
    responsavel_id: Optional[int] = Query(default=None),
) -> PropostaListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.list_propostas(
        db=db,
        company_id=company_id,
        oportunidade_id=oportunidade_id,
        status=status_filtro,
        tipo=tipo,
        responsavel_id=responsavel_id,
        page=page,
        page_size=page_size,
    )


@router.get("/api/propostas/{prp_id}", response_model=PropostaResponse)
def obter_proposta(
    prp_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.get_proposta(db, prp_id, company_id)


@router.post("/api/propostas", response_model=PropostaResponse, status_code=status.HTTP_201_CREATED)
def criar_proposta(
    data: PropostaCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.create_proposta(db, data, company_id, current_user.usuId)


@router.put("/api/propostas/{prp_id}", response_model=PropostaResponse)
def atualizar_proposta(
    prp_id: int,
    data: PropostaUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.update_proposta(db, prp_id, data, company_id, current_user.usuId)


@router.patch("/api/propostas/{prp_id}/publicar", response_model=PropostaResponse)
def publicar_proposta(
    prp_id: int,
    data: PropostaPublicarRequest,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.publicar_proposta(db, prp_id, company_id, current_user.usuId, data.forcar_nova_versao)


@router.patch("/api/propostas/{prp_id}/arquivar", response_model=PropostaResponse)
def arquivar_proposta(
    prp_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.arquivar_proposta(db, prp_id, company_id, current_user.usuId)


@router.patch("/api/propostas/{prp_id}/duplicar", response_model=PropostaResponse)
def duplicar_proposta(
    prp_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.duplicar_proposta(db, prp_id, company_id, current_user.usuId)


@router.get("/api/oportunidades/{opo_id}/propostas", response_model=PropostaListResponse)
def listar_propostas_da_oportunidade(
    opo_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PropostaListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.list_propostas_oportunidade(db, opo_id, company_id, page, page_size)


@router.get("/api/propostas/{prp_id}/versoes", response_model=PropostaVersaoListResponse)
def listar_versoes(
    prp_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PropostaVersaoListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.list_versoes(db, prp_id, company_id, page, page_size)


@router.post("/api/propostas/{prp_id}/versoes", response_model=PropostaVersaoResponse, status_code=status.HTTP_201_CREATED)
def criar_versao(
    prp_id: int,
    data: PropostaVersaoCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaVersaoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.create_versao(db, prp_id, data, company_id, current_user.usuId)


@router.get("/api/versoes-proposta/{prv_id}", response_model=PropostaVersaoResponse)
def obter_versao(
    prv_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaVersaoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.get_versao(db, prv_id, company_id)


@router.get("/api/templates-proposta", response_model=PropostaTemplateListResponse)
def listar_templates(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tipo_proposta: Optional[str] = Query(default=None),
) -> PropostaTemplateListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.list_templates(db, company_id, page, page_size, tipo_proposta)


@router.get("/api/templates-proposta/{ptl_id}", response_model=PropostaTemplateResponse)
def obter_template(
    ptl_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaTemplateResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.get_template(db, ptl_id, company_id)


@router.post("/api/templates-proposta", response_model=PropostaTemplateResponse, status_code=status.HTTP_201_CREATED)
def criar_template(
    data: PropostaTemplateCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaTemplateResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.create_template(db, data, company_id)


@router.put("/api/templates-proposta/{ptl_id}", response_model=PropostaTemplateResponse)
def atualizar_template(
    ptl_id: int,
    data: PropostaTemplateUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaTemplateResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.update_template(db, ptl_id, data, company_id)


@router.patch("/api/templates-proposta/{ptl_id}/ativar", response_model=PropostaTemplateResponse)
def ativar_template(
    ptl_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaTemplateResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.set_template_ativo(db, ptl_id, True, company_id)


@router.patch("/api/templates-proposta/{ptl_id}/inativar", response_model=PropostaTemplateResponse)
def inativar_template(
    ptl_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaTemplateResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.set_template_ativo(db, ptl_id, False, company_id)


@router.get("/api/propostas/{prp_id}/blocos", response_model=PropostaBlocoListResponse)
def listar_blocos(
    prp_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PropostaBlocoListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.list_blocos(db, prp_id, company_id, page, page_size)


@router.post("/api/propostas/{prp_id}/blocos", response_model=PropostaBlocoResponse, status_code=status.HTTP_201_CREATED)
def criar_bloco(
    prp_id: int,
    data: PropostaBlocoCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaBlocoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.create_bloco(db, prp_id, data, company_id)


@router.put("/api/blocos-proposta/{pbl_id}", response_model=PropostaBlocoResponse)
def atualizar_bloco(
    pbl_id: int,
    data: PropostaBlocoUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaBlocoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.update_bloco(db, pbl_id, data, company_id)


@router.patch("/api/blocos-proposta/{pbl_id}/reordenar", response_model=PropostaBlocoResponse)
def reordenar_bloco(
    pbl_id: int,
    data: PropostaBlocoReordenarRequest,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaBlocoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.reordenar_bloco(db, pbl_id, data.pblOrdem, company_id)


@router.patch("/api/blocos-proposta/{pbl_id}/visibilidade", response_model=PropostaBlocoResponse)
def visibilidade_bloco(
    pbl_id: int,
    data: PropostaBlocoVisibilidadeRequest,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaBlocoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.set_visibilidade_bloco(db, pbl_id, data.pblVisivel, company_id)


@router.get("/api/propostas/{prp_id}/eventos", response_model=PropostaEventoListResponse)
def listar_eventos(
    prp_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PropostaEventoListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.list_eventos(db, prp_id, company_id, page, page_size)


@router.get("/api/cadastros-proposta/blocos-padrao", response_model=PropostaBlocoPadraoListResponse)
def listar_blocos_padroes(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    ptl_id: int | None = Query(default=None),
    tipo: str | None = Query(default=None),
) -> PropostaBlocoPadraoListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.list_blocos_padroes(db, company_id, page, page_size, ptl_id=ptl_id, tipo=tipo)


@router.post("/api/cadastros-proposta/blocos-padrao", response_model=PropostaBlocoPadraoResponse, status_code=status.HTTP_201_CREATED)
def criar_bloco_padrao(
    data: PropostaBlocoPadraoCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaBlocoPadraoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.create_bloco_padrao(db, data, company_id)


@router.put("/api/cadastros-proposta/blocos-padrao/{pbp_id}", response_model=PropostaBlocoPadraoResponse)
def atualizar_bloco_padrao(
    pbp_id: int,
    data: PropostaBlocoPadraoUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaBlocoPadraoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.update_bloco_padrao(db, pbp_id, data, company_id)


@router.patch("/api/cadastros-proposta/blocos-padrao/{pbp_id}/ativar", response_model=PropostaBlocoPadraoResponse)
def ativar_bloco_padrao(
    pbp_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaBlocoPadraoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.set_bloco_padrao_ativo(db, pbp_id, True, company_id)


@router.patch("/api/cadastros-proposta/blocos-padrao/{pbp_id}/inativar", response_model=PropostaBlocoPadraoResponse)
def inativar_bloco_padrao(
    pbp_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> PropostaBlocoPadraoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return proposta_service.set_bloco_padrao_ativo(db, pbp_id, False, company_id)


@router.get("/public/propostas/{token}", response_class=HTMLResponse)
def pagina_publica_proposta(token: str, db: DbSessionDep, preview: bool = False) -> HTMLResponse:
    html = proposta_service.get_public_html(db, token, preview=preview)
    return HTMLResponse(content=html)


@router.post("/public/propostas/{token}/visualizacao", response_model=PropostaEventoResponse)
def registrar_visualizacao(
    token: str,
    request: Request,
    db: DbSessionDep,
    body: PropostaEventoPublicoRequest = PropostaEventoPublicoRequest(),
) -> PropostaEventoResponse:
    return proposta_service.registrar_evento_publico(
        db=db,
        token=token,
        event_type="visualizacao",
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        dados=body.dados,
    )


@router.post("/public/propostas/{token}/clique-whatsapp")
def registrar_clique_whatsapp(
    token: str,
    request: Request,
    db: DbSessionDep,
    body: PropostaEventoPublicoRequest = PropostaEventoPublicoRequest(),
) -> dict:
    proposta_service.registrar_evento_publico(
        db=db,
        token=token,
        event_type="clique_whatsapp",
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        dados=body.dados,
    )
    return {"whatsappUrl": proposta_service.build_whatsapp_link(db, token)}


@router.post("/public/propostas/{token}/aceite", response_model=PropostaEventoResponse)
def aceitar_proposta_publica(
    token: str,
    request: Request,
    db: DbSessionDep,
    body: PropostaEventoPublicoRequest = PropostaEventoPublicoRequest(),
) -> PropostaEventoResponse:
    return proposta_service.registrar_evento_publico(
        db=db,
        token=token,
        event_type="aceite",
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        dados=body.dados,
    )

