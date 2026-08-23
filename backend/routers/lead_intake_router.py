"""
Superficie externa versionada: /api/v1/*.

Excecao deliberada a convencao /api/<recurso-pt> do docs/API_GUIDELINES.md. Este e um
contrato publico consumido por terceiros (Zapier hoje; Meta Lead Ads e formulario do
site depois), entao versao explicita e nomes em ingles sao o certo aqui. As rotas
internas do CRM seguem em portugues e sem versao.

Autenticacao por X-API-Key. Estas rotas NAO usam CompanyIdDep: a empresa vem da chave.
"""

from __future__ import annotations

import os
import time
from urllib.parse import urlparse

from fastapi import APIRouter, Request, Response, status

from ..api_key import ApiKeyDep, exigir_escopo
from ..dependencies import DbSessionDep
from ..exceptions import ConflictError
from ..schemas.lead_integracao import LeadIntakeRequest, LeadIntakeResponse, PingResponse
from ..services import integracao_log_service, lead_intake_service

router = APIRouter(prefix="/api/v1", tags=["integracao-externa"])

ROTA_LEADS = "/api/v1/leads"


def _url_da_oportunidade(opo_id: int) -> str | None:
    """Mesma fonte que proposta_service usa para montar links publicos."""
    base = (os.getenv("VITE_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if not base:
        return None
    parsed = urlparse(base)
    if not parsed.scheme:
        return None
    return base + "/oportunidades/" + str(opo_id)


def _ip(request: Request) -> str | None:
    encaminhado = request.headers.get("x-forwarded-for")
    if encaminhado:
        return encaminhado.split(",")[0].strip()[:64]
    return request.client.host if request.client else None


@router.get("/ping", response_model=PingResponse)
def ping(ctx: ApiKeyDep) -> PingResponse:
    """Smoke test da chave. Existe para tornar a configuracao do Zapier depuravel."""
    return PingResponse(
        ok=True,
        company_id=ctx.empId,
        integration=ctx.nome,
        scopes=sorted(ctx.escopos),
    )


@router.post("/leads", response_model=LeadIntakeResponse, status_code=status.HTTP_201_CREATED)
def receber_lead(
    payload: LeadIntakeRequest,
    request: Request,
    response: Response,
    db: DbSessionDep,
    ctx: ApiKeyDep,
) -> LeadIntakeResponse:
    exigir_escopo(ctx, "leads:write")
    inicio = time.perf_counter()

    dados_brutos = payload.model_dump()

    def _logar(status_http: int, resultado: str, opo_id: int | None = None, erro=None) -> None:
        integracao_log_service.registrar(
            db,
            rota=ROTA_LEADS,
            metodo="POST",
            status_http=status_http,
            resultado=resultado,
            emp_id=ctx.empId,
            ich_id=ctx.ichId,
            prefixo_informado=None,
            origem_sistema=payload.source,
            external_id=payload.external_id,
            opo_id=opo_id,
            payload=dados_brutos,
            erro=erro,
            ip=_ip(request),
            user_agent=request.headers.get("user-agent"),
            duracao_ms=int((time.perf_counter() - inicio) * 1000),
        )

    try:
        resultado = lead_intake_service.processar_lead(
            db, emp_id=ctx.empId, ich_id=ctx.ichId, payload=payload
        )
    except ConflictError:
        _logar(status.HTTP_409_CONFLICT, "conflict")
        raise
    except Exception as exc:
        _logar(status.HTTP_500_INTERNAL_SERVER_ERROR, "error", erro={"detalhe": str(exc)[:500]})
        raise

    status_http = (
        status.HTTP_200_OK if resultado.status == "updated" else status.HTTP_201_CREATED
    )
    response.status_code = status_http

    # "novo_ciclo" distingue, no log, a criacao que veio de um contato com historico
    # anterior encerrado -- e o caso da decisao de conflito.
    marcador = "novo_ciclo" if resultado.ciclo_anterior_id else resultado.status
    _logar(status_http, marcador, opo_id=resultado.opo_id)

    anterior = resultado.ciclo_anterior_id
    return LeadIntakeResponse(
        lead_id="ld_" + str(resultado.opo_id),
        status=resultado.status,
        opportunity_id=resultado.opo_id,
        deduped_by=resultado.deduped_by,
        previous_cycle_lead_id=("ld_" + str(anterior)) if anterior else None,
        url=_url_da_oportunidade(resultado.opo_id),
    )
