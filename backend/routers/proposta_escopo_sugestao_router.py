from fastapi import APIRouter, File, Form, UploadFile

from ..config import settings
from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..exceptions import BadRequestError
from ..schemas.escopo_sugestao_ia import EscopoSugestaoIaResponse
from ..services.proposta_escopo_sugestao_service import gerar_sugestao_escopo_para_proposta

router = APIRouter(tags=["proposta-escopo-sugestao"])


@router.post(
    "/api/propostas/{prp_id}/escopo/sugerir-ia",
    response_model=EscopoSugestaoIaResponse,
)
async def sugerir_escopo_ia(
    prp_id: int,
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    pontos_principais: str = Form(""),
    observacoes_adicionais: str = Form(""),
    files: list[UploadFile] | None = File(None),
) -> EscopoSugestaoIaResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    upload_list = files if files else []
    if len(upload_list) > settings.LLM_MAX_FILES:
        raise BadRequestError(f"Envie no máximo {settings.LLM_MAX_FILES} arquivos por requisição.")

    max_bytes = settings.LLM_MAX_FILE_SIZE_MB * 1024 * 1024
    for file in upload_list:
        content = await file.read()
        if len(content) > max_bytes:
            raise BadRequestError(
                f"O arquivo '{file.filename}' excede o limite de {settings.LLM_MAX_FILE_SIZE_MB}MB."
            )
        await file.seek(0)

    return await gerar_sugestao_escopo_para_proposta(
        db=db,
        prp_id=prp_id,
        company_id=company_id,
        pontos_principais=pontos_principais,
        observacoes_adicionais=observacoes_adicionais,
        files=upload_list,
    )
