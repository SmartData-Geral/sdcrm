from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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

