from datetime import date
from typing import Literal

from mcp.server.mcpserver import Context

from ...services.meta_ads import alertas, indicadores, resumo
from ..ferramenta import executar_ferramenta
from ..servidor import mcp

StatusAlerta = Literal["aberto", "ciente", "resolvido"]


def _sem_filhos(linha) -> dict:
    return linha.model_dump(mode="json", exclude={"filhos"})


def _anuncios(linhas) -> list:
    achatados = []
    for linha in linhas:
        if linha.nivel == "anuncio":
            achatados.append(linha)
        achatados.extend(_anuncios(linha.filhos))
    return achatados


def _alerta(a) -> dict:
    base = {
        "id": a.malId,
        "tipo": a.malTipo,
        "status": a.malStatus,
        "primeiroEm": a.malPrimeiroEm.isoformat(),
        "ultimoEm": a.malUltimoEm.isoformat(),
    }
    if a.malTipo == "sem_contato":
        # A mensagem e os dados trazem nome e telefone do lead: só o id e as horas saem daqui.
        _, _, numero = a.malChave.partition(":")
        base["oportunidadeId"] = int(numero) if numero.isdigit() else None
        base["horas"] = (a.malDados or {}).get("horas")
    else:
        base["mensagem"] = a.malMensagem
        base["alvo"] = a.alvoNome
    return base


@mcp.tool()
def resumo_campanhas(
    ctx: Context,
    data_inicial: date | None = None,
    data_final: date | None = None,
) -> dict:
    """Painel de campanhas Meta Ads no período: a linha de total e uma linha por campanha,
    com investimento, impressões, cliques, leads (Meta e CRM), MQLs, oportunidades, vendas,
    MRR e custos (CPL, custo por MQL e por oportunidade, CAC, retorno). Não traz os
    conjuntos e anúncios (use `funil_por_criativo`) nem dados de pessoas."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "resumo_campanhas", escrita=False, argumentos=argumentos) as s:
        painel = indicadores.painel(s.db, s.empId, indicadores.FiltroPainel(data_inicial, data_final))
        return {
            "total": _sem_filhos(painel.total),
            "campanhas": [_sem_filhos(c) for c in painel.campanhas],
            "cobertura": painel.cobertura,
        }


@mcp.tool()
def funil_por_criativo(
    ctx: Context,
    data_inicial: date | None = None,
    data_final: date | None = None,
    campanha_id: int | None = None,
) -> dict:
    """Funil por criativo (anúncio) Meta Ads no período: para cada anúncio, leads, MQLs,
    oportunidades, contratos (vendas), MRR, investimento e custos (por lead, MQL e
    oportunidade, CAC). Ordenado por oportunidades, do maior para o menor. `campanha_id`
    restringe a uma campanha. Responde, por exemplo, qual criativo trouxe mais oportunidades."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "funil_por_criativo", escrita=False, argumentos=argumentos) as s:
        painel = indicadores.painel(s.db, s.empId, indicadores.FiltroPainel(data_inicial, data_final))
        linhas = _anuncios(painel.campanhas)
        if campanha_id is not None:
            linhas = [a for a in linhas if a.mcgId == campanha_id]
        linhas.sort(key=lambda a: a.oportunidades, reverse=True)
        return {"anuncios": [_sem_filhos(a) for a in linhas]}


@mcp.tool()
def alertas_campanhas(ctx: Context, status: StatusAlerta = "aberto") -> dict:
    """Alertas do monitoramento de campanhas Meta Ads (CPL alto, gasto sem lead, frequência,
    queda de CTR, anúncio reprovado, conta com problema, campanha parada, lead sem contato)
    no status pedido. Alertas de lead sem contato trazem só o id da oportunidade e as horas
    de espera, sem nome nem telefone."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "alertas_campanhas", escrita=False, argumentos=argumentos) as s:
        return {"status": status, "alertas": [_alerta(a) for a in alertas.listar(s.db, s.empId, status)]}


@mcp.tool()
def resumo_diario(ctx: Context, data: date | None = None) -> dict:
    """Resumo diário de campanhas Meta Ads já gerado: período analisado, dados agregados
    (ranking de anúncios, variações, alertas abertos) e a leitura em texto feita por IA.
    Sem `data`, devolve o mais recente. Dá erro se não houver resumo para a data."""
    argumentos = dict(locals())
    with executar_ferramenta(ctx, "resumo_diario", escrita=False, argumentos=argumentos) as s:
        r = resumo.obter(s.db, s.empId, data)
        return {
            "data": r.mrsData.isoformat(),
            "inicio": r.mrsInicio.isoformat(),
            "fim": r.mrsFim.isoformat(),
            "dados": r.mrsDados,
            "leitura": r.mrsLeitura,
            "aviso": r.mrsAviso,
            "geradoEm": r.mrsGeradoEm.isoformat(),
        }
