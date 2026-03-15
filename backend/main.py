from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .dependencies import CurrentUserDep, require_admin
from .routers import (
    auth_router,
    como_conheceu_router,
    empresa_router,
    etapa_kanban_router,
    health_router,
    historico_oportunidade_router,
    motivo_cancelamento_router,
    oportunidade_router,
    produto_router,
    usuario_router,
)

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(o) for o in settings.ALLOW_ORIGINS],
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
app.include_router(historico_oportunidade_router.router)
app.include_router(usuario_router.router)

# Pasta de uploads (avatars) e rota estática
UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
AVATARS_DIR = UPLOADS_DIR / "avatars"
AVATARS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(UPLOADS_DIR)), name="static")

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


@app.get("/")
def root() -> dict[str, str]:
    return {"message": settings.APP_NAME}

