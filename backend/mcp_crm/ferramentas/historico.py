from typing import Annotated

from pydantic import Field

from mcp.server.mcpserver import Context

from ...services import oportunidade_historico_service
from ..ferramenta import executar_ferramenta
from ..serializacao import carregar_autores, historico_item
from ..servidor import mcp
from ._comum import limitar_pagina, obter_oportunidade_ativa


@mcp.tool()
def listar_historico(
    ctx: Context,
    oportunidade_id: int,
    pagina: Annotated[int, Field(ge=1)] = 1,
    por_pagina: Annotated[int, Field(ge=1)] = 20,
) -> dict:
    """Histórico completo de interações e mudanças de uma oportunidade, do mais
    recente para o mais antigo. Máximo de 50 por página."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "listar_historico", escrita=False, argumentos=argumentos, opo_id=oportunidade_id) as s:
        pagina, por_pagina = limitar_pagina(pagina, por_pagina)
        obter_oportunidade_ativa(s, oportunidade_id)
        resultado = oportunidade_historico_service.list_historicos(
            s.db, oportunidade_id, company_id=s.empId, page=pagina, page_size=por_pagina
        )
        autores = carregar_autores(s.db, resultado.items)
        return {
            "itens": [historico_item(h, autores) for h in resultado.items],
            "total": resultado.total,
            "pagina": pagina,
            "por_pagina": por_pagina,
        }
