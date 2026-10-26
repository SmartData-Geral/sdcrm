from typing import Annotated, Literal

from pydantic import Field
from sqlalchemy import func, select

from mcp.server.mcpserver import Context

from ...exceptions import BadRequestError
from ...models.etapa_kanban import EtapaKanban
from ...models.oportunidade import Oportunidade
from ...schemas.oportunidade import (
    OportunidadeLeadScoreRequest,
    OportunidadeMoverEtapaRequest,
    OportunidadeTemperaturaRequest,
)
from ...services import oportunidade_service
from ..ferramenta import executar_ferramenta
from ..servidor import mcp
from ._comum import obter_oportunidade_ativa, responder_oportunidade


@mcp.tool()
def resumo_funil(ctx: Context, pipeline: str | None = None) -> dict:
    """Foto do kanban: quantidade e valor das oportunidades ativas (sem fechamento)
    em cada etapa de um pipeline, na ordem do funil. Sem `pipeline`, usa o primeiro."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "resumo_funil", escrita=False, argumentos=argumentos) as s:
        db, emp = s.db, s.empId
        ativa = (EtapaKanban.etkEmpId == emp, EtapaKanban.etkAtivo.is_(True))
        if not pipeline:
            pipeline = db.scalar(
                select(EtapaKanban.etkPipeline).where(*ativa).order_by(EtapaKanban.etkOrdem, EtapaKanban.etkId).limit(1)
            )
        if not pipeline:
            return {"pipeline": None, "etapas": [], "total_quantidade": 0, "total_valor": 0.0}

        etapas = db.scalars(
            select(EtapaKanban)
            .where(*ativa, EtapaKanban.etkPipeline == pipeline)
            .order_by(EtapaKanban.etkOrdem, EtapaKanban.etkId)
        ).all()
        linhas = []
        if etapas:
            linhas = db.execute(
                select(
                    Oportunidade.opoEtkId,
                    func.count(Oportunidade.opoId),
                    func.coalesce(func.sum(Oportunidade.opoValorOportunidade), 0),
                )
                .where(
                    Oportunidade.opoEmpId == emp,
                    Oportunidade.opoAtivo.is_(True),
                    Oportunidade.opoStatusFechamento.is_(None),
                    Oportunidade.opoEtkId.in_([e.etkId for e in etapas]),
                )
                .group_by(Oportunidade.opoEtkId)
            ).all()
        por_etapa = {etk: (int(qtd), float(valor)) for etk, qtd, valor in linhas}
        itens = []
        for e in etapas:
            qtd, valor = por_etapa.get(e.etkId, (0, 0.0))
            itens.append({"etapa": {"id": e.etkId, "nome": e.etkNome}, "quantidade": qtd, "valor_total": valor})
        return {
            "pipeline": pipeline,
            "etapas": itens,
            "total_quantidade": sum(i["quantidade"] for i in itens),
            "total_valor": round(sum(i["valor_total"] for i in itens), 2),
        }


@mcp.tool()
def mover_etapa(ctx: Context, oportunidade_id: int, etapa_id: int) -> dict:
    """Move a oportunidade para outra etapa do mesmo pipeline. Registra no histórico
    e dispara o webhook deal.stage_changed. Use listar_cadastros para os IDs de etapa."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "mover_etapa", escrita=True, argumentos=argumentos, opo_id=oportunidade_id) as s:
        opo = obter_oportunidade_ativa(s, oportunidade_id)
        oportunidade_service.mover_etapa(s.db, oportunidade_id, OportunidadeMoverEtapaRequest(opoEtkId=etapa_id), s.empId, origem="mcp")
        return responder_oportunidade(s, opo)


@mcp.tool()
def atualizar_qualificacao(
    ctx: Context,
    oportunidade_id: int,
    temperatura: Literal["quente", "morno", "frio"] | None = None,
    lead_score: Annotated[int | None, Field(ge=0, le=10)] = None,
    reuniao_confirmada: bool | None = None,
    proposta_enviada: bool | None = None,
) -> dict:
    """Atualiza a qualificação da oportunidade: temperatura, lead score (0 a 10),
    reunião confirmada e proposta enviada. Informe ao menos um campo."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "atualizar_qualificacao", escrita=True, argumentos=argumentos, opo_id=oportunidade_id) as s:
        if temperatura is None and lead_score is None and reuniao_confirmada is None and proposta_enviada is None:
            raise BadRequestError("Informe ao menos um campo de qualificação.")
        opo = obter_oportunidade_ativa(s, oportunidade_id)
        db, emp = s.db, s.empId
        if temperatura is not None:
            oportunidade_service.set_temperatura(db, oportunidade_id, OportunidadeTemperaturaRequest(opoTemperatura=temperatura), emp)
        if lead_score is not None:
            oportunidade_service.set_lead_score(db, oportunidade_id, OportunidadeLeadScoreRequest(opoLeadScore=lead_score), emp)
        if reuniao_confirmada is not None:
            oportunidade_service.set_reuniao_confirmada(db, oportunidade_id, reuniao_confirmada, emp)
        if proposta_enviada is not None:
            oportunidade_service.set_proposta_enviada(db, oportunidade_id, proposta_enviada, emp)
        return responder_oportunidade(s, opo)
