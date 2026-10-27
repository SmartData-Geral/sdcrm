"""Regras puras do cockpit de campanhas: selos, gargalo, quadrante dos criativos e periodos.

Sem acesso a banco: so le atributos do objeto de configuracao em `metas_da_config`.
Os textos de "por que" seguem a tabela 5.7 da spec.
"""
from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from fractions import Fraction
from typing import Literal

Selo = Literal["bom", "atencao", "ruim", "sem_dados"]
Quadrante = Literal["escalar", "otimizar_custo", "rever_publico", "pausar", "aguardar_dados"]
Passagem = Literal["mql", "oportunidade", "contrato"]

AMOSTRA_MINIMA = 5
BASE_MINIMA_GARGALO = 3
FRACAO_ATENCAO_TAXA = 0.6
LIMITE_DIAS_MENSAL = 62

_GRAVIDADE = {"bom": 0, "atencao": 1, "ruim": 2}
_MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")

_ROTULOS = {
    "escalar": "Escalar",
    "otimizar_custo": "Otimizar custo",
    "rever_publico": "Rever público",
    "pausar": "Pausar",
    "aguardar_dados": "Aguardar dados",
}
_POR_QUE = {
    "escalar": "Lead barato e que vira reunião: candidato a receber mais verba.",
    "otimizar_custo": "Traz MQL, mas cada lead está acima da meta: testar público ou lance.",
    "rever_publico": "Lead barato que ainda não vira reunião: rever público e perguntas do formulário.",
    "pausar": "Caro e sem MQL até agora: candidato a pausar.",
}
_POR_QUE_AGUARDAR = {
    "sem_lead": "Gasto ainda baixo e nenhum lead: aguardar mais dados.",
    "sem_crm": "Os leads ainda não chegaram ao CRM com este anúncio.",
}
# passagem: (frase sem ninguém na passagem, frase "para cada N")
_FRASES = {
    "mql": ("Nenhum dos {base} leads no CRM virou MQL.", "Para cada {n} leads no CRM, só 1 vira MQL."),
    "oportunidade": ("Nenhum dos {base} MQLs virou oportunidade.", "Para cada {n} MQLs, só 1 vira oportunidade."),
    "contrato": (
        "Nenhuma das {base} oportunidades virou contrato.",
        "Para cada {n} oportunidades, só 1 vira contrato.",
    ),
}


@dataclass(frozen=True)
class Metas:
    cpl: float
    taxa_mql: float
    fator: float
    gasto_sem_lead: float

    @property
    def custo_mql_implicito(self) -> float:
        return self.cpl / (self.taxa_mql / 100)


def metas_da_config(cfg) -> Metas:
    return Metas(
        cpl=float(cfg.mmcMetaCpl),
        taxa_mql=float(cfg.mmcMetaTaxaMql),
        fator=float(cfg.mmcCplFator),
        gasto_sem_lead=float(cfg.mmcGastoSemLead),
    )


def taxa(parte: int, base: int) -> float | None:
    if not base:
        return None
    return round(parte / base * 100, 2)


def _selo_custo(valor: float | None, meta: float, fator: float) -> Selo:
    if valor is None:
        return "sem_dados"
    if valor <= meta:
        return "bom"
    if valor <= meta * fator:
        return "atencao"
    return "ruim"


def selo_cpl(cpl: float | None, m: Metas) -> Selo:
    return _selo_custo(cpl, m.cpl, m.fator)


def selo_custo_mql(custo_mql: float | None, m: Metas) -> Selo:
    return _selo_custo(custo_mql, m.custo_mql_implicito, m.fator)


def selo_taxa_mql(mqls: int, leads_crm: int, m: Metas) -> Selo:
    if not leads_crm:
        return "sem_dados"
    valor = mqls / leads_crm * 100
    if valor >= m.taxa_mql:
        return "bom"
    if valor >= m.taxa_mql * FRACAO_ATENCAO_TAXA:
        return "atencao"
    return "ruim"


def saude_periodo(cpl: Selo, taxa_mql: Selo) -> Selo:
    if cpl == "sem_dados":
        return "sem_dados"
    selos = [s for s in (cpl, taxa_mql) if s != "sem_dados"]
    return max(selos, key=lambda s: _GRAVIDADE[s])


def gargalo(leads_crm: int, mqls: int, oportunidades: int, contratos: int) -> Passagem | None:
    """Passagem de menor taxa entre as de base >= 3; no empate, a mais cedo no funil."""
    passagens: list[tuple[Passagem, int, int]] = [
        ("mql", leads_crm, mqls),
        ("oportunidade", mqls, oportunidades),
        ("contrato", oportunidades, contratos),
    ]
    elegiveis = [(p, Fraction(chegaram, base)) for p, base, chegaram in passagens if base >= BASE_MINIMA_GARGALO]
    if not elegiveis:
        return None
    return min(elegiveis, key=lambda item: item[1])[0]


def frase_gargalo(passagem: Passagem, base: int, chegaram: int) -> str | None:
    if chegaram >= base:
        return None
    nenhum, para_cada = _FRASES[passagem]
    if chegaram == 0:
        return nenhum.format(base=base)
    return para_cada.format(n=max(2, int(base / chegaram + 0.5)))


@dataclass(frozen=True)
class Classificacao:
    quadrante: Quadrante
    motivo: Literal["sem_lead", "sem_crm"] | None
    amostra_pequena: bool
    cpl: float | None
    taxa_mql: float | None


def classificar_anuncio(investimento: float, leads_meta: int, leads_crm: int, mqls: int, m: Metas) -> Classificacao:
    if leads_meta == 0 and leads_crm == 0:
        if investimento >= m.gasto_sem_lead:
            return Classificacao("pausar", None, True, None, None)
        return Classificacao("aguardar_dados", "sem_lead", False, None, None)
    if leads_crm == 0:
        return Classificacao("aguardar_dados", "sem_crm", False, round(investimento / leads_meta, 2), None)
    cpl = investimento / (leads_meta or leads_crm)
    taxa_bruta = mqls / leads_crm * 100
    barato = cpl <= m.cpl
    converte = taxa_bruta >= m.taxa_mql
    if barato and converte:
        quadrante: Quadrante = "escalar"
    elif converte:
        quadrante = "otimizar_custo"
    elif barato:
        quadrante = "rever_publico"
    else:
        quadrante = "pausar"
    return Classificacao(quadrante, None, leads_crm < AMOSTRA_MINIMA, round(cpl, 2), round(taxa_bruta, 2))


def recomendacao(c: Classificacao, ativo: bool) -> tuple[str, str]:
    """(rotulo, por que) da recomendacao do anuncio."""
    rotulo = _ROTULOS[c.quadrante]
    if c.quadrante == "aguardar_dados":
        porque = _POR_QUE_AGUARDAR[c.motivo or "sem_lead"]
    else:
        porque = _POR_QUE[c.quadrante]
        if c.quadrante == "pausar" and not ativo:
            rotulo = "Manter pausado"
            porque += " (já pausado)"
    if c.amostra_pequena:
        porque += f" Amostra pequena: menos de {AMOSTRA_MINIMA} leads."
    return rotulo, porque


def periodo_anterior(inicio: date, fim: date) -> tuple[date, date]:
    dias = (fim - inicio).days + 1
    novo_fim = inicio - timedelta(days=1)
    return novo_fim - timedelta(days=dias - 1), novo_fim


def intervalos(inicio: date, fim: date) -> tuple[Literal["mes", "semana"], list[tuple[date, date, str]]]:
    """Meses (periodo > 62 dias) ou semanas de segunda a domingo, cortados nas pontas."""
    itens: list[tuple[date, date, str]] = []
    atual = inicio
    if (fim - inicio).days + 1 > LIMITE_DIAS_MENSAL:
        while atual <= fim:
            ultimo = date(atual.year, atual.month, monthrange(atual.year, atual.month)[1])
            itens.append((atual, min(ultimo, fim), f"{_MESES[atual.month - 1]}/{atual.year}"))
            atual = ultimo + timedelta(days=1)
        return "mes", itens
    while atual <= fim:
        domingo = atual + timedelta(days=6 - atual.weekday())
        corte = min(domingo, fim)
        itens.append((atual, corte, f"{atual:%d/%m}–{corte:%d/%m}"))
        atual = domingo + timedelta(days=1)
    return "semana", itens
