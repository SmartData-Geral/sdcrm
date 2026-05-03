from __future__ import annotations

import json
from typing import Any

from openai import APIConnectionError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError

from ....exceptions import BadRequestError
from ...llm_agente_defaults import PROMPT_ESCOPO_ARQUIVO, PROMPT_ESCOPO_SUGESTAO_CONSULTIVO
from .base import LlmScopeProvider, MeetingAnalysisInput, ScopeGenerationInput


class OpenAiScopeProvider(LlmScopeProvider):
    provider_name = "openai"

    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str | None = None,
        *,
        timeout_seconds: float = 180.0,
    ) -> None:
        self.model_name = model_name
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=2,
        )

    def _chat_completions_create(self, **kwargs: Any):
        try:
            return self._client.chat.completions.create(**kwargs)
        except APIConnectionError as exc:
            raise BadRequestError(
                "Não foi possível conectar à API da OpenAI. Verifique: internet ativa; firewall/antivírus "
                "permitindo saída HTTPS para api.openai.com (ou ao host definido em LLM_OPENAI_BASE_URL); "
                "em rede corporativa, configure proxy (variáveis HTTP_PROXY e HTTPS_PROXY) ou VPN. "
                f"Erro: {exc}"
            ) from exc
        except APITimeoutError as exc:
            raise BadRequestError(
                "Tempo esgotado ao chamar a OpenAI. Tente novamente ou reduza o tamanho da transcrição/anexos. "
                f"Ajuste LLM_HTTP_TIMEOUT_SECONDS no .env se necessário. Detalhe: {exc}"
            ) from exc
        except AuthenticationError as exc:
            raise BadRequestError(
                "Autenticação recusada pela OpenAI. Confira se LLM_OPENAI_API_KEY está correta e ativa."
            ) from exc
        except RateLimitError as exc:
            raise BadRequestError("Limite de uso da API OpenAI atingido. Aguarde e tente novamente.") from exc

    def generate_scope(self, payload: ScopeGenerationInput) -> dict:
        user_content: list[dict[str, Any]] = []
        if payload.texts:
            text_blocks = []
            for item in payload.texts:
                text_blocks.append(f"Arquivo: {item.filename}\nConteúdo:\n{item.content}")
            user_content.append({"type": "text", "text": "\n\n---\n\n".join(text_blocks)})

        for image in payload.images:
            user_content.append({"type": "text", "text": f"Imagem enviada: {image.filename}"})
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image.mime_type};base64,{image.base64_data}"},
                }
            )

        if not user_content:
            raise BadRequestError("Envie ao menos um arquivo para gerar o escopo.")

        sys_prompt = (system_prompt or "").strip() or PROMPT_ESCOPO_ARQUIVO
        response = self._chat_completions_create(
            model=self.model_name,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise BadRequestError("A IA não retornou conteúdo para geração de escopo.")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise BadRequestError("A IA retornou um formato inválido de escopo.") from exc

    def generate_escopo_sugestao(
        self, context_text: str, payload: ScopeGenerationInput, system_prompt: str | None = None
    ) -> dict:
        user_content: list[dict[str, Any]] = [{"type": "text", "text": context_text}]
        if payload.texts:
            text_blocks = []
            for item in payload.texts:
                text_blocks.append(f"Arquivo anexado pelo usuário: {item.filename}\nConteúdo:\n{item.content}")
            user_content.append(
                {"type": "text", "text": "\n\n---\n\nMateriais de apoio (anexos)\n\n" + "\n\n---\n\n".join(text_blocks)}
            )
        for image in payload.images:
            user_content.append({"type": "text", "text": f"Imagem anexada: {image.filename}"})
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image.mime_type};base64,{image.base64_data}"},
                }
            )
        if not str(context_text or "").strip() and not payload.texts and not payload.images:
            raise BadRequestError("Não há conteúdo suficiente para gerar o escopo.")

        sys_prompt = (system_prompt or "").strip() or PROMPT_ESCOPO_SUGESTAO_CONSULTIVO
        response = self._chat_completions_create(
            model=self.model_name,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.25,
        )
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise BadRequestError("A IA não retornou conteúdo para a sugestão de escopo.")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise BadRequestError("A IA retornou um formato JSON inválido para a sugestão de escopo.") from exc

    def generate_meeting_analysis(self, payload: MeetingAnalysisInput, system_prompt: str) -> dict:
        materiais_text = "\n\n".join(
            [f"Arquivo: {item.filename}\nConteúdo extraído:\n{item.content}" for item in payload.materiais]
        )
        prior = (payload.reunioes_anteriores_resumo or "").strip()
        bloco_anteriores = ""
        if prior:
            bloco_anteriores = (
                "=== Reuniões anteriores da mesma oportunidade (contexto cumulativo) ===\n"
                f"{prior}\n\n"
            )
        prompt_usuario = (
            "Contexto da oportunidade:\n"
            f"{payload.oportunidade_contexto}\n\n"
            f"{bloco_anteriores}"
            "=== Reunião atual (foco principal desta análise) ===\n"
            "Transcrição principal:\n"
            f"{payload.transcricao}\n\n"
            "Materiais complementares desta reunião:\n"
            f"{materiais_text or 'Sem materiais complementares legíveis.'}"
        )
        response = self._chat_completions_create(
            model=self.model_name,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_usuario},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise BadRequestError("A IA não retornou conteúdo para análise da reunião.")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise BadRequestError("A IA retornou um formato inválido de análise.") from exc

    def chat_completion(self, messages: list[dict[str, str]], *, temperature: float = 0.6) -> str:
        """Chat em texto livre (sem response_format JSON)."""
        if not messages:
            raise BadRequestError("Mensagens vazias para o chat.")
        response = self._chat_completions_create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
        )
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise BadRequestError("A IA não retornou conteúdo para o chat.")
        return str(content).strip()
