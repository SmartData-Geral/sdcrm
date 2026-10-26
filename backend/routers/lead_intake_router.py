"""
Superficie externa versionada: /api/v1/*.

Excecao deliberada a convencao /api/<recurso-pt> do docs/API_GUIDELINES.md. Este e um
contrato publico consumido por terceiros (Zapier hoje; Meta Lead Ads e formulario do
site depois), entao versao explicita e nomes em ingles sao o certo aqui. As rotas
internas do CRM seguem em portugues e sem versao.

Autenticacao por X-API-Key. Estas rotas NAO usam CompanyIdDep: a empresa vem da chave.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Request, Response, status

from ..api_key import ApiKeyDep, exigir_escopo
from ..core.links import url_da_oportunidade as _url_da_oportunidade
from ..dependencies import DbSessionDep
from ..exceptions import ConflictError
from ..schemas.lead_integracao import (
    LeadIntakeRequest,
    LeadIntakeResponse,
    PingResponse,
    RastreioMetaRequest,
    RastreioMetaResponse,
)
from ..services import integracao_log_service, lead_intake_service
from ..services.meta_ads import rastreio as rastreio_meta

router = APIRouter(prefix="/api/v1", tags=["integracao-externa"])

ROTA_LEADS = "/api/v1/leads"
ROTA_RASTREIO_META = "/api/v1/leads/rastreio-meta"


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
        _logar(status.HTTP_500_INTERNAL_SERVER_ERROR, "error", erro={"tipo": type(exc).__name__, "detalhe": "Erro interno ao processar a requisição."})
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


@router.post("/leads/rastreio-meta", response_model=RastreioMetaResponse)
def rastrear_leads_meta(
    payload: RastreioMetaRequest,
    request: Request,
    db: DbSessionDep,
    ctx: ApiKeyDep,
) -> RastreioMetaResponse:
    """
    Carga retroativa: so atualiza leads existentes com os ids da Meta; nunca cria.

    O chamador deve enviar as linhas da planilha inteira em ordem crescente de created_time
    (lotes em sequência); a regra 'a mais antiga vence' vale entre lotes só nessa condição.
    """
    exigir_escopo(ctx, "leads:write")
    inicio = time.perf_counter()

    def _logar(status_http: int, resultado: str, erro=None) -> None:
        # Sem payload: as linhas trazem telefone e e-mail, e o total basta para depurar.
        integracao_log_service.registrar(
            db,
            rota=ROTA_RASTREIO_META,
            metodo="POST",
            status_http=status_http,
            resultado=resultado,
            emp_id=ctx.empId,
            ich_id=ctx.ichId,
            origem_sistema="meta_ads",
            payload={"itens": len(payload.itens)},
            erro=erro,
            ip=_ip(request),
            user_agent=request.headers.get("user-agent"),
            duracao_ms=int((time.perf_counter() - inicio) * 1000),
        )

    try:
        resposta = rastreio_meta.aplicar_rastreio_retroativo(db, ctx.empId, payload.itens)
    except Exception as exc:
        db.rollback()
        _logar(status.HTTP_500_INTERNAL_SERVER_ERROR, "error", erro={"tipo": type(exc).__name__, "detalhe": "Erro interno ao processar a requisição."})
        raise
    _logar(status.HTTP_200_OK, "rastreio")
    return resposta
