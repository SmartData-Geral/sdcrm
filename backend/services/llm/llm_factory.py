from __future__ import annotations

from ...config import settings
from ...exceptions import BadRequestError
from .providers.base import LlmMeetingProvider, LlmScopeProvider
from .providers.openai_provider import OpenAiScopeProvider


def get_scope_provider(*, model_override: str | None = None) -> LlmScopeProvider:
    provider = settings.LLM_PROVIDER.strip().lower()
    if provider != "openai":
        raise BadRequestError(f"Provider LLM não suportado: {settings.LLM_PROVIDER}")
    if not settings.LLM_OPENAI_API_KEY:
        raise BadRequestError("LLM_OPENAI_API_KEY não configurada.")
    model_name = (model_override or "").strip() or settings.LLM_OPENAI_MODEL
    return OpenAiScopeProvider(
        api_key=settings.LLM_OPENAI_API_KEY,
        model_name=model_name,
        base_url=settings.LLM_OPENAI_BASE_URL,
        timeout_seconds=settings.LLM_HTTP_TIMEOUT_SECONDS,
    )


def get_meeting_provider(*, model_override: str | None = None) -> LlmMeetingProvider:
    provider = settings.LLM_PROVIDER.strip().lower()
    if provider != "openai":
        raise BadRequestError(f"Provider LLM não suportado: {settings.LLM_PROVIDER}")
    if not settings.LLM_OPENAI_API_KEY:
        raise BadRequestError("LLM_OPENAI_API_KEY não configurada.")
    model_name = (model_override or "").strip() or settings.LLM_OPENAI_MODEL
    return OpenAiScopeProvider(
        api_key=settings.LLM_OPENAI_API_KEY,
        model_name=model_name,
        base_url=settings.LLM_OPENAI_BASE_URL,
        timeout_seconds=settings.LLM_HTTP_TIMEOUT_SECONDS,
    )
