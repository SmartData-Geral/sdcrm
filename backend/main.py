import os
import shutil
from pathlib import Path

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .dependencies import CurrentUserDep, require_admin
from .routers import (
    auth_router,
    contrato_router,
    como_conheceu_router,
    crm_dashboard_router,
    crm_meta_mensal_router,
    escopo_ai_router,
    empresa_router,
    etapa_kanban_router,
    health_router,
    historico_oportunidade_router,
    integracao_router,
    lead_intake_router,
    webhook_router,
    llm_agente_router,
    motivo_cancelamento_router,
    oportunidade_router,
    proposta_router,
    proposta_escopo_sugestao_router,
    produto_router,
    reuniao_analise_router,
    usuario_router,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Sobe e desce o worker de entrega de webhooks junto com a aplicacao."""
    from .workers import webhook_worker

    await webhook_worker.iniciar()
    try:
        yield
    finally:
        await webhook_worker.parar()


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)

allow_origins = [str(o) for o in settings.ALLOW_ORIGINS]

# Facilita desenvolvimento local (localhost/127 e webviews com origin "null")
for local_origin in (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
):
    if local_origin not in allow_origins:
        allow_origins.append(local_origin)
if settings.DEBUG and "null" not in allow_origins:
    allow_origins.append("null")

app.add_middleware(
    CORSMiddleware,
    # Importante: com allow_credentials=True, não podemos usar allow_origins=["*"].
    # Em dev, garantimos localhost/127.0.0.1 acima; em prod, use ALLOW_ORIGINS no .env.
    allow_origins=allow_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router.router)
app.include_router(auth_router.router)
app.include_router(empresa_router.router)
app.include_router(como_conheceu_router.router)
app.include_router(motivo_cancelamento_router.router)
app.include_router(produto_router.router)
app.include_router(etapa_kanban_router.router)
app.include_router(oportunidade_router.router)
app.include_router(proposta_router.router)
app.include_router(contrato_router.router)
app.include_router(proposta_escopo_sugestao_router.router)
app.include_router(historico_oportunidade_router.router)
app.include_router(llm_agente_router.router)
app.include_router(usuario_router.router)
app.include_router(crm_dashboard_router.router)
app.include_router(crm_meta_mensal_router.router)
app.include_router(escopo_ai_router.router)
app.include_router(reuniao_analise_router.router)
app.include_router(integracao_router.router)
app.include_router(lead_intake_router.router)
app.include_router(webhook_router.router)

logger = logging.getLogger(__name__)


@app.exception_handler(RequestValidationError)
async def registrar_validacao_integracao(request: Request, exc: RequestValidationError):
    """
    O 422 do Pydantic curto-circuita antes do handler da rota, entao o log da
    requisicao invalida so pode acontecer aqui.

    Tres cuidados: abrimos uma Session propria (o get_db da rota ja foi encerrado),
    envolvemos tudo em try/except para que uma falha de log jamais transforme um 422
    em 500, e preservamos o corpo de resposta padrao do FastAPI para nao quebrar
    clientes nem o OpenAPI.
    """
    if request.url.path.startswith("/api/v1/"):
        try:
            from .services import integracao_chave_service, integracao_log_service

            corpo = await request.body()
            try:
                dados = json.loads(corpo) if corpo else None
            except (ValueError, UnicodeDecodeError):
                dados = None

            encaminhado = request.headers.get("x-forwarded-for")
            ip = (
                encaminhado.split(",")[0].strip()[:64]
                if encaminhado
                else (request.client.host if request.client else None)
            )
            integracao_log_service.registrar_isolado(
                rota=request.url.path[:120],
                metodo=request.method,
                status_http=422,
                resultado="invalid",
                prefixo_informado=integracao_chave_service.prefixo_para_log(
                    request.headers.get("x-api-key")
                ),
                origem_sistema=(dados or {}).get("source") if isinstance(dados, dict) else None,
                external_id=(dados or {}).get("external_id") if isinstance(dados, dict) else None,
                payload=dados,
                erro=jsonable_encoder(exc.errors()),
                ip=ip,
                user_agent=request.headers.get("user-agent"),
            )
        except Exception:
            logger.exception("Falha ao registrar log de validacao da integracao")

    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})


def _resolve_uploads_dir() -> Path:
    configured = (os.getenv("SDCRM_UPLOADS_DIR") or os.getenv("UPLOADS_DIR") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parent / "uploads"


# Pasta de uploads (avatars/logos/imagens) e rota estática.
# Em produção, configure SDCRM_UPLOADS_DIR para usar um volume persistente.
UPLOADS_DIR = _resolve_uploads_dir()
AVATARS_DIR = UPLOADS_DIR / "avatars"
LOGOS_DIR = UPLOADS_DIR / "company-logos"
PROPOSAL_IMAGES_DIR = UPLOADS_DIR / "proposal-images"
AVATARS_DIR.mkdir(parents=True, exist_ok=True)
LOGOS_DIR.mkdir(parents=True, exist_ok=True)
PROPOSAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def _seed_default_proposal_images() -> None:
    """
    Copia imagens padrão versionadas no repositório para /static/proposal-images.
    Isso evita necessidade de reupload para os defaults da proposta base.
    """
    project_root = Path(__file__).resolve().parent.parent
    source_dir = project_root / "images"
    if not source_dir.exists():
        return

    seed_map = {
        "Grupo SD (3).png": "998d57eee88841cfa83b918e75a27d2f.png",
        "Clientes.png": "db19573ee526402cb15dc7668043a173.png",
        "Logo Branca Vertical.png": "smart-data-logo-branca-vertical.png",
    }
    for source_name, target_name in seed_map.items():
        source_path = source_dir / source_name
        target_path = PROPOSAL_IMAGES_DIR / target_name
        if source_path.exists() and not target_path.exists():
            shutil.copy2(source_path, target_path)


_seed_default_proposal_images()
# Servimos arquivos estáticos (avatars) em dois caminhos:
# - /static        -> uso atual
# - /api/static    -> compatibilidade com URLs antigas gravadas no banco
static_files = StaticFiles(directory=str(UPLOADS_DIR))
app.mount("/static", static_files, name="static")
app.mount("/api/static", static_files, name="api-static")

ALLOWED_AVATAR_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg"}
ALLOWED_AVATAR_EXTENSIONS = {".png", ".jpg", ".jpeg"}


@app.post("/api/usuarios/avatar/upload", status_code=status.HTTP_200_OK)
async def upload_avatar(
    current_user: CurrentUserDep,
    file: UploadFile = File(..., description="Imagem do avatar (.png ou .jpg)"),
):
    """Faz upload de uma imagem de avatar (PNG ou JPG). Retorna a URL para usar no usuário."""
    require_admin(current_user)
    if file.content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aceito apenas imagens PNG ou JPG.",
        )
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_AVATAR_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use um arquivo .png ou .jpg",
        )
    import uuid
    name = f"{uuid.uuid4().hex}{ext}"
    path = AVATARS_DIR / name
    contents = await file.read()
    path.write_bytes(contents)
    return {"avatarUrl": f"/static/avatars/{name}"}


@app.post("/api/empresas/logo/upload", status_code=status.HTTP_200_OK)
async def upload_empresa_logo(
    current_user: CurrentUserDep,
    file: UploadFile = File(..., description="Logo da empresa (.png ou .jpg)"),
):
    """Upload de logo da empresa (PNG ou JPG). Retorna a URL para uso no cadastro da empresa."""
    require_admin(current_user)
    if file.content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aceito apenas imagens PNG ou JPG.",
        )
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_AVATAR_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use um arquivo .png ou .jpg",
        )
    import uuid

    name = f"{uuid.uuid4().hex}{ext}"
    path = LOGOS_DIR / name
    contents = await file.read()
    path.write_bytes(contents)
    return {"logoUrl": f"/static/company-logos/{name}"}


@app.post("/api/propostas/apresentacao/imagem/upload", status_code=status.HTTP_200_OK)
async def upload_proposta_apresentacao_imagem(
    current_user: CurrentUserDep,
    file: UploadFile = File(..., description="Imagem da seção de apresentação (.png ou .jpg)"),
):
    """Upload de imagem para a seção de apresentação da proposta (PNG/JPG)."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    if file.content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aceito apenas imagens PNG ou JPG.",
        )
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_AVATAR_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use um arquivo .png ou .jpg",
        )
    import uuid

    name = f"{uuid.uuid4().hex}{ext}"
    path = PROPOSAL_IMAGES_DIR / name
    contents = await file.read()
    path.write_bytes(contents)
    return {"imageUrl": f"/static/proposal-images/{name}"}


@app.post("/api/propostas/clientes/imagem/upload", status_code=status.HTTP_200_OK)
async def upload_proposta_clientes_imagem(
    current_user: CurrentUserDep,
    file: UploadFile = File(..., description="Imagem da seção de clientes (.png ou .jpg)"),
):
    """Upload de imagem para a seção de clientes da proposta (PNG/JPG)."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    if file.content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aceito apenas imagens PNG ou JPG.",
        )
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_AVATAR_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use um arquivo .png ou .jpg",
        )
    import uuid

    name = f"{uuid.uuid4().hex}{ext}"
    path = PROPOSAL_IMAGES_DIR / name
    contents = await file.read()
    path.write_bytes(contents)
    return {"imageUrl": f"/static/proposal-images/{name}"}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": settings.APP_NAME}

