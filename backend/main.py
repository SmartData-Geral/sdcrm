from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
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


@app.get("/")
def root() -> dict[str, str]:
    return {"message": settings.APP_NAME}

