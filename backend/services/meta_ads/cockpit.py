"""Resposta do cockpit de campanhas: monta o painel, o periodo anterior, selos, funil, serie e criativos.

Nenhuma regra de contagem nova: os numeros saem de `indicadores.calcular_painel` e da serie por
intervalo. Sem nome, telefone ou e-mail de lead: a revisao de origem entra so como contagem.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ...exceptions import BadRequestError
from ...schemas.meta_ads import (
    MetaAdsCockpitCriativo,
    MetaAdsCockpitEtapa,
    MetaAdsCockpitMetas,
    MetaAdsCockpitOperacao,
    MetaAdsCockpitPonto,
    MetaAdsCockpitResponse,
    MetaAdsCockpitSelos,
    MetaAdsLinha,
    MetaAdsPainelResponse,
)
from . import cockpit_regras as regras
from .config_monitor import obter_config
from .indicadores import FiltroPainel, calcular_painel, serie_por_intervalo
from .resumo import contar_alertas_abertos


def _sem_filhos(linha: MetaAdsLinha) -> MetaAdsLinha:
    return linha.model_copy(update={"filhos": []})


def _tem_dados(linha: MetaAdsLinha) -> bool:
    return linha.investimento > 0 or linha.leadsMeta > 0 or linha.leadsCrm > 0


def _dividir(a: float, b: float, escala: float = 1) -> float | None:
    return round(a / b * escala, 2) if b else None


def _funil(t: MetaAdsLinha, marcado: str | None) -> list[MetaAdsCockpitEtapa]:
    etapas = [
        ("impressoes", t.impressoes, None, _dividir(t.investimento, t.impressoes, 1000)),
        ("cliques", t.cliques, regras.taxa(t.cliques, t.impressoes), t.cpc),
        ("leads", t.leadsMeta, regras.taxa(t.leadsMeta, t.cliques), t.cpl),
        ("crm", t.leadsCrm, regras.taxa(t.leadsCrm, t.leadsMeta), t.custoLeadCrm),
        ("mql", t.mqls, regras.taxa(t.mqls, t.leadsCrm), t.custoMql),
        ("oportunidade", t.oportunidades, regras.taxa(t.oportunidades, t.mqls), t.custoOportunidade),
        ("contrato", t.vendas, regras.taxa(t.vendas, t.oportunidades), t.cac),
    ]
    return [
        MetaAdsCockpitEtapa(chave=c, quantidade=q, taxa=tx, custo=custo, gargalo=c == marcado)
        for c, q, tx, custo in etapas
    ]


def _serie(db, emp_id, filtro, calculo) -> tuple[str, list[MetaAdsCockpitPonto]]:
    tipo, faixas = regras.intervalos(filtro.data_inicial, filtro.data_final)
    valores = serie_por_intervalo(db, emp_id, filtro, calculo, [(i, f) for i, f, _ in faixas])
    pontos = [
        MetaAdsCockpitPonto(
            inicio=ini, fim=fim, rotulo=rotulo,
            investimento=v["investimento"], impressoes=v["impressoes"], cliques=v["cliques"],
            leadsMeta=v["leadsMeta"], leadsCrm=v["leadsCrm"], mqls=v["mqls"],
            cpl=_dividir(v["investimento"], v["leadsMeta"]),
        )
        for (ini, fim, rotulo), v in zip(faixas, valores)
    ]

    def vazio(p: MetaAdsCockpitPonto) -> bool:
        return not (p.investimento or p.leadsMeta or p.leadsCrm)

    while pontos and vazio(pontos[0]):
        pontos.pop(0)
    while pontos and vazio(pontos[-1]):
        pontos.pop()
    return tipo, pontos


def _criativos(painel: MetaAdsPainelResponse, metas: regras.Metas) -> list[MetaAdsCockpitCriativo]:
    """Anuncios da arvore do painel com investimento no periodo, do maior gasto para o menor."""
    itens: list[MetaAdsCockpitCriativo] = []
    for campanha in painel.campanhas:
        for conjunto in campanha.filhos:
            for a in conjunto.filhos:
                if a.investimento <= 0:
                    continue
                ativo = a.status == "ACTIVE"
                c = regras.classificar_anuncio(a.investimento, a.leadsMeta, a.leadsCrm, a.mqls, metas)
                rotulo, porque = regras.recomendacao(c, ativo)
                itens.append(MetaAdsCockpitCriativo(
                    id=a.id, mcgId=a.mcgId, nome=a.nome, campanha=campanha.nome, status=a.status,
                    ativo=ativo, investimento=a.investimento, leadsMeta=a.leadsMeta,
                    leadsCrm=a.leadsCrm, mqls=a.mqls, cpl=c.cpl, taxaMql=c.taxa_mql,
                    quadrante=c.quadrante, motivo=c.motivo, amostraPequena=c.amostra_pequena,
                    recomendacao=rotulo, porque=porque,
                ))
    itens.sort(key=lambda i: i.investimento, reverse=True)
    return itens


def montar(db: Session, emp_id: int, filtro: FiltroPainel) -> MetaAdsCockpitResponse:
    if filtro.data_inicial is None or filtro.data_final is None:
        raise BadRequestError("Informe data inicial e final")
    ini, fim = filtro.data_inicial, filtro.data_final
    metas = regras.metas_da_config(obter_config(db, emp_id))

    calculo = calcular_painel(db, emp_id, filtro)
    painel = calculo.resposta
    total = _sem_filhos(painel.total)

    ant_ini, ant_fim = regras.periodo_anterior(ini, fim)
    filtro_anterior = FiltroPainel(ant_ini, ant_fim, filtro.mac_id, filtro.somente_ativas)
    anterior = _sem_filhos(calcular_painel(db, emp_id, filtro_anterior).resposta.total)

    selo_cpl = regras.selo_cpl(total.cpl, metas)
    selo_taxa = regras.selo_taxa_mql(total.mqls, total.leadsCrm, metas)
    passagem = regras.gargalo(total.leadsCrm, total.mqls, total.oportunidades, total.vendas)
    frase = None
    if passagem is not None:
        base, chegaram = {
            "mql": (total.leadsCrm, total.mqls),
            "oportunidade": (total.mqls, total.oportunidades),
            "contrato": (total.oportunidades, total.vendas),
        }[passagem]
        frase = regras.frase_gargalo(passagem, base, chegaram)

    tipo, serie = _serie(db, emp_id, filtro, calculo)

    return MetaAdsCockpitResponse(
        temConta=painel.temConta,
        inicio=ini,
        fim=fim,
        metas=MetaAdsCockpitMetas(
            cpl=metas.cpl, taxaMql=metas.taxa_mql,
            custoMqlImplicito=round(metas.custo_mql_implicito, 2), cplFator=metas.fator,
        ),
        total=total,
        taxaMql=regras.taxa(total.mqls, total.leadsCrm),
        anterior=anterior,
        anteriorInicio=ant_ini,
        anteriorFim=ant_fim,
        anteriorTemDados=_tem_dados(anterior),
        selos=MetaAdsCockpitSelos(
            cpl=selo_cpl,
            taxaMql=selo_taxa,
            custoMql=regras.selo_custo_mql(total.custoMql, metas),
            saude=regras.saude_periodo(selo_cpl, selo_taxa),
        ),
        funil=_funil(total, passagem),
        gargalo=passagem,
        fraseGargalo=frase,
        intervalo=tipo,
        serie=serie,
        criativos=_criativos(painel, metas),
        operacao=MetaAdsCockpitOperacao(
            cobertura=painel.cobertura,
            horasPrimeiroContato=total.horasPrimeiroContato,
            alertasAbertos=contar_alertas_abertos(db, emp_id),
            origemRevisar=len(painel.revisaoOrigem),
        ),
    )
