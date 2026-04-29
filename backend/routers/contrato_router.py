from fastapi import APIRouter, Query, status
from fastapi.responses import HTMLResponse
from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..schemas.contrato import (
    ContratoClausulaResponse,
    ContratoClausulaUpdate,
    ContratoCreate,
    ContratoModeloCreate,
    ContratoModeloListResponse,
    ContratoModeloResponse,
    ContratoModeloUpdate,
    ContratoModeloClausulaCreate,
    ContratoModeloClausulaReordenarRequest,
    ContratoModeloClausulaResponse,
    ContratoModeloClausulaUpdate,
    ContratoModeloClausulaVariacaoListResponse,
    ContratoModeloClausulaVariacaoResponse,
    ContratoModeloClausulaVariacaoCreate,
    ContratoModeloClausulaVariacaoUpdate,
    ContratoListResponse,
    ContratoMacroItem,
    ContratoMacroListResponse,
    ContratoResponse,
    ContratoSalvarComoVariacaoRequest,
    ContratoUpdate,
)
from ..services import contrato_service
from ..services import contrato_modelo_service
from ..services.contrato_macros_catalog import list_macro_catalog
from ..services.contrato_render_service import (
    gerar_html_contrato as render_contrato_html,
)
from ..exceptions import NotFoundError
from sqlalchemy import select
from ..models.contrato import Contrato
router = APIRouter(tags=["contratos"])


@router.get("/api/contratos", response_model=ContratoListResponse)
def listar_contratos(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ContratoListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_service.list_contratos(db=db, company_id=company_id, page=page, page_size=page_size)


@router.get("/api/contratos/macros", response_model=ContratoMacroListResponse)
def listar_macros_contrato(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoMacroListResponse:
    """Lista macros {{chave}} suportadas nos textos de modelos e cláusulas (referência para redatores)."""
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    rows = list_macro_catalog()
    return ContratoMacroListResponse(
        items=[ContratoMacroItem.model_validate(r) for r in rows],
    )


@router.get("/api/contratos/{ctr_id}", response_model=ContratoResponse)
def obter_contrato(
    ctr_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_service.get_contrato(db=db, company_id=company_id, contrato_id=ctr_id)


@router.post("/api/contratos", response_model=ContratoResponse, status_code=201)
def criar_contrato_avulso(
    data: ContratoCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    # Regra: avulso deve ser criado com ctrOpoId nulo.
    data_avulso = data.model_copy(update={"ctrOpoId": None})
    return contrato_service.criar_contrato(db=db, data=data_avulso, company_id=company_id)


@router.post("/api/oportunidades/{opo_id}/contrato", response_model=ContratoResponse, status_code=201)
def criar_contrato_por_oportunidade(
    opo_id: int,
    data: ContratoCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    data_op = data.model_copy(update={"ctrOpoId": opo_id})
    return contrato_service.criar_contrato(db=db, data=data_op, company_id=company_id)


@router.get("/api/oportunidades/{opo_id}/contrato", response_model=ContratoResponse)
def obter_contrato_por_oportunidade(
    opo_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_service.get_contrato_por_oportunidade(
        db=db,
        company_id=company_id,
        oportunidade_id=opo_id,
    )


@router.put("/api/contratos/{ctr_id}", response_model=ContratoResponse)
def atualizar_contrato(
    ctr_id: int,
    data: ContratoUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_service.update_contrato(db=db, company_id=company_id, contrato_id=ctr_id, data=data)


@router.patch("/api/contratos/{ctr_id}/pronto", response_model=ContratoResponse)
def set_pronto(
    ctr_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_service.set_status_contrato(db=db, company_id=company_id, contrato_id=ctr_id, novo_status="pronto")


@router.patch("/api/contratos/{ctr_id}/assinado", response_model=ContratoResponse)
def set_assinado(
    ctr_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_service.set_status_contrato(db=db, company_id=company_id, contrato_id=ctr_id, novo_status="assinado")


@router.patch("/api/contratos/{ctr_id}/inativar", response_model=ContratoResponse)
def inativar_contrato_endpoint(
    ctr_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_service.inativar_contrato(
        db=db, company_id=company_id, contrato_id=ctr_id
    )


@router.get("/api/contratos/{ctr_id}/clausulas", response_model=list[ContratoClausulaResponse])
def listar_clausulas_contrato(
    ctr_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> list[ContratoClausulaResponse]:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_service.listar_clausulas_contrato(db=db, company_id=company_id, contrato_id=ctr_id)


@router.patch("/api/contratos/{ctr_id}/clausulas/{clausula_id}/utilizar", response_model=ContratoClausulaResponse)
def utilizar_clausula(
    ctr_id: int,
    clausula_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoClausulaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_service.set_clausula_utilizar(
        db=db,
        company_id=company_id,
        contrato_id=ctr_id,
        clausula_id=clausula_id,
        utilizar=True,
    )


@router.patch("/api/contratos/{ctr_id}/clausulas/{clausula_id}/nao-utilizar", response_model=ContratoClausulaResponse)
def nao_utilizar_clausula(
    ctr_id: int,
    clausula_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoClausulaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_service.set_clausula_utilizar(
        db=db,
        company_id=company_id,
        contrato_id=ctr_id,
        clausula_id=clausula_id,
        utilizar=False,
    )


@router.put(
    "/api/contratos/{ctr_id}/clausulas/{clausula_id}",
    response_model=ContratoClausulaResponse,
)
def atualizar_snapshot_clausula(
    ctr_id: int,
    clausula_id: int,
    data: ContratoClausulaUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoClausulaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_service.update_clausula_snapshot(
        db=db,
        company_id=company_id,
        contrato_id=ctr_id,
        clausula_id=clausula_id,
        data=data,
    )


@router.post(
    "/api/contratos/{ctr_id}/clausulas/{clausula_id}/salvar-como-variacao",
    response_model=ContratoClausulaResponse,
)
def salvar_clausula_como_variacao(
    ctr_id: int,
    clausula_id: int,
    data: ContratoSalvarComoVariacaoRequest,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoClausulaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_service.salvar_clausula_como_variacao(
        db=db,
        company_id=company_id,
        contrato_id=ctr_id,
        clausula_id=clausula_id,
        data=data,
    )


# =========================
# Cadastros: modelo/claúsulas/variações
# =========================


@router.get("/api/contratos-modelo", response_model=ContratoModeloListResponse)
def listar_contratos_modelo(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ContratoModeloListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.list_modelos(db=db, company_id=company_id, page=page, page_size=page_size)


@router.get("/api/contratos-modelo/{ctm_id}", response_model=ContratoModeloResponse)
def obter_contrato_modelo(
    ctm_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoModeloResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.get_modelo(db=db, company_id=company_id, modelo_id=ctm_id)


@router.post("/api/contratos-modelo", response_model=ContratoModeloResponse, status_code=201)
def criar_contrato_modelo(
    data: ContratoModeloCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoModeloResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.create_modelo(db=db, company_id=company_id, data=data)


@router.put("/api/contratos-modelo/{ctm_id}", response_model=ContratoModeloResponse)
def atualizar_contrato_modelo(
    ctm_id: int,
    data: ContratoModeloUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoModeloResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.update_modelo(db=db, company_id=company_id, modelo_id=ctm_id, data=data)


@router.patch("/api/contratos-modelo/{ctm_id}/ativar", response_model=ContratoModeloResponse)
def ativar_contrato_modelo(
    ctm_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoModeloResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.set_modelo_ativo(db=db, company_id=company_id, modelo_id=ctm_id, ativo=True)


@router.patch("/api/contratos-modelo/{ctm_id}/inativar", response_model=ContratoModeloResponse)
def inativar_contrato_modelo(
    ctm_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoModeloResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.set_modelo_ativo(db=db, company_id=company_id, modelo_id=ctm_id, ativo=False)


@router.get("/api/contratos-modelo/{ctm_id}/clausulas", response_model=list[ContratoModeloClausulaResponse])
def listar_clausulas_modelo(
    ctm_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> list[ContratoModeloClausulaResponse]:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.list_clausulas_modelo(db=db, company_id=company_id, modelo_id=ctm_id)


@router.post("/api/contratos-modelo/{ctm_id}/clausulas", response_model=ContratoModeloClausulaResponse, status_code=201)
def criar_clausula_modelo(
    ctm_id: int,
    data: ContratoModeloClausulaCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoModeloClausulaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.create_clausula_modelo(db=db, company_id=company_id, modelo_id=ctm_id, data=data)


@router.put("/api/clausulas-modelo/{cmc_id}", response_model=ContratoModeloClausulaResponse)
def atualizar_clausula_modelo(
    cmc_id: int,
    data: ContratoModeloClausulaUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoModeloClausulaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.update_clausula_modelo(db=db, company_id=company_id, clausula_id=cmc_id, data=data)


@router.patch("/api/clausulas-modelo/{cmc_id}/ativar", response_model=ContratoModeloClausulaResponse)
def ativar_clausula_modelo(
    cmc_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoModeloClausulaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.set_clausula_ativa(db=db, company_id=company_id, clausula_id=cmc_id, ativo=True)


@router.patch("/api/clausulas-modelo/{cmc_id}/inativar", response_model=ContratoModeloClausulaResponse)
def inativar_clausula_modelo(
    cmc_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoModeloClausulaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.set_clausula_ativa(db=db, company_id=company_id, clausula_id=cmc_id, ativo=False)


@router.patch("/api/clausulas-modelo/{cmc_id}/reordenar", response_model=ContratoModeloClausulaResponse)
def reordenar_clausula_modelo(
    cmc_id: int,
    data: ContratoModeloClausulaReordenarRequest,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoModeloClausulaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.reordenar_clausula_modelo(
        db=db,
        company_id=company_id,
        clausula_id=cmc_id,
        data=data,
    )


@router.get("/api/clausulas-modelo/{cmc_id}/variacoes", response_model=ContratoModeloClausulaVariacaoListResponse)
def listar_variacoes_clausula_modelo(
    cmc_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoModeloClausulaVariacaoListResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.list_variacoes_clausula_modelo(db=db, company_id=company_id, clausula_id=cmc_id)


@router.post("/api/clausulas-modelo/{cmc_id}/variacoes", response_model=ContratoModeloClausulaVariacaoResponse, status_code=201)
def criar_variacao_clausula_modelo(
    cmc_id: int,
    data: ContratoModeloClausulaVariacaoCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoModeloClausulaVariacaoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.create_variacao_clausula_modelo(
        db=db,
        company_id=company_id,
        clausula_id=cmc_id,
        data=data,
    )


@router.put("/api/variacoes-clausula/{cmv_id}", response_model=ContratoModeloClausulaVariacaoResponse)
def atualizar_variacao_clausula_modelo(
    cmv_id: int,
    data: ContratoModeloClausulaVariacaoUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoModeloClausulaVariacaoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.update_variacao_clausula_modelo(
        db=db,
        company_id=company_id,
        variacao_id=cmv_id,
        data=data,
    )


@router.patch("/api/variacoes-clausula/{cmv_id}/ativar", response_model=ContratoModeloClausulaVariacaoResponse)
def ativar_variacao_clausula_modelo(
    cmv_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoModeloClausulaVariacaoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.set_variacao_clausula_ativa(
        db=db,
        company_id=company_id,
        variacao_id=cmv_id,
        ativo=True,
    )


@router.patch("/api/variacoes-clausula/{cmv_id}/inativar", response_model=ContratoModeloClausulaVariacaoResponse)
def inativar_variacao_clausula_modelo(
    cmv_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> ContratoModeloClausulaVariacaoResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    return contrato_modelo_service.set_variacao_clausula_ativa(
        db=db,
        company_id=company_id,
        variacao_id=cmv_id,
        ativo=False,
    )


# =========================
# Preview HTML / Link público (ETAPA 6)
# =========================


@router.get("/api/contratos/{ctr_id}/preview", response_class=HTMLResponse)
def preview_contrato(
    ctr_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> HTMLResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    # Gera HTML a partir do snapshot atual (inclui placeholders + numeração).
    _ = contrato_service._get_contrato_ativo(db=db, company_id=company_id, contrato_id=ctr_id)  # type: ignore[attr-defined]
    html_out = render_contrato_html(db=db, contrato_id=ctr_id)
    return HTMLResponse(content=html_out)


@router.post("/api/contratos/{ctr_id}/gerar-html", response_class=HTMLResponse, status_code=status.HTTP_200_OK)
def gerar_html_contrato(
    ctr_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
) -> HTMLResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    contrato = contrato_service._get_contrato_ativo(db=db, company_id=company_id, contrato_id=ctr_id)  # type: ignore[attr-defined]
    html_out = render_contrato_html(db=db, contrato_id=ctr_id)
    contrato.ctrHtmlSnapshot = html_out
    db.add(contrato)
    db.commit()
    return HTMLResponse(content=html_out)


@router.get("/public/contratos/{token}", response_class=HTMLResponse)
def pagina_publica_contrato(token: str, db: DbSessionDep) -> HTMLResponse:
    # Sem autenticação; isolamento pelo token.
    contrato = db.scalars(
        select(Contrato).where(Contrato.ctrTokenPublico == token, Contrato.ctrAtivo.is_(True))
    ).first()
    if contrato is None:
        raise NotFoundError("Contrato público não encontrado")

    if contrato.ctrHtmlSnapshot:
        return HTMLResponse(content=contrato.ctrHtmlSnapshot)

    html_out = render_contrato_html(db=db, contrato_id=contrato.ctrId)
    contrato.ctrHtmlSnapshot = html_out
    db.add(contrato)
    db.commit()
    return HTMLResponse(content=html_out)

