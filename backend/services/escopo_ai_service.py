from __future__ import annotations

import base64
import csv
import json
from io import BytesIO, StringIO
from typing import Iterable, Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session
from pypdf import PdfReader

from ..exceptions import BadRequestError
from ..schemas.escopo_ai import EscopoAiGenerateResponse, EscopoInicialAiResponse
from .llm.llm_factory import get_scope_provider
from .llm.providers.base import ScopeGenerationInput, ScopeSourceImage, ScopeSourceText
from .llm_agente_service import get_agent_by_codigo

ALLOWED_EXTENSIONS = {".json", ".txt", ".csv", ".pdf", ".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_CONTENT_TYPES = {
    "application/json",
    "text/plain",
    "text/csv",
    "application/csv",
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
}
IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
MAX_TEXT_CHARS_PER_FILE = 40000


def _sanitize_text(value: str) -> str:
    clean = value.replace("\x00", "").strip()
    if len(clean) > MAX_TEXT_CHARS_PER_FILE:
        return clean[:MAX_TEXT_CHARS_PER_FILE]
    return clean


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return _sanitize_text("\n".join(pages))


def _parse_csv_text(decoded: str) -> str:
    reader = csv.reader(StringIO(decoded))
    lines: list[str] = []
    for idx, row in enumerate(reader, start=1):
        if not row:
            continue
        normalized = [str(col).strip() for col in row]
        if all(not col for col in normalized):
            continue
        lines.append(f"Linha {idx}: {' | '.join(normalized)}")
    return "\n".join(lines)


def _normalize_escopo(payload: dict) -> EscopoInicialAiResponse:
    raw_escopo = payload.get("escopo_inicial", payload)
    if not isinstance(raw_escopo, dict):
        raise BadRequestError("A IA retornou um formato de escopo inválido.")
    cards = raw_escopo.get("cards")
    if not isinstance(cards, list):
        cards = []
    normalized_cards = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        itens = card.get("itens")
        normalized_items = []
        if isinstance(itens, list):
            for item in itens:
                text = str(item).strip()
                if text:
                    normalized_items.append(text)
        titulo = str(card.get("titulo", "")).strip() or "Bloco de escopo"
        subtitulo = str(card.get("subtitulo", "")).strip()
        normalized_cards.append({"titulo": titulo, "subtitulo": subtitulo, "itens": normalized_items})
    raw_escopo["cards"] = normalized_cards
    return EscopoInicialAiResponse.model_validate(raw_escopo)


def _extract_extension(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return f".{filename.rsplit('.', 1)[-1].lower()}"


async def read_scope_upload_files(files: Iterable[UploadFile] | None) -> ScopeGenerationInput:
    """Extrai textos/imagens de uploads para escopo/IA (lista vazia é válida)."""
    if not files:
        return ScopeGenerationInput(texts=[], images=[])
    return await _read_files(files)


async def _read_files(files: Iterable[UploadFile]) -> ScopeGenerationInput:
    texts: list[ScopeSourceText] = []
    images: list[ScopeSourceImage] = []

    for upload in files:
        ext = _extract_extension(upload.filename)
        content_type = (upload.content_type or "").lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise BadRequestError(f"Extensão não suportada: {ext or 'desconhecida'}.")
        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            raise BadRequestError(f"Tipo de arquivo não suportado: {content_type}.")

        raw_content = await upload.read()
        if not raw_content:
            continue

        if content_type in IMAGE_CONTENT_TYPES:
            images.append(
                ScopeSourceImage(
                    filename=upload.filename or "imagem",
                    mime_type=content_type,
                    base64_data=base64.b64encode(raw_content).decode("ascii"),
                )
            )
            continue

        if ext == ".pdf" or content_type == "application/pdf":
            text_content = _extract_pdf_text(raw_content)
            if not text_content:
                raise BadRequestError(f"O PDF '{upload.filename}' não possui texto legível para IA.")
            texts.append(ScopeSourceText(filename=upload.filename or "documento.pdf", content=text_content))
            continue

        decoded = raw_content.decode("utf-8", errors="ignore")
        if ext == ".json" or content_type == "application/json":
            try:
                parsed = json.loads(decoded)
                decoded = json.dumps(parsed, ensure_ascii=False, indent=2)
            except json.JSONDecodeError as exc:
                raise BadRequestError(f"O arquivo JSON '{upload.filename}' é inválido.") from exc
        elif ext == ".csv" or content_type in {"text/csv", "application/csv"}:
            decoded = _parse_csv_text(decoded)
        text_content = _sanitize_text(decoded)
        if text_content:
            texts.append(ScopeSourceText(filename=upload.filename or "arquivo.txt", content=text_content))

    return ScopeGenerationInput(texts=texts, images=images)


async def generate_scope_from_files(
    db: Session,
    company_id: Optional[int],
    files: list[UploadFile],
) -> EscopoAiGenerateResponse:
    if not files:
        raise BadRequestError("Envie ao menos um arquivo para gerar o escopo.")

    payload = await _read_files(files)
    resolved = get_agent_by_codigo(db, company_id, "escopo_arquivo")
    if resolved.llm_provider.strip().lower() != "openai":
        raise BadRequestError("Apenas o provider 'openai' é suportado para geração de escopo por arquivo.")
    provider = get_scope_provider(model_override=resolved.llm_model)
    llm_output = provider.generate_scope(payload, system_prompt=resolved.system_prompt)
    escopo = _normalize_escopo(llm_output)
    return EscopoAiGenerateResponse(escopo_inicial=escopo, provider=provider.provider_name, model=provider.model_name)
