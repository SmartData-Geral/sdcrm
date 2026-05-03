from fastapi import APIRouter, File, UploadFile

from ..config import settings
from ..dependencies import CompanyIdDep, CurrentUserDep, DbSessionDep, require_user_in_company
from ..exceptions import BadRequestError
from ..schemas.escopo_ai import EscopoAiGenerateResponse
from ..services.escopo_ai_service import generate_scope_from_files

router = APIRouter(tags=["escopo-ai"])


@router.post("/api/propostas/escopo/gerar-ia", response_model=EscopoAiGenerateResponse)
async def gerar_escopo_por_ia(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    company_id: CompanyIdDep,
    files: list[UploadFile] = File(..., description="Arquivos de contexto (json, txt, md, csv, pdf, imagens)"),
) -> EscopoAiGenerateResponse:
    require_user_in_company(db=db, current_user=current_user, company_id=company_id)
    if len(files) > settings.LLM_MAX_FILES:
        raise BadRequestError(f"Envie no máximo {settings.LLM_MAX_FILES} arquivos por requisição.")

    max_bytes = settings.LLM_MAX_FILE_SIZE_MB * 1024 * 1024
    for file in files:
        # UploadFile não expõe tamanho com confiança, então lemos o conteúdo para validar.
        content = await file.read()
        if len(content) > max_bytes:
            raise BadRequestError(
                f"O arquivo '{file.filename}' excede o limite de {settings.LLM_MAX_FILE_SIZE_MB}MB."
            )
        await file.seek(0)
    return await generate_scope_from_files(db, company_id, files)
