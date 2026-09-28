from typing import Annotated

from pydantic import Field

from mcp.server.mcpserver import Context

from ...schemas.oportunidade_historico import OportunidadeHistoricoCreate
from ...services import oportunidade_historico_service
from ..ferramenta import executar_ferramenta
from ..serializacao import carregar_autores, historico_item
from ..servidor import mcp
from ._comum import limitar_pagina, obter_oportunidade_ativa, prefixar


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


@mcp.tool()
def registrar_interacao(
    ctx: Context,
    oportunidade_id: int,
    conteudo: Annotated[str, Field(min_length=1, max_length=10000)],
) -> dict:
    """Registra uma anotação no histórico da oportunidade (resumo de reunião,
    ligação, e-mail, próximo passo) e atualiza a data do último contato para hoje.
    A anotação fica marcada como feita via MCP."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "registrar_interacao", escrita=True, argumentos=argumentos, opo_id=oportunidade_id) as s:
        obter_oportunidade_ativa(s, oportunidade_id)
        criado = oportunidade_historico_service.create_historico(
            s.db,
            oportunidade_id,
            OportunidadeHistoricoCreate(ophConteudo=prefixar(s, conteudo)),
            company_id=s.empId,
            usu_id=s.usuResponsavelPadraoId,
        )
        return historico_item(criado, carregar_autores(s.db, [criado]))
