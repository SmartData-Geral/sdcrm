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

    # --- Integração externa (API de leads + webhooks) ---
    # Pepper da hash das chaves de API. Um dump do banco sozinho deixa de confirmar
    # uma chave adivinhada. ATENÇÃO: trocar este valor invalida todas as chaves emitidas.
    API_KEY_PEPPER: str | None = None
    LEADS_PIPELINE_PADRAO: str = "default"
    LEADS_ETAPA_PADRAO_NOME: str = "Novo Lead"
    # Cria em como_conheceu a origem que chegar no `source` e ainda não existir,
    # marcada com ccoGrupo="Integração". Desligue se preferir curar a lista à mão.
    INTEGRACAO_AUTOCRIAR_ORIGEM: bool = True
    INTEGRACAO_LOG_RETENCAO_DIAS: int = 90
    # Por padrão o log mascara e-mail e telefone (LGPD). Ligue por uma janela curta
    # de depuração apenas.
    INTEGRACAO_LOG_PAYLOAD_COMPLETO: bool = False

    # --- Webhooks de saida ---
    # Desligavel para o caso de extrairem um container de worker dedicado: as replicas
    # de API sobem com false e so o worker roda o dispatcher.
    WEBHOOK_WORKER_ENABLED: bool = True
    WEBHOOK_POLL_INTERVAL_SECONDS: float = 10.0
    WEBHOOK_BATCH_SIZE: int = 20
    WEBHOOK_TIMEOUT_SECONDS: float = 15.0
    WEBHOOK_MAX_FALHAS_DESATIVAR: int = 20
    WEBHOOK_RETENCAO_DIAS: int = 30
    # Vazio = qualquer host publico. A protecao contra faixas privadas vale sempre.
    WEBHOOK_HOSTS_PERMITIDOS: str = ""
    # Minutos ate uma entrega reivindicada por um processo morto ser recuperada.
    WEBHOOK_CLAIM_TIMEOUT_MINUTOS: int = 5

    LLM_PROVIDER: str = "openai"
    LLM_OPENAI_API_KEY: str | None = None
    LLM_OPENAI_BASE_URL: str | None = None
    LLM_OPENAI_MODEL: str = "gpt-4o-mini"
    # Timeout total (s) para chamadas HTTP à OpenAI (transcrições grandes podem demorar).
    LLM_HTTP_TIMEOUT_SECONDS: float = 180.0
    LLM_MAX_FILE_SIZE_MB: int = 10
    LLM_MAX_FILES: int = 10

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

