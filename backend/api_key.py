"""
Autenticação por chave de API para a superfície externa (/api/v1/*).

Paralelo a backend/auth.py, que cuida do JWT do frontend. As duas nunca se encontram:
uma rota declara `ApiKeyDep` ou declara `CurrentUserDep` + `CompanyIdDep`, nunca ambos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Optional

from fastapi import Depends, Header, Request

from .database import get_db
from .dependencies import DbSessionDep
from .exceptions import AuthenticationError, AuthorizationError
from .services import integracao_chave_service, integracao_log_service


def _ip_do_request(request: Request) -> str | None:
    encaminhado = request.headers.get("x-forwarded-for")
    if encaminhado:
        return encaminhado.split(",")[0].strip()[:64]
    return request.client.host if request.client else None


@dataclass(frozen=True)
class ApiKeyContext:
    """Identidade resolvida de uma integração. A empresa vem daqui, nunca do header."""

    ichId: int
    empId: int
    nome: str
    escopos: frozenset[str]
    usuResponsavelPadraoId: int | None

    def tem_escopo(self, escopo: str) -> bool:
        return escopo in self.escopos


def get_api_key_context(
    request: Request,
    db: DbSessionDep,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    x_company_id: Optional[str] = Header(default=None, alias="X-Company-Id"),
) -> ApiKeyContext:
    chave = integracao_chave_service.autenticar(db, x_api_key)
    if chave is None:
        # O 401 nunca chega ao service, entao o log dele acontece aqui.
        integracao_log_service.registrar(
            db,
            rota=request.url.path[:120],
            metodo=request.method,
            status_http=401,
            resultado="unauthorized",
            prefixo_informado=integracao_chave_service.prefixo_para_log(x_api_key),
            ip=_ip_do_request(request),
            user_agent=request.headers.get("user-agent"),
        )
        # Mensagem unica de proposito: header ausente, malformado, inexistente, com
        # segredo errado, revogado, inativo ou expirado respondem todos igual.
        raise AuthenticationError("Chave de API invalida ou revogada")

    # O tenant é o da chave. Se alguém mandar X-Company-Id divergente, ignoramos e
    # deixamos o rastro -- seria uma tentativa de saltar de empresa.
    if x_company_id is not None and str(x_company_id).strip() not in ("", str(chave.ichEmpId)):
        request.state.company_id_divergente = str(x_company_id).strip()

    integracao_chave_service.registrar_uso(db, chave)
    db.commit()

    ctx = ApiKeyContext(
        ichId=chave.ichId,
        empId=chave.ichEmpId,
        nome=chave.ichNome,
        escopos=frozenset(e.strip() for e in (chave.ichEscopos or "").split(",") if e.strip()),
        usuResponsavelPadraoId=chave.ichUsuResponsavelPadraoId,
    )
    request.state.api_key_context = ctx
    return ctx


ApiKeyDep = Annotated[ApiKeyContext, Depends(get_api_key_context)]


def exigir_escopo(ctx: ApiKeyContext, escopo: str) -> None:
    if not ctx.tem_escopo(escopo):
        raise AuthorizationError(f"A chave de integração não possui o escopo {escopo}")
