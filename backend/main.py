from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .dependencies import CurrentUserDep, require_admin
from .routers import (
    auth_router,
    como_conheceu_router,
    crm_dashboard_router,
    escopo_ai_router,
    empresa_router,
    etapa_kanban_router,
    health_router,
    historico_oportunidade_router,
    llm_agente_router,
    motivo_cancelamento_router,
    oportunidade_router,
    proposta_router,
    proposta_escopo_sugestao_router,
    produto_router,
    reuniao_analise_router,
    usuario_router,
)

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

allow_origins = [str(o) for o in settings.ALLOW_ORIGINS]

# Facilita desenvolvimento local (localhost/127 e webviews com origin "null")
for local_origin in ("http://127.0.0.1:5173", "http://localhost:5173"):
    if local_origin not in allow_origins:
        allow_origins.append(local_origin)
if settings.DEBUG and "null" not in allow_origins:
    allow_origins.append("null")

if settings.DEBUG:
    # Ambiente de desenvolvimento: liberar totalmente CORS para facilitar integração local.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
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
app.include_router(proposta_escopo_sugestao_router.router)
app.include_router(historico_oportunidade_router.router)
app.include_router(llm_agente_router.router)
app.include_router(usuario_router.router)
app.include_router(crm_dashboard_router.router)
app.include_router(escopo_ai_router.router)
app.include_router(reuniao_analise_router.router)

# Pasta de uploads (avatars) e rota estática
UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
AVATARS_DIR = UPLOADS_DIR / "avatars"
LOGOS_DIR = UPLOADS_DIR / "company-logos"
PROPOSAL_IMAGES_DIR = UPLOADS_DIR / "proposal-images"
AVATARS_DIR.mkdir(parents=True, exist_ok=True)
LOGOS_DIR.mkdir(parents=True, exist_ok=True)
PROPOSAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
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

