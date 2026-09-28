from sqlalchemy import func, select

from mcp.server.mcpserver import Context

from ...models.etapa_kanban import EtapaKanban
from ...models.oportunidade import Oportunidade
from ..ferramenta import executar_ferramenta
from ..servidor import mcp


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
