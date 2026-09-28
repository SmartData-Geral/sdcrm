from datetime import date
from typing import Annotated, Literal

from pydantic import Field

from mcp.server.mcpserver import Context

from ...models.oportunidade import Oportunidade
from ...services import oportunidade_historico_service, oportunidade_service
from ..ferramenta import executar_ferramenta
from ..serializacao import carregar_autores, carregar_nomes, historico_item, oportunidade_completa, resumo_oportunidade, status_de
from ..servidor import mcp
from ._comum import limitar_pagina, obter_oportunidade_ativa

Status = Literal["ativo", "ganho", "perdido", "stand-by"]
Temperatura = Literal["quente", "morno", "frio"]


@mcp.tool()
def buscar_oportunidades(
    ctx: Context,
    texto: str | None = None,
    status: Status | None = None,
    etapa_id: int | None = None,
    pipeline: str | None = None,
    responsavel_id: int | None = None,
    produto_id: int | None = None,
    temperatura: Temperatura | None = None,
    ultimo_contato_de: date | None = None,
    ultimo_contato_ate: date | None = None,
    pagina: Annotated[int, Field(ge=1)] = 1,
    por_pagina: Annotated[int, Field(ge=1)] = 20,
) -> dict:
    """Busca oportunidades/leads ativos no CRM, das mais novas para as mais antigas.
    `texto` procura em título, nome do contato, empresa e e-mail. Para achar leads
    parados, use `status="ativo"` com `ultimo_contato_ate`. Máximo de 50 por página."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "buscar_oportunidades", escrita=False, argumentos=argumentos) as s:
        pagina, por_pagina = limitar_pagina(pagina, por_pagina)
        resultado = oportunidade_service.list_oportunidades(
            s.db,
            company_id=s.empId,
            busca=texto,
            pipeline=pipeline,
            status="ativos",
            etapa_id=etapa_id,
            responsavel_id=responsavel_id,
            pro_id=produto_id,
            data_ultimo_contato_inicio=ultimo_contato_de,
            data_ultimo_contato_fim=ultimo_contato_ate,
            status_fechamento=status,
            temperatura=temperatura,
            page=pagina,
            page_size=por_pagina,
        )
        nomes = carregar_nomes(s.db, resultado.items)
        return {
            "itens": [resumo_oportunidade(o, nomes) for o in resultado.items],
            "total": resultado.total,
            "pagina": pagina,
            "por_pagina": por_pagina,
        }


@mcp.tool()
def obter_oportunidade(ctx: Context, oportunidade_id: int) -> dict:
    """Detalhe completo de uma oportunidade: dados do contato, etapa, responsável,
    qualificação, valores, fechamento, os 10 registros mais recentes do histórico,
    o ciclo anterior do mesmo contato (se houver) e o link para abrir no CRM."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "obter_oportunidade", escrita=False, argumentos=argumentos, opo_id=oportunidade_id) as s:
        opo = obter_oportunidade_ativa(s, oportunidade_id)
        dados = oportunidade_completa(opo, carregar_nomes(s.db, [opo]))
        historicos = oportunidade_historico_service.list_historicos(
            s.db, oportunidade_id, company_id=s.empId, page=1, page_size=10
        ).items
        autores = carregar_autores(s.db, historicos)
        dados["historico_recente"] = [historico_item(h, autores) for h in historicos]
        dados["ciclo_anterior"] = None
        if opo.opoOpoAnteriorId:
            anterior = s.db.get(Oportunidade, opo.opoOpoAnteriorId)
            if anterior is not None and anterior.opoEmpId == s.empId:
                dados["ciclo_anterior"] = {
                    "id": anterior.opoId,
                    "titulo": anterior.opoTitulo,
                    "status": status_de(anterior),
                }
        return dados
