from datetime import date
from typing import Annotated, Literal

from pydantic import Field

from mcp.server.mcpserver import Context

from ...exceptions import BadRequestError
from ...schemas.oportunidade import (
    OportunidadeGanharRequest,
    OportunidadeStandByRequest,
    OportunidadeUpdate,
)
from ...schemas.oportunidade_historico import OportunidadeHistoricoCreate
from ...services import oportunidade_historico_service, oportunidade_service
from ..ferramenta import executar_ferramenta
from ..serializacao import status_de
from ..servidor import mcp
from ._comum import hoje, obter_oportunidade_ativa, prefixar, responder_oportunidade, validar_motivo

_TIPO_PARA_RECORRENCIA = {"recorrencia": 0, "projeto": 1}


def _sem_alteracao(s, opo, aviso: str) -> dict:
    return {**responder_oportunidade(s, opo), "aviso": aviso}


@mcp.tool()
def marcar_ganho(
    ctx: Context,
    oportunidade_id: int,
    data_fechamento: date,
    tipo: Literal["recorrencia", "projeto"],
    valor_fechado: Annotated[float, Field(gt=0)],
) -> dict:
    """Marca a oportunidade como GANHA. Altera MRR e indicadores: confirme com o
    usuário data, tipo (recorrencia = receita mensal; projeto = receita única) e valor
    antes de chamar."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "marcar_ganho", escrita=True, argumentos=argumentos, opo_id=oportunidade_id) as s:
        opo = obter_oportunidade_ativa(s, oportunidade_id)
        if status_de(opo) == "ganho":
            return _sem_alteracao(s, opo, "A oportunidade já está marcada como ganha.")
        dados = OportunidadeGanharRequest(
            opoDataFechamento=data_fechamento,
            opoFechadoRecorrencia=_TIPO_PARA_RECORRENCIA[tipo],
            opoValorFechado=valor_fechado,
        )
        # O service devolve OportunidadeResponse (sem opoOrigemSistema/opoUtmSource/
        # opoUtmCampaign): usamos o efeito colateral e respondemos com a instância ORM
        # `opo`, que o service já commitou/atualizou na mesma sessão.
        oportunidade_service.set_oportunidade_status_fechamento(
            s.db, oportunidade_id, "ganho", s.empId, data=dados
        )
        return responder_oportunidade(s, opo)


@mcp.tool()
def marcar_perdido(
    ctx: Context,
    oportunidade_id: int,
    motivo_id: int,
    observacao: Annotated[str | None, Field(max_length=10000)] = None,
) -> dict:
    """Marca a oportunidade como PERDIDA com um motivo de perda (IDs em
    listar_cadastros). A observação opcional vai para o histórico. Altera indicadores:
    confirme com o usuário antes de chamar."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "marcar_perdido", escrita=True, argumentos=argumentos, opo_id=oportunidade_id) as s:
        opo = obter_oportunidade_ativa(s, oportunidade_id)
        validar_motivo(s, motivo_id)
        if status_de(opo) == "perdido":
            return _sem_alteracao(s, opo, "A oportunidade já está marcada como perdida.")
        # Cada service faz commit próprio: toda validação acontece antes desta linha.
        oportunidade_service.update_oportunidade(s.db, oportunidade_id, OportunidadeUpdate(opoMcaId=motivo_id), s.empId)
        oportunidade_service.set_oportunidade_status_fechamento(s.db, oportunidade_id, "perdido", s.empId)
        if observacao and observacao.strip():
            oportunidade_historico_service.create_historico(
                s.db,
                oportunidade_id,
                OportunidadeHistoricoCreate(ophConteudo=prefixar(s, observacao)),
                company_id=s.empId,
                usu_id=s.usuResponsavelPadraoId,
            )
        return responder_oportunidade(s, opo)


@mcp.tool()
def colocar_stand_by(ctx: Context, oportunidade_id: int, data_retorno: date) -> dict:
    """Coloca a oportunidade em STAND-BY até `data_retorno` (hoje ou depois). Na data,
    ela volta sozinha para o funil. Confirme com o usuário antes de chamar."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "colocar_stand_by", escrita=True, argumentos=argumentos, opo_id=oportunidade_id) as s:
        opo = obter_oportunidade_ativa(s, oportunidade_id)
        if data_retorno < hoje():
            raise BadRequestError("A data de retorno não pode estar no passado.")
        oportunidade_service.set_oportunidade_stand_by(
            s.db, oportunidade_id, OportunidadeStandByRequest(opoDataUltimoContato=data_retorno), s.empId
        )
        return responder_oportunidade(s, opo)


@mcp.tool()
def reativar_oportunidade(ctx: Context, oportunidade_id: int) -> dict:
    """Devolve ao funil (status ativo) uma oportunidade ganha, perdida ou em stand-by,
    limpando os dados de fechamento. Confirme com o usuário antes de chamar."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "reativar_oportunidade", escrita=True, argumentos=argumentos, opo_id=oportunidade_id) as s:
        opo = obter_oportunidade_ativa(s, oportunidade_id)
        if status_de(opo) == "ativo":
            return _sem_alteracao(s, opo, "A oportunidade já está ativa no funil.")
        oportunidade_service.reativar_oportunidade_para_funil(s.db, oportunidade_id, s.empId)
        return responder_oportunidade(s, opo)
