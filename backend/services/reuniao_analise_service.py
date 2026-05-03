from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Iterable, Optional

from fastapi import UploadFile
from sqlalchemy import asc, func, select
from sqlalchemy.orm import Session

from ..exceptions import BadRequestError, NotFoundError
from ..models.oportunidade import Oportunidade
from ..models.reuniao_analise import ReuniaoAnalise
from ..schemas.reuniao_analise import (
    ReuniaoAnaliseArquivoResumo,
    ReuniaoAnaliseListResponse,
    ReuniaoAnaliseProcessResult,
    ReuniaoAnaliseResponse,
)
from ..config import settings
from .llm.llm_factory import get_meeting_provider
from .llm.providers.base import MeetingAnalysisInput, ScopeSourceText
from .llm_agente_service import get_agent_by_codigo
from .reuniao_contexto_llm import build_reunioes_anteriores_resumo_para_analise
from .oportunidade_service import get_oportunidade

ALLOWED_EXTENSIONS = {".txt", ".csv", ".json", ".pdf", ".md", ".log", ".tsv"}
ALLOWED_CONTENT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "text/tab-separated-values",
    "application/csv",
    "application/json",
    "application/pdf",
}
MAX_TEXT_CHARS = 60000


def _sanitize_text(value: str) -> str:
    clean = value.replace("\x00", "").strip()
    if len(clean) > MAX_TEXT_CHARS:
        return clean[:MAX_TEXT_CHARS]
    return clean


def _extract_extension(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return f".{filename.rsplit('.', 1)[-1].lower()}"


def _parse_csv_text(decoded: str) -> str:
    reader = csv.reader(io.StringIO(decoded))
    lines: list[str] = []
    for idx, row in enumerate(reader, start=1):
        if not row:
            continue
        normalized = [str(col).strip() for col in row]
        if all(not col for col in normalized):
            continue
        lines.append(f"Linha {idx}: {' | '.join(normalized)}")
    return "\n".join(lines)


def _extract_pdf_text(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return _sanitize_text("\n".join(pages))


async def _extract_files_summary(files: Iterable[UploadFile]) -> list[ReuniaoAnaliseArquivoResumo]:
    items: list[ReuniaoAnaliseArquivoResumo] = []
    for upload in files:
        filename = upload.filename or "arquivo"
        ext = _extract_extension(filename)
        content_type = (upload.content_type or "").lower() or None
        raw_content = await upload.read()
        tamanho = len(raw_content)
        max_bytes = settings.LLM_MAX_FILE_SIZE_MB * 1024 * 1024
        if tamanho > max_bytes:
            items.append(
                ReuniaoAnaliseArquivoResumo(
                    nome=filename,
                    mime=content_type,
                    extensao=ext or None,
                    tamanho_bytes=tamanho,
                    leitura_sucesso=False,
                    mensagem=f"Arquivo excede o limite de {settings.LLM_MAX_FILE_SIZE_MB}MB.",
                    conteudo_extraido=None,
                )
            )
            continue

        if ext not in ALLOWED_EXTENSIONS:
            items.append(
                ReuniaoAnaliseArquivoResumo(
                    nome=filename,
                    mime=content_type,
                    extensao=ext or None,
                    tamanho_bytes=tamanho,
                    leitura_sucesso=False,
                    mensagem=f"Formato '{ext or 'desconhecido'}' não suportado nesta etapa.",
                    conteudo_extraido=None,
                )
            )
            continue
        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            items.append(
                ReuniaoAnaliseArquivoResumo(
                    nome=filename,
                    mime=content_type,
                    extensao=ext or None,
                    tamanho_bytes=tamanho,
                    leitura_sucesso=False,
                    mensagem=f"Tipo MIME '{content_type}' não suportado nesta etapa.",
                    conteudo_extraido=None,
                )
            )
            continue
        if tamanho == 0:
            items.append(
                ReuniaoAnaliseArquivoResumo(
                    nome=filename,
                    mime=content_type,
                    extensao=ext or None,
                    tamanho_bytes=0,
                    leitura_sucesso=False,
                    mensagem="Arquivo vazio.",
                    conteudo_extraido=None,
                )
            )
            continue

        try:
            if ext == ".pdf" or content_type == "application/pdf":
                extracted = _extract_pdf_text(raw_content)
                if not extracted:
                    raise ValueError("PDF sem texto legível.")
            else:
                decoded = raw_content.decode("utf-8", errors="ignore")
                if ext in {".json"} or content_type == "application/json":
                    parsed = json.loads(decoded)
                    extracted = json.dumps(parsed, ensure_ascii=False, indent=2)
                elif ext in {".csv", ".tsv"} or content_type in {"text/csv", "application/csv"}:
                    extracted = _parse_csv_text(decoded)
                else:
                    extracted = decoded
                extracted = _sanitize_text(extracted)
                if not extracted:
                    raise ValueError("Sem conteúdo textual legível.")

            items.append(
                ReuniaoAnaliseArquivoResumo(
                    nome=filename,
                    mime=content_type,
                    extensao=ext or None,
                    tamanho_bytes=tamanho,
                    leitura_sucesso=True,
                    mensagem=None,
                    conteudo_extraido=extracted,
                )
            )
        except Exception as exc:
            items.append(
                ReuniaoAnaliseArquivoResumo(
                    nome=filename,
                    mime=content_type,
                    extensao=ext or None,
                    tamanho_bytes=tamanho,
                    leitura_sucesso=False,
                    mensagem=f"Falha ao ler arquivo: {exc}",
                    conteudo_extraido=None,
                )
            )
    return items


async def _read_transcricao_arquivo(upload: UploadFile) -> tuple[str, str, int, str | None, str | None]:
    """Extrai texto de um único arquivo de transcrição. Falha com BadRequestError se inválido."""
    filename = upload.filename or "transcricao"
    ext = _extract_extension(filename)
    content_type = (upload.content_type or "").lower() or None
    raw_content = await upload.read()
    tamanho = len(raw_content)
    max_bytes = settings.LLM_MAX_FILE_SIZE_MB * 1024 * 1024
    if tamanho > max_bytes:
        raise BadRequestError(
            f"O arquivo de transcrição '{filename}' excede o limite de {settings.LLM_MAX_FILE_SIZE_MB}MB."
        )

    if ext not in ALLOWED_EXTENSIONS:
        raise BadRequestError(
            f"Formato de transcrição não suportado: '{ext or 'desconhecido'}'. "
            "Use .txt, .csv, .json, .pdf, .md, .log ou .tsv."
        )
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise BadRequestError(f"Tipo de arquivo de transcrição não suportado: {content_type}.")
    if tamanho == 0:
        raise BadRequestError("O arquivo de transcrição está vazio.")

    try:
        if ext == ".pdf" or content_type == "application/pdf":
            extracted = _extract_pdf_text(raw_content)
            if not extracted:
                raise ValueError("PDF sem texto legível.")
        else:
            decoded = raw_content.decode("utf-8", errors="ignore")
            if ext in {".json"} or content_type == "application/json":
                parsed = json.loads(decoded)
                extracted = json.dumps(parsed, ensure_ascii=False, indent=2)
            elif ext in {".csv", ".tsv"} or content_type in {"text/csv", "application/csv"}:
                extracted = _parse_csv_text(decoded)
            else:
                extracted = decoded
            extracted = _sanitize_text(extracted)
            if not extracted:
                raise ValueError("Sem conteúdo textual legível.")
    except BadRequestError:
        raise
    except Exception as exc:
        raise BadRequestError(f"Não foi possível ler o arquivo de transcrição: {exc}") from exc

    return extracted, filename, tamanho, content_type, ext or None


def _merge_transcricao_texto_e_arquivo(texto_form: str, texto_arquivo: str, nome_arquivo: str) -> str:
    a = _sanitize_text(texto_form)
    b = _sanitize_text(texto_arquivo)
    if a and b:
        return a + f"\n\n--- Transcrição extraída do arquivo: {nome_arquivo} ---\n\n" + b
    return a or b


def _build_oportunidade_context(oportunidade: Oportunidade) -> str:
    return (
        f"Título: {oportunidade.opoTitulo}\n"
        f"Contato: {oportunidade.opoNomeContato or '-'}\n"
        f"Empresa contato: {oportunidade.opoEmpresaContato or '-'}\n"
        f"Solução: {oportunidade.opoSolucao or '-'}\n"
        f"Lead score atual: {oportunidade.opoLeadScore if oportunidade.opoLeadScore is not None else '-'}\n"
        f"Temperatura atual: {oportunidade.opoTemperatura or '-'}\n"
        f"Dores/motivadores atuais: {oportunidade.opoDoresMotivadores or '-'}\n"
        f"Comentários atuais: {oportunidade.opoComentarios or '-'}"
    )


def _normalize_meeting_result(payload: dict) -> ReuniaoAnaliseProcessResult:
    def as_text(key: str) -> str:
        value = payload.get(key, "")
        return str(value).strip()

    lead_raw = payload.get("lead_score_sugerido")
    lead_score: int | None = None
    if lead_raw is not None and str(lead_raw).strip() != "":
        try:
            lead_score = max(0, min(10, int(lead_raw)))
        except (TypeError, ValueError):
            lead_score = None

    temp_raw = str(payload.get("temperatura_sugerida", "")).strip().lower()
    temperatura = temp_raw if temp_raw in {"frio", "morno", "quente"} else None

    return ReuniaoAnaliseProcessResult(
        resumo_reuniao=as_text("resumo_reuniao"),
        feedback_ia=as_text("feedback_ia"),
        lead_score_sugerido=lead_score,
        temperatura_sugerida=temperatura,  # type: ignore[arg-type]
        dores_oportunidades_sugeridas=as_text("dores_oportunidades_sugeridas"),
        observacoes_sugeridas=as_text("observacoes_sugeridas"),
        proximos_passos_sugeridos=as_text("proximos_passos_sugeridos"),
    )


def _list_reunioes_anteriores_mesma_oportunidade(
    db: Session,
    opo_id: int,
    exclude_ran_id: int,
    company_id: Optional[int],
) -> list[ReuniaoAnalise]:
    stmt = select(ReuniaoAnalise).where(
        ReuniaoAnalise.ranOpoId == opo_id,
        ReuniaoAnalise.ranAtivo.is_(True),
        ReuniaoAnalise.ranId != exclude_ran_id,
    )
    if company_id is not None:
        stmt = stmt.where(ReuniaoAnalise.ranEmpId == company_id)
    stmt = stmt.order_by(asc(ReuniaoAnalise.ranDataCriacao))
    return list(db.scalars(stmt).all())


def _get_reuniao_analise(db: Session, ran_id: int, company_id: Optional[int]) -> ReuniaoAnalise:
    stmt = select(ReuniaoAnalise).where(ReuniaoAnalise.ranId == ran_id, ReuniaoAnalise.ranAtivo.is_(True))
    if company_id is not None:
        stmt = stmt.where(ReuniaoAnalise.ranEmpId == company_id)
    row = db.scalars(stmt).first()
    if row is None:
        raise NotFoundError("Análise de reunião não encontrada.")
    return row


def get_reuniao_analise(db: Session, ran_id: int, company_id: Optional[int]) -> ReuniaoAnaliseResponse:
    row = _get_reuniao_analise(db, ran_id, company_id)
    return ReuniaoAnaliseResponse.model_validate(row)


def list_reuniao_analises(
    db: Session,
    opo_id: int,
    company_id: Optional[int],
    page: int = 1,
    page_size: int = 20,
) -> ReuniaoAnaliseListResponse:
    get_oportunidade(db, opo_id, company_id)
    stmt = select(ReuniaoAnalise).where(ReuniaoAnalise.ranOpoId == opo_id, ReuniaoAnalise.ranAtivo.is_(True))
    if company_id is not None:
        stmt = stmt.where(ReuniaoAnalise.ranEmpId == company_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(ReuniaoAnalise.ranDataCriacao.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return ReuniaoAnaliseListResponse(
        items=[ReuniaoAnaliseResponse.model_validate(item) for item in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def create_reuniao_analise(
    db: Session,
    opo_id: int,
    company_id: Optional[int],
    usu_id: int,
    transcricao: str | None,
    transcricao_arquivos: list[UploadFile],
    files: list[UploadFile],
) -> ReuniaoAnaliseResponse:
    oportunidade = get_oportunidade(db, opo_id, company_id)
    total_envios = len(transcricao_arquivos) + len(files)
    if total_envios > settings.LLM_MAX_FILES:
        raise BadRequestError(f"Envie no máximo {settings.LLM_MAX_FILES} arquivos no total (transcrição + complementares).")

    arquivos_resumo = await _extract_files_summary(files)

    transcricao_clean = _sanitize_text(transcricao or "")
    resumos_transcricao: list[ReuniaoAnaliseArquivoResumo] = []
    for tr_upload in transcricao_arquivos:
        extracted, nome_arquivo_tr, tamanho_bytes, mime_tr, ext_tr = await _read_transcricao_arquivo(tr_upload)
        transcricao_clean = _merge_transcricao_texto_e_arquivo(
            transcricao_clean, extracted, nome_arquivo_tr or "transcricao"
        )
        resumos_transcricao.append(
            ReuniaoAnaliseArquivoResumo(
                nome=nome_arquivo_tr,
                mime=mime_tr,
                extensao=ext_tr,
                tamanho_bytes=tamanho_bytes,
                leitura_sucesso=True,
                mensagem="Conteúdo incorporado ao campo Transcrição (não duplicado nos materiais complementares).",
                conteudo_extraido=None,
            )
        )
    arquivos_resumo = resumos_transcricao + arquivos_resumo
    has_text = bool(transcricao_clean)
    has_file_text = any(item.leitura_sucesso and (item.conteudo_extraido or "").strip() for item in arquivos_resumo)
    if not has_text and not has_file_text:
        raise BadRequestError("Forneça transcrição (texto e/ou arquivo), anexos legíveis ou ambos para criar a análise.")

    obj = ReuniaoAnalise(
        ranEmpId=oportunidade.opoEmpId,
        ranOpoId=oportunidade.opoId,
        ranUsuId=usu_id,
        ranTranscricao=transcricao_clean or None,
        ranArquivosResumo=[item.model_dump() for item in arquivos_resumo],
        ranStatus="pendente",
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return ReuniaoAnaliseResponse.model_validate(obj)


def process_reuniao_analise(db: Session, ran_id: int, company_id: Optional[int]) -> ReuniaoAnaliseResponse:
    obj = _get_reuniao_analise(db, ran_id, company_id)
    oportunidade = get_oportunidade(db, obj.ranOpoId, company_id)
    obj.ranStatus = "processando"
    db.add(obj)
    db.commit()
    db.refresh(obj)

    try:
        arquivos = obj.ranArquivosResumo or []
        materiais: list[ScopeSourceText] = []
        for item in arquivos:
            if not isinstance(item, dict):
                continue
            if not item.get("leitura_sucesso"):
                continue
            conteudo = str(item.get("conteudo_extraido") or "").strip()
            if not conteudo:
                continue
            materiais.append(ScopeSourceText(filename=str(item.get("nome") or "arquivo"), content=conteudo))

        anteriores = _list_reunioes_anteriores_mesma_oportunidade(
            db, obj.ranOpoId, obj.ranId, company_id
        )
        reunioes_anteriores_txt = build_reunioes_anteriores_resumo_para_analise(anteriores)

        payload = MeetingAnalysisInput(
            oportunidade_contexto=_build_oportunidade_context(oportunidade),
            transcricao=str(obj.ranTranscricao or ""),
            materiais=materiais,
            reunioes_anteriores_resumo=reunioes_anteriores_txt,
        )
        resolved = get_agent_by_codigo(db, company_id, "reuniao_analise")
        if resolved.llm_provider.strip().lower() != "openai":
            raise BadRequestError("Apenas o provider 'openai' é suportado para análise de reunião.")
        provider = get_meeting_provider(model_override=resolved.llm_model)
        raw_result = provider.generate_meeting_analysis(payload=payload, system_prompt=resolved.system_prompt)
        result = _normalize_meeting_result(raw_result)

        obj.ranResumo = result.resumo_reuniao
        obj.ranFeedbackIa = result.feedback_ia
        obj.ranLeadScoreSugerido = result.lead_score_sugerido
        obj.ranTemperaturaSugerida = result.temperatura_sugerida
        obj.ranDoresOportunidadesSugeridas = result.dores_oportunidades_sugeridas
        obj.ranObservacoesSugeridas = result.observacoes_sugeridas
        obj.ranProximosPassosSugeridos = result.proximos_passos_sugeridos
        obj.ranPromptUtilizado = resolved.system_prompt
        obj.ranRespostaJson = raw_result
        obj.ranModeloIa = provider.model_name
        obj.ranProcessadoEm = datetime.now(timezone.utc)
        obj.ranStatus = "concluido"
        oportunidade.opoReuniaoConfirmada = True
        db.add(oportunidade)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return ReuniaoAnaliseResponse.model_validate(obj)
    except Exception as exc:
        obj.ranStatus = "erro"
        obj.ranFeedbackIa = f"Falha no processamento da IA: {exc}"
        db.add(obj)
        db.commit()
        db.refresh(obj)
        raise BadRequestError(f"Não foi possível processar a análise de reunião: {exc}") from exc


def apply_observacoes(db: Session, ran_id: int, company_id: Optional[int]) -> ReuniaoAnaliseResponse:
    obj = _get_reuniao_analise(db, ran_id, company_id)
    if not obj.ranObservacoesSugeridas:
        raise BadRequestError("Esta análise não possui observações sugeridas para aplicar.")
    oportunidade = get_oportunidade(db, obj.ranOpoId, company_id)
    oportunidade.opoComentarios = obj.ranObservacoesSugeridas
    db.add(oportunidade)
    db.commit()
    db.refresh(obj)
    return ReuniaoAnaliseResponse.model_validate(obj)


def apply_dores_oportunidades(db: Session, ran_id: int, company_id: Optional[int]) -> ReuniaoAnaliseResponse:
    obj = _get_reuniao_analise(db, ran_id, company_id)
    if not obj.ranDoresOportunidadesSugeridas:
        raise BadRequestError("Esta análise não possui dores/oportunidades sugeridas para aplicar.")
    oportunidade = get_oportunidade(db, obj.ranOpoId, company_id)
    oportunidade.opoDoresMotivadores = obj.ranDoresOportunidadesSugeridas
    db.add(oportunidade)
    db.commit()
    db.refresh(obj)
    return ReuniaoAnaliseResponse.model_validate(obj)


def apply_lead_score(db: Session, ran_id: int, company_id: Optional[int]) -> ReuniaoAnaliseResponse:
    obj = _get_reuniao_analise(db, ran_id, company_id)
    if obj.ranLeadScoreSugerido is None:
        raise BadRequestError("Esta análise não possui lead score sugerido para aplicar.")
    oportunidade = get_oportunidade(db, obj.ranOpoId, company_id)
    oportunidade.opoLeadScore = obj.ranLeadScoreSugerido
    db.add(oportunidade)
    db.commit()
    db.refresh(obj)
    return ReuniaoAnaliseResponse.model_validate(obj)


def apply_temperatura(db: Session, ran_id: int, company_id: Optional[int]) -> ReuniaoAnaliseResponse:
    obj = _get_reuniao_analise(db, ran_id, company_id)
    if not obj.ranTemperaturaSugerida:
        raise BadRequestError("Esta análise não possui temperatura sugerida para aplicar.")
    oportunidade = get_oportunidade(db, obj.ranOpoId, company_id)
    oportunidade.opoTemperatura = obj.ranTemperaturaSugerida
    db.add(oportunidade)
    db.commit()
    db.refresh(obj)
    return ReuniaoAnaliseResponse.model_validate(obj)
