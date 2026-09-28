from datetime import date
from typing import Annotated, Literal

from pydantic import Field

from mcp.server.mcpserver import Context

from ...schemas.crm_dashboard import CrmDashboardFiltroParams, CrmDashboardOportunidadesFiltroParams
from ...services import crm_dashboard_service, crm_meta_mensal_service
from ..ferramenta import executar_ferramenta
from ..servidor import mcp

StatusPainel = Literal["todas", "ganhas", "perdidas", "ativas"]
Metrica = Literal["recebidas", "ganhas", "perdidas", "ativas", "mrrIncremental", "valorProjeto"]
_CAMPOS_INDICADORES = ("cards", "temMeta", "resumoMetas", "motivosPerda", "rankings")


@mcp.tool()
def obter_indicadores(
    ctx: Context,
    data_inicial: date | None = None,
    data_final: date | None = None,
    responsavel_id: int | None = None,
    status: StatusPainel = "todas",
    incluir_serie_mensal: bool = False,
    anos_serie: list[int] | None = None,
) -> dict:
    """Indicadores comerciais do painel do CRM: cards (recebidas, ganhas, perdidas,
    MRR, valor de projeto, forecast, conversão), meta x realizado, motivos de perda e
    rankings. A série mensal só vem com `incluir_serie_mensal=true` (use `anos_serie`
    para anos-calendário completos)."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "obter_indicadores", escrita=False, argumentos=argumentos) as s:
        filtros = CrmDashboardFiltroParams(
            data_inicial=data_inicial,
            data_final=data_final,
            responsavel_id=responsavel_id,
            status=status,
            serie_anos=anos_serie if incluir_serie_mensal else None,
        )
        dados = crm_dashboard_service.get_dashboard(s.db, s.empId, filtros).model_dump(mode="json")
        resposta = {campo: dados.get(campo) for campo in _CAMPOS_INDICADORES}
        if incluir_serie_mensal:
            resposta["serieMensal"] = dados.get("serieMensal", [])
        return resposta


@mcp.tool()
def detalhar_indicador(
    ctx: Context,
    metrica: Metrica | None = None,
    periodo: Annotated[str | None, Field(pattern=r"^\d{4}-\d{2}$")] = None,
    fonte: str | None = None,
    solucao: str | None = None,
    motivo_perda: str | None = None,
    data_inicial: date | None = None,
    data_final: date | None = None,
    responsavel_id: int | None = None,
) -> dict:
    """Lista as oportunidades por trás de um número do painel (drill-down), filtrando
    por métrica, mês (`periodo` YYYY-MM), origem, solução ou motivo de perda. Devolve
    no máximo 100 itens; `truncado=true` indica que há mais."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "detalhar_indicador", escrita=False, argumentos=argumentos) as s:
        filtros = CrmDashboardOportunidadesFiltroParams(
            data_inicial=data_inicial,
            data_final=data_final,
            responsavel_id=responsavel_id,
            fonte=fonte,
            solucao=solucao,
            motivo_perda=motivo_perda,
            periodo=periodo,
            metrica=metrica,
        )
        dados = crm_dashboard_service.list_dashboard_oportunidades(s.db, s.empId, filtros).model_dump(mode="json")
        dados["truncado"] = dados.get("total", 0) > len(dados.get("itens", []))
        return dados


@mcp.tool()
def obter_metas(ctx: Context, ano: Annotated[int, Field(ge=2000, le=2100)]) -> dict:
    """Metas mensais do CRM e realizado de cada mês de um ano."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "obter_metas", escrita=False, argumentos=argumentos) as s:
        return crm_meta_mensal_service.list_resumo_ano(s.db, company_id=s.empId, ano=ano).model_dump(mode="json")
