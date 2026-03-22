from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ScopeSourceText:
    filename: str
    content: str


@dataclass
class ScopeSourceImage:
    filename: str
    mime_type: str
    base64_data: str


@dataclass
class ScopeGenerationInput:
    texts: list[ScopeSourceText]
    images: list[ScopeSourceImage]


class LlmScopeProvider(Protocol):
    provider_name: str
    model_name: str

    def generate_scope(self, payload: ScopeGenerationInput, system_prompt: str | None = None) -> dict:
        ...

    def generate_escopo_sugestao(
        self, context_text: str, payload: ScopeGenerationInput, system_prompt: str | None = None
    ) -> dict:
        ...


@dataclass
class MeetingAnalysisInput:
    oportunidade_contexto: str
    transcricao: str
    materiais: list[ScopeSourceText]


class LlmMeetingProvider(Protocol):
    provider_name: str
    model_name: str

    def generate_meeting_analysis(self, payload: MeetingAnalysisInput, system_prompt: str) -> dict:
        ...
