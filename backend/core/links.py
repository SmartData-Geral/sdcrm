"""Links públicos do frontend usados em respostas de integração."""

from __future__ import annotations

import os
from urllib.parse import urlparse


def url_da_oportunidade(opo_id: int) -> str | None:
    """Mesma fonte que proposta_service usa para montar links publicos."""
    base = (os.getenv("VITE_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if not base:
        return None
    parsed = urlparse(base)
    if not parsed.scheme:
        return None
    return base + "/oportunidades/" + str(opo_id)
