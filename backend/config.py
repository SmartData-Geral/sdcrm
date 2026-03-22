from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import AnyHttpUrl, Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Diretório deste arquivo: .../backend/
_BACKEND_DIR = Path(__file__).resolve().parent
# Raiz do repositório (pasta que contém backend/ e normalmente o .env)
_REPO_ROOT = _BACKEND_DIR.parent


def _resolve_env_files() -> tuple[Path, ...]:
    """
    Carrega .env de caminhos fixos para não depender do cwd do processo.
    Ordem: raiz do repo, depois backend/ (útil se alguém copiar .env só para lá).
    """
    candidates = (_REPO_ROOT / ".env", _BACKEND_DIR / ".env")
    found = tuple(p for p in candidates if p.is_file())
    if found:
        return found
    return (Path(".env"),)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_resolve_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "SD Framework"
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = Field(..., description="URL de conexão do banco (SQLAlchemy style)")

    JWT_SECRET_KEY: str = Field(..., min_length=16)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ALLOW_ORIGINS: List[AnyHttpUrl] | List[str] = ["http://localhost:5173"]

    MULTIEMPRESA_ENABLED: bool = True

    LLM_PROVIDER: str = "openai"
    LLM_OPENAI_API_KEY: str | None = None
    LLM_OPENAI_BASE_URL: str | None = None
    LLM_OPENAI_MODEL: str = "gpt-4o-mini"
    # Timeout total (s) para chamadas HTTP à OpenAI (transcrições grandes podem demorar).
    LLM_HTTP_TIMEOUT_SECONDS: float = 180.0
    LLM_MAX_FILE_SIZE_MB: int = 10
    LLM_MAX_FILES: int = 5

    @field_validator("LLM_OPENAI_BASE_URL", mode="before")
    @classmethod
    def empty_base_url_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("LLM_OPENAI_API_KEY", mode="before")
    @classmethod
    def strip_openai_api_key(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        return v

    @field_validator("ALLOW_ORIGINS", mode="before")
    @classmethod
    def parse_allow_origins(cls, v):
        # Aceita lista já pronta, string simples ou CSV.
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            value = v.strip()
            if value.startswith("[") and value.endswith("]"):
                import json

                return json.loads(value)
            return [item.strip() for item in value.split(",") if item.strip()]
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]


settings = get_settings()

