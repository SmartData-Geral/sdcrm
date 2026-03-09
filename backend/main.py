from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import auth_router, cliente_router, health_router

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
app.include_router(cliente_router.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": settings.APP_NAME}

