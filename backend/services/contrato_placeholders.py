from __future__ import annotations

import html
import re
from typing import Any


_PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")


def render_placeholders(text: str, values: dict[str, Any]) -> str:
    """
    Substitui placeholders {{chave}} por valores do contrato.

    Regras:
    - placeholders desconhecidos permanecem como estão (evita apagar tokens por engano)
    - valores são HTML-escaped para reduzir risco em link público
    - valores None viram string vazia
    """

    # Escapamos o texto inteiro antes de substituir, para garantir que conteúdo
    # digitado pelo usuário não injete HTML no snapshot final.
    safe_text = html.escape(text)

    def _repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            return match.group(0)
        raw = values.get(key)
        if raw is None:
            return ""
        # Valores sempre escapados (já que podem vir de campos do contrato).
        return html.escape(str(raw))

    return _PLACEHOLDER_RE.sub(_repl, safe_text)

