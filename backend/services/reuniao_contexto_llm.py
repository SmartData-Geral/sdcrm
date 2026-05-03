"""Formatação de análises de reunião para prompts de IA (escopo na proposta e análise cumulativa)."""

from __future__ import annotations

import json

from ..models.reuniao_analise import ReuniaoAnalise

PRIOR_REUNIOES_ANALISE_MAX_CHARS = 14_000


def truncate_for_llm(text: str | None, max_len: int) -> str:
    if not text:
        return ""
    s = str(text).replace("\x00", "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def indent_for_llm(block: str, prefix: str = "    ") -> str:
    if not block.strip():
        return prefix + "(vazio)"
    return "\n".join(prefix + line for line in block.split("\n"))


def format_reuniao_para_contexto_escopo(
    ran: ReuniaoAnalise,
    transcricao_max: int,
    *,
    resumo_max: int = 8000,
    feedback_ia_max: int = 4000,
    dores_max: int = 4000,
    observacoes_max: int = 4000,
    proximos_max: int = 2000,
    json_max: int = 6000,
) -> str:
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
        linhas.append("  Resumo:\n" + indent_for_llm(truncate_for_llm(ran.ranResumo, resumo_max)))
    if ran.ranFeedbackIa:
        linhas.append("  Feedback IA:\n" + indent_for_llm(truncate_for_llm(ran.ranFeedbackIa, feedback_ia_max)))
    if ran.ranDoresOportunidadesSugeridas:
        linhas.append(
            "  Dores e oportunidades:\n" + indent_for_llm(truncate_for_llm(ran.ranDoresOportunidadesSugeridas, dores_max))
        )
    if ran.ranObservacoesSugeridas:
        linhas.append(
            "  Observações sugeridas:\n" + indent_for_llm(truncate_for_llm(ran.ranObservacoesSugeridas, observacoes_max))
        )
    if ran.ranProximosPassosSugeridos:
        linhas.append(
            "  Próximos passos:\n" + indent_for_llm(truncate_for_llm(ran.ranProximosPassosSugeridos, proximos_max))
        )
    if ran.ranTranscricao:
        linhas.append(
            "  Transcrição (trecho):\n" + indent_for_llm(truncate_for_llm(ran.ranTranscricao, transcricao_max))
        )
    if ran.ranRespostaJson and isinstance(ran.ranRespostaJson, dict):
        try:
            js = json.dumps(ran.ranRespostaJson, ensure_ascii=False, indent=2)
            linhas.append("  JSON resposta IA (referência):\n" + indent_for_llm(truncate_for_llm(js, json_max)))
        except (TypeError, ValueError):
            pass
    return "\n".join(linhas)


def build_reunioes_anteriores_resumo_para_analise(prior_runs: list[ReuniaoAnalise]) -> str:
    """
    Texto compacto das reuniões já registradas na mesma oportunidade, para contextualizar a reunião atual na IA.
    Ordem da lista = ordem cronológica (mais antiga primeiro).
    """
    if not prior_runs:
        return ""
    parts: list[str] = []
    n = len(prior_runs)
    for idx, ran in enumerate(prior_runs):
        header = (
            f"--- Reunião anterior {idx + 1} de {n} (ranId={ran.ranId}, registro={ran.ranDataCriacao}, "
            f"status={ran.ranStatus}) ---"
        )
        chunks: list[str] = [header]
        if ran.ranResumo:
            chunks.append(f"Resumo IA:\n{indent_for_llm(truncate_for_llm(ran.ranResumo, 2200))}")
        if ran.ranDoresOportunidadesSugeridas:
            chunks.append(
                "Dores e oportunidades (IA):\n"
                + indent_for_llm(truncate_for_llm(ran.ranDoresOportunidadesSugeridas, 1800))
            )
        if ran.ranProximosPassosSugeridos:
            chunks.append(
                "Próximos passos (IA):\n" + indent_for_llm(truncate_for_llm(ran.ranProximosPassosSugeridos, 1200))
            )
        if ran.ranObservacoesSugeridas:
            chunks.append(
                "Observações sugeridas (IA):\n" + indent_for_llm(truncate_for_llm(ran.ranObservacoesSugeridas, 1200))
            )
        if ran.ranTranscricao:
            chunks.append(
                "Trecho da transcrição:\n" + indent_for_llm(truncate_for_llm(ran.ranTranscricao, 1400))
            )
        parts.append("\n".join(chunks))
    out = "\n\n".join(parts)
    if len(out) > PRIOR_REUNIOES_ANALISE_MAX_CHARS:
        return out[: PRIOR_REUNIOES_ANALISE_MAX_CHARS - 3] + "..."
    return out


def caps_por_num_reunioes_escopo(n: int) -> dict[str, int]:
    """Limites por análise quando há várias reuniões no contexto de escopo (peso mais equilibrado)."""
    per = max(n, 1)
    return {
        "transcricao_max": min(5500, max(2500, 12000 // per)),
        "resumo_max": min(8000, max(2000, 16000 // per)),
        "feedback_ia_max": min(4000, max(1200, 8000 // per)),
        "dores_max": min(4000, max(1200, 8000 // per)),
        "observacoes_max": min(4000, max(1000, 6000 // per)),
        "proximos_max": min(2000, max(800, 4000 // per)),
        "json_max": min(6000, max(1500, 12000 // per)),
    }
