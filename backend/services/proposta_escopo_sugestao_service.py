from __future__ import annotations

import json
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import case, desc, select
from sqlalchemy.orm import Session

from ..exceptions import BadRequestError
from ..models.reuniao_analise import ReuniaoAnalise
from ..schemas.escopo_sugestao_ia import EscopoSugestaoBloco, EscopoSugestaoIaResponse
from .escopo_ai_service import read_scope_upload_files
from .llm.llm_factory import get_scope_provider
from .llm_agente_service import get_agent_by_codigo
from .proposta_service import _get_proposta


def _truncate(text: str | None, max_len: int) -> str:
    if not text:
        return ""
    s = str(text).replace("\x00", "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _indent(block: str, prefix: str = "    ") -> str:
    if not block.strip():
        return prefix + "(vazio)"
    return "\n".join(prefix + line for line in block.split("\n"))


def _tipo_label(tipo: str) -> str:
    m = {
        "projeto": "Projeto",
        "planos": "Planos (recorrente)",
        "hibrida": "Híbrida (projeto + planos)",
    }
    return m.get((tipo or "").strip().lower(), tipo or "-")


def _format_reuniao_para_contexto(ran: ReuniaoAnalise, transcricao_max: int) -> str:
    linhas = [
        f"- ID: {ran.ranId} | Status: {ran.ranStatus} | Registro: {ran.ranDataCriacao}",
    ]
    if ran.ranStatus != "concluido":
        linhas.append(
            "  (Atenção: esta análise pode não ter resultado da IA ainda; use transcrição/dados brutos se forem o único conteúdo.)"
        )
    if ran.ranProcessadoEm:
        linhas.append(f"  Processado em: {ran.ranProcessadoEm}")
    if ran.ranResumo:
        linhas.append("  Resumo:\n" + _indent(_truncate(ran.ranResumo, 8000)))
    if ran.ranFeedbackIa:
        linhas.append("  Feedback IA:\n" + _indent(_truncate(ran.ranFeedbackIa, 4000)))
    if ran.ranDoresOportunidadesSugeridas:
        linhas.append(
            "  Dores e oportunidades:\n" + _indent(_truncate(ran.ranDoresOportunidadesSugeridas, 4000))
        )
    if ran.ranObservacoesSugeridas:
        linhas.append("  Observações sugeridas:\n" + _indent(_truncate(ran.ranObservacoesSugeridas, 4000)))
    if ran.ranProximosPassosSugeridos:
        linhas.append("  Próximos passos:\n" + _indent(_truncate(ran.ranProximosPassosSugeridos, 2000)))
    if ran.ranTranscricao:
        linhas.append("  Transcrição (trecho):\n" + _indent(_truncate(ran.ranTranscricao, transcricao_max)))
    if ran.ranRespostaJson and isinstance(ran.ranRespostaJson, dict):
        try:
            js = json.dumps(ran.ranRespostaJson, ensure_ascii=False, indent=2)
            linhas.append("  JSON resposta IA (referência):\n" + _indent(_truncate(js, 6000)))
        except (TypeError, ValueError):
            pass
    return "\n".join(linhas)


def _load_analises(db: Session, opo_id: int, company_id: Optional[int], limit: int = 15) -> list[ReuniaoAnalise]:
    """
    Prioriza análises com IA concluída (mais recente por ranProcessadoEm), depois as demais por data.
    Evita que a “última” linha seja só um registro pendente sem resumo quando já existe análise processada.
    """
    stmt = select(ReuniaoAnalise).where(ReuniaoAnalise.ranOpoId == opo_id, ReuniaoAnalise.ranAtivo.is_(True))
    if company_id is not None:
        stmt = stmt.where(ReuniaoAnalise.ranEmpId == company_id)
    prioridade_concluida = case((ReuniaoAnalise.ranStatus == "concluido", 0), else_=1)
    # MySQL não suporta NULLS LAST; coloca registros com ranProcessadoEm preenchido antes dos NULL
    processado_nao_nulo_primeiro = case((ReuniaoAnalise.ranProcessadoEm.is_(None), 1), else_=0)
    stmt = (
        stmt.order_by(
            prioridade_concluida.asc(),
            processado_nao_nulo_primeiro.asc(),
            desc(ReuniaoAnalise.ranProcessadoEm),
            desc(ReuniaoAnalise.ranDataCriacao),
        ).limit(limit)
    )
    return list(db.scalars(stmt).all())


def _normalize_sugestao(payload: dict, provider_name: str, model_name: str) -> EscopoSugestaoIaResponse:
    raw_blocos = payload.get("blocos")
    if not isinstance(raw_blocos, list):
        raw_blocos = []
    out_blocos: list[EscopoSugestaoBloco] = []
    for b in raw_blocos:
        if not isinstance(b, dict):
            continue
        titulo = str(b.get("titulo", "")).strip() or "Bloco sugerido"
        subtitulo = str(b.get("subtitulo", "")).strip()
        itens_raw = b.get("itens")
        itens: list[str] = []
        if isinstance(itens_raw, list):
            for it in itens_raw:
                s = str(it).strip()
                if s:
                    itens.append(s)
        out_blocos.append(EscopoSugestaoBloco(titulo=titulo, subtitulo=subtitulo, itens=itens))
    obs = str(payload.get("observacoes", "") or "").strip()
    return EscopoSugestaoIaResponse(
        blocos=out_blocos,
        observacoes=obs[:4000],
        provider=provider_name,
        model=model_name,
    )


async def gerar_sugestao_escopo_para_proposta(
    db: Session,
    prp_id: int,
    company_id: Optional[int],
    pontos_principais: str,
    observacoes_adicionais: str,
    files: list[UploadFile] | None,
) -> EscopoSugestaoIaResponse:
    proposta = _get_proposta(db, prp_id, company_id)
    pontos = (pontos_principais or "").strip()
    obs_user = (observacoes_adicionais or "").strip()
    analises = _load_analises(db, proposta.prpOpoId, company_id)
    file_input = await read_scope_upload_files(files)

    tem_analise = len(analises) > 0
    tem_texto_usuario = bool(pontos or obs_user)
    tem_arquivo = bool(file_input.texts or file_input.images)
    if not tem_analise and not tem_texto_usuario and not tem_arquivo:
        raise BadRequestError(
            "Informe pontos principais ou observações, anexe arquivos ou cadastre análises de reunião na oportunidade."
        )

    sec_ultima = ""
    sec_historico = ""
    if analises:
        ultima = analises[0]
        sec_ultima = _format_reuniao_para_contexto(ultima, transcricao_max=12000)
        if len(analises) > 1:
            hist_parts = []
            for ran in analises[1:]:
                hist_parts.append(_format_reuniao_para_contexto(ran, transcricao_max=4000))
            sec_historico = "\n\n---\n\n".join(hist_parts)

    contexto = f"""INSTRUÇÃO CRÍTICA
- Gere uma sugestão de escopo NOVA e independente.
- NÃO copie, reproduza nem “aperfeiçoe” blocos de escopo já existentes na proposta (eles NÃO foram enviados neste contexto de propósito).
- Após os textos do usuário, dê PESO ALTO à análise da reunião (resumo, dores, oportunidades, próximos passos, transcrição).

DADOS DA PROPOSTA (somente metadados)
Título: {proposta.prpTitulo}
Tipo: {_tipo_label(proposta.prpTipo)}

=== PRIORIDADE MÁXIMA — PONTOS PRINCIPAIS (usuário) ===
{pontos or "(não informado)"}

=== OBSERVAÇÕES ADICIONAIS (usuário) ===
{obs_user or "(não informado)"}

=== ANÁLISE DE REUNIÃO — PRINCIPAL (priorize após os inputs do usuário) ===
{sec_ultima or "(nenhuma análise cadastrada para esta oportunidade)"}

=== OUTRAS ANÁLISES DE REUNIÃO (contexto complementar) ===
{sec_historico or "(não há análises adicionais)"}

Agora gere o escopo com base nos dados acima (usuário + reunião + anexos, se houver).
"""
    resolved = get_agent_by_codigo(db, company_id, "escopo_sugestao")
    if resolved.llm_provider.strip().lower() != "openai":
        raise BadRequestError("Apenas o provider 'openai' é suportado para sugestão de escopo.")
    provider = get_scope_provider(model_override=resolved.llm_model)
    raw = provider.generate_escopo_sugestao(contexto, file_input, system_prompt=resolved.system_prompt)
    return _normalize_sugestao(raw, provider.provider_name, provider.model_name)
