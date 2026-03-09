from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
def root_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/health", tags=["health"])
def api_health() -> dict[str, str]:
    return {"status": "ok"}

