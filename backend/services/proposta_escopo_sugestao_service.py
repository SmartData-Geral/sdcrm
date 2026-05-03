from __future__ import annotations

import json
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import asc, select
from sqlalchemy.orm import Session

from ..exceptions import BadRequestError
from ..models.reuniao_analise import ReuniaoAnalise
from ..schemas.escopo_sugestao_ia import EscopoSugestaoBloco, EscopoSugestaoIaResponse
from .escopo_ai_service import read_scope_upload_files
from .llm.llm_factory import get_scope_provider
from .llm_agente_service import get_agent_by_codigo
from .proposta_service import _get_proposta
from .reuniao_contexto_llm import caps_por_num_reunioes_escopo, format_reuniao_para_contexto_escopo


def _tipo_label(tipo: str) -> str:
    m = {
        "projeto": "Projeto",
        "planos": "Planos (recorrente)",
        "hibrida": "Híbrida (projeto + planos)",
    }
    return m.get((tipo or "").strip().lower(), tipo or "-")


def _load_analises_escopo_cronologicas(db: Session, opo_id: int, company_id: Optional[int], limit: int = 15) -> list[ReuniaoAnalise]:
    stmt = select(ReuniaoAnalise).where(ReuniaoAnalise.ranOpoId == opo_id, ReuniaoAnalise.ranAtivo.is_(True))
    if company_id is not None:
        stmt = stmt.where(ReuniaoAnalise.ranEmpId == company_id)
    stmt = stmt.order_by(asc(ReuniaoAnalise.ranDataCriacao)).limit(limit)
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
    analises = _load_analises_escopo_cronologicas(db, proposta.prpOpoId, company_id)
    file_input = await read_scope_upload_files(files)

    tem_analise = len(analises) > 0
    tem_texto_usuario = bool(pontos or obs_user)
    tem_arquivo = bool(file_input.texts or file_input.images)
    if not tem_analise and not tem_texto_usuario and not tem_arquivo:
        raise BadRequestError(
            "Informe pontos principais ou observações, anexe arquivos ou cadastre análises de reunião na oportunidade."
        )

    if analises:
        n = len(analises)
        caps = caps_por_num_reunioes_escopo(n)
        blocos_r: list[str] = []
        for i, ran in enumerate(analises, start=1):
            body = format_reuniao_para_contexto_escopo(ran, **caps)
            blocos_r.append(f"--- Reunião {i} de {n} (ordem cronológica) ---\n{body}")
        sec_reunioes = "\n\n".join(blocos_r)
    else:
        sec_reunioes = "(nenhuma análise cadastrada para esta oportunidade)"

    contexto = f"""INSTRUÇÃO CRÍTICA
- Gere uma sugestão de escopo NOVA e independente.
- NÃO copie, reproduza nem “aperfeiçoe” blocos de escopo já existentes na proposta (eles NÃO foram enviados neste contexto de propósito).
- Após os textos do usuário, use TODAS as análises de reunião com peso alto e equilibrado (cronologia informada abaixo).

DADOS DA PROPOSTA (somente metadados)
Título: {proposta.prpTitulo}
Tipo: {_tipo_label(proposta.prpTipo)}

=== PRIORIDADE MÁXIMA — PONTOS PRINCIPAIS (usuário) ===
{pontos or "(não informado)"}

=== OBSERVAÇÕES ADICIONAIS (usuário) ===
{obs_user or "(não informado)"}

=== ANÁLISES DE REUNIÃO DESTA OPORTUNIDADE (ordem cronológica; mesmo peso) ===
{sec_reunioes}

Agora gere o escopo com base nos dados acima (usuário + reuniões + anexos, se houver).
"""
    resolved = get_agent_by_codigo(db, company_id, "escopo_sugestao")
    if resolved.llm_provider.strip().lower() != "openai":
        raise BadRequestError("Apenas o provider 'openai' é suportado para sugestão de escopo.")
    provider = get_scope_provider(model_override=resolved.llm_model)
    raw = provider.generate_escopo_sugestao(contexto, file_input, system_prompt=resolved.system_prompt)
    return _normalize_sugestao(raw, provider.provider_name, provider.model_name)
