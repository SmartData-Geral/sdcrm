from __future__ import annotations

import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..exceptions import BadRequestError
from ..models.oportunidade import Oportunidade
from ..models.proposta import Proposta
from ..models.proposta_versao import PropostaVersao
from ..models.reuniao_analise import ReuniaoAnalise
from ..schemas.oportunidade import (
    OportunidadeSmartAgenteChatRequest,
    OportunidadeSmartAgenteChatResponse,
)
from .llm.llm_factory import get_meeting_provider
from .llm_agente_service import get_agent_by_codigo
from .oportunidade_service import get_oportunidade

AGENT_CODIGO = "oportunidade_smart_agente"
MAX_CONTEXT_TOTAL = 28_000
MAX_REUNIOES = 3
MAX_SNAPSHOT_POR_PROPOSTA = 8_000
MAX_MSG_CONTENT = 12_000
MAX_TURNS = 40


def _truncate(text: str, max_len: int) -> str:
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 24].rstrip() + "\n...[conteúdo truncado]"


def _build_oportunidade_crm_block(opo: Oportunidade) -> str:
    return (
        f"Título: {opo.opoTitulo}\n"
        f"Contato: {opo.opoNomeContato or '-'}\n"
        f"Empresa contato: {opo.opoEmpresaContato or '-'}\n"
        f"E-mail: {opo.opoEmail or '-'}\n"
        f"Telefone: {opo.opoTelefone or '-'}\n"
        f"Solução: {opo.opoSolucao or '-'}\n"
        f"Lead score: {opo.opoLeadScore if opo.opoLeadScore is not None else '-'}\n"
        f"Temperatura: {opo.opoTemperatura or '-'}\n"
        f"Valor oportunidade: {opo.opoValorOportunidade if opo.opoValorOportunidade is not None else '-'}\n"
        f"Reunião confirmada: {'sim' if opo.opoReuniaoConfirmada else 'não'}\n"
        f"Proposta enviada: {'sim' if opo.opoPropostaEnviada else 'não'}\n"
        f"Status fechamento: {opo.opoStatusFechamento or 'ativo'}\n"
        f"Dores / motivadores: {opo.opoDoresMotivadores or '-'}\n"
        f"Comentários: {opo.opoComentarios or '-'}"
    )


def _reunioes_concluidas(
    db: Session, opo_id: int, company_id: Optional[int], limit: int
) -> list[ReuniaoAnalise]:
    stmt = select(ReuniaoAnalise).where(
        ReuniaoAnalise.ranOpoId == opo_id,
        ReuniaoAnalise.ranAtivo.is_(True),
        ReuniaoAnalise.ranStatus == "concluido",
    )
    if company_id is not None:
        stmt = stmt.where(ReuniaoAnalise.ranEmpId == company_id)
    stmt = stmt.order_by(ReuniaoAnalise.ranDataCriacao.desc()).limit(limit)
    return list(db.scalars(stmt).all())


def _propostas_com_snapshot(
    db: Session, opo_id: int, company_id: Optional[int]
) -> list[tuple[Proposta, PropostaVersao | None]]:
    stmt = select(Proposta).where(Proposta.prpOpoId == opo_id, Proposta.prpAtivo.is_(True))
    if company_id is not None:
        stmt = stmt.where(Proposta.prpEmpId == company_id)
    stmt = stmt.order_by(Proposta.prpDataCriacao.desc())
    propostas = list(db.scalars(stmt).all())
    out: list[tuple[Proposta, PropostaVersao | None]] = []
    for p in propostas:
        versao: PropostaVersao | None = None
        if p.prpVersaoAtual is not None:
            v_stmt = select(PropostaVersao).where(
                PropostaVersao.prvPrpId == p.prpId,
                PropostaVersao.prvNumero == p.prpVersaoAtual,
                PropostaVersao.prvAtivo.is_(True),
            )
            if company_id is not None:
                v_stmt = v_stmt.where(PropostaVersao.prvEmpId == company_id)
            versao = db.scalars(v_stmt).first()
        out.append((p, versao))
    return out


def _snapshot_text(versao: PropostaVersao | None) -> str:
    if versao is None:
        return "(sem versão salva)"
    parts: list[str] = []
    if versao.prvJsonSnapshot:
        try:
            raw = json.dumps(versao.prvJsonSnapshot, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            raw = str(versao.prvJsonSnapshot)
        parts.append("JSON da versão:\n" + _truncate(raw, MAX_SNAPSHOT_POR_PROPOSTA))
    html = (versao.prvHtmlSnapshot or "").strip()
    if html:
        parts.append("HTML (trecho):\n" + _truncate(html, min(4000, MAX_SNAPSHOT_POR_PROPOSTA)))
    if not parts:
        return "(versão sem snapshot textual)"
    return "\n\n".join(parts)


def build_context_text(db: Session, opo_id: int, company_id: Optional[int], opo: Oportunidade) -> str:
    blocks: list[str] = ["--- CRM (oportunidade) ---\n" + _build_oportunidade_crm_block(opo)]

    reunioes = _reunioes_concluidas(db, opo_id, company_id, MAX_REUNIOES)
    if reunioes:
        linhas: list[str] = []
        for r in reversed(reunioes):
            bloco = (
                f"Análise ranId={r.ranId} ({r.ranDataCriacao}):\n"
                f"Resumo da reunião: {r.ranResumo or '-'}\n"
                f"Feedback IA: {(r.ranFeedbackIa or '-')[:2000]}\n"
                f"Próximos passos sugeridos: {r.ranProximosPassosSugeridos or '-'}\n"
                f"Dores/oportunidades (IA): {r.ranDoresOportunidadesSugeridas or '-'}"
            )
            linhas.append(bloco)
        blocks.append("--- Reuniões (análises concluídas, mais recentes primeiro no bloco acima) ---\n" + "\n\n".join(linhas))
    else:
        blocks.append("--- Reuniões ---\nNenhuma análise de reunião concluída registrada.")

    props = _propostas_com_snapshot(db, opo_id, company_id)
    if props:
        partes_p: list[str] = []
        for p, v in props:
            partes_p.append(
                f"Proposta prpId={p.prpId}: {p.prpTitulo}\n"
                f"Tipo: {p.prpTipo} | Status: {p.prpStatus} | Versão atual: {p.prpVersaoAtual}\n"
                f"{_snapshot_text(v)}"
            )
        blocks.append("--- Propostas ---\n" + "\n\n---\n\n".join(partes_p))
    else:
        blocks.append("--- Propostas ---\nNenhuma proposta ativa nesta oportunidade.")

    full = "\n\n".join(blocks)
    return _truncate(full, MAX_CONTEXT_TOTAL)


def _validate_client_messages(messages: list[dict[str, str]]) -> None:
    if not messages:
        raise BadRequestError("Envie ao menos uma mensagem.")
    if len(messages) > MAX_TURNS:
        raise BadRequestError(f"No máximo {MAX_TURNS} mensagens por requisição.")
    if messages[-1]["role"] != "user":
        raise BadRequestError("A última mensagem deve ser do usuário.")
    for i, m in enumerate(messages):
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role not in ("user", "assistant"):
            raise BadRequestError("Cada mensagem deve ter role 'user' ou 'assistant'.")
        expected = "user" if i % 2 == 0 else "assistant"
        if role != expected:
            raise BadRequestError("A conversa deve alternar user e assistant, começando por user.")
        if len(content) > MAX_MSG_CONTENT:
            raise BadRequestError(f"Mensagem excede {MAX_MSG_CONTENT} caracteres.")
        if role == "user" and not content:
            raise BadRequestError("Mensagem do usuário não pode ser vazia.")
        if role == "assistant" and not content:
            raise BadRequestError("Mensagem do assistente não pode ser vazia.")


def chat_smart_agente(
    db: Session,
    opo_id: int,
    company_id: Optional[int],
    data: OportunidadeSmartAgenteChatRequest,
) -> OportunidadeSmartAgenteChatResponse:
    oportunidade = get_oportunidade(db, opo_id, company_id)
    resolved = get_agent_by_codigo(db, company_id, AGENT_CODIGO)
    if resolved.llm_provider.strip().lower() != "openai":
        raise BadRequestError("Apenas o provider 'openai' é suportado para o Smart Agente.")

    client_msgs = [{"role": m.role, "content": m.content.strip()} for m in data.messages]
    _validate_client_messages(client_msgs)

    context = build_context_text(db, opo_id, company_id, oportunidade)
    system_content = (
        f"{resolved.system_prompt}\n\n=== Dados atuais da oportunidade (somente leitura) ===\n{context}"
    )
    system_content = _truncate(system_content, MAX_CONTEXT_TOTAL + 4000)

    openai_messages: list[dict[str, str]] = [{"role": "system", "content": system_content}, *client_msgs]

    provider = get_meeting_provider(model_override=resolved.llm_model)
    reply = provider.chat_completion(openai_messages, temperature=0.6)
    return OportunidadeSmartAgenteChatResponse(message=reply)
