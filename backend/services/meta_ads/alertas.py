"""Regras puras dos alertas de monitoramento Meta (sem banco).

Cada regra devolve um `Disparo` quando a condição vale, ou `None`. Só
`regra_sem_contato` leva nome e telefone na mensagem/dados.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

_TOLERANCIA = 1e-9
_DIAS_MIN_CTR = 14
_IMPRESSOES_MIN_CTR = 1000

_STATUS_CONTA = {
    2: "desativada",
    3: "pagamento pendente",
    7: "em análise de risco",
    8: "pagamento pendente",
    9: "período de carência",
    100: "encerrada",
    101: "encerrada",
}


@dataclass(frozen=True)
class Disparo:
    tipo: str
    chave: str
    mensagem: str
    dados: dict = field(default_factory=dict)


def _num(v: float, casas: int = 2) -> str:
    return f"{v:,.{casas}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def _brl(v: float) -> str:
    return f"R$ {_num(v)}"


def regra_cpl(man_id, nome, gasto_ontem, leads_ontem, gasto_base, leads_base, fator) -> Disparo | None:
    if leads_ontem < 1 or leads_base < 1:
        return None
    cpl_ontem = gasto_ontem / leads_ontem
    cpl_base = gasto_base / leads_base
    if not cpl_ontem > fator * cpl_base:
        return None
    mult = cpl_ontem / cpl_base if cpl_base else None
    mult_txt = f"{_num(mult, 1)}× a média de " if mult is not None else "acima da média de "
    return Disparo(
        "cpl",
        f"anuncio:{man_id}",
        f"CPL de ontem {_brl(cpl_ontem)} ({mult_txt}{_brl(cpl_base)} dos 7 dias anteriores).",
        {
            "man_id": man_id,
            "cpl_ontem": round(cpl_ontem, 2),
            "cpl_base": round(cpl_base, 2),
            "leads_ontem": leads_ontem,
            "leads_base": leads_base,
            "fator": fator,
        },
    )


def regra_gasto(man_id, nome, gasto_7d, leads_7d, limite) -> Disparo | None:
    if leads_7d != 0 or gasto_7d < limite:
        return None
    return Disparo(
        "gasto",
        f"anuncio:{man_id}",
        f"Gastou {_brl(gasto_7d)} nos últimos 7 dias sem nenhum lead da Meta.",
        {"man_id": man_id, "gasto_7d": round(gasto_7d, 2), "limite": limite},
    )


def regra_frequencia(man_id, nome, frequencia_7d, maximo) -> Disparo | None:
    if not frequencia_7d > maximo:
        return None
    return Disparo(
        "frequencia",
        f"anuncio:{man_id}",
        f"Frequência de {_num(frequencia_7d, 1)} nos últimos 7 dias (limite {_num(maximo, 1)}): criativo saturando.",
        {"man_id": man_id, "frequencia_7d": round(frequencia_7d, 2), "maximo": maximo},
    )


def regra_ctr(man_id, nome, ctr_inicial, imp_inicial, ctr_atual, imp_atual, dias_veiculacao, queda_pct) -> Disparo | None:
    if dias_veiculacao < _DIAS_MIN_CTR or imp_inicial < _IMPRESSOES_MIN_CTR or imp_atual < _IMPRESSOES_MIN_CTR:
        return None
    if not ctr_atual <= ctr_inicial * (1 - queda_pct / 100) + _TOLERANCIA:
        return None
    queda = (1 - ctr_atual / ctr_inicial) * 100 if ctr_inicial else 0.0
    return Disparo(
        "ctr",
        f"anuncio:{man_id}",
        f"CTR dos últimos 7 dias {_num(ctr_atual)}% ({_num(queda, 0)}% abaixo dos {_num(ctr_inicial)}% iniciais).",
        {
            "man_id": man_id,
            "ctr_inicial": round(ctr_inicial, 4),
            "ctr_atual": round(ctr_atual, 4),
            "imp_inicial": imp_inicial,
            "imp_atual": imp_atual,
            "dias_veiculacao": dias_veiculacao,
            "queda_pct": queda_pct,
        },
    )


def regra_anuncio_reprovado(man_id, nome, status, motivo) -> Disparo | None:
    if status not in ("DISAPPROVED", "WITH_ISSUES"):
        return None
    situacao = "reprovado" if status == "DISAPPROVED" else "com problemas"
    msg = f"Anúncio {situacao} na Meta."
    if motivo:
        msg += f" Motivo: {motivo}"
    return Disparo("parado", f"anuncio:{man_id}", msg, {"man_id": man_id})


def regra_conta(mac_id, nome, account_status, disable_reason) -> Disparo | None:
    if account_status in (None, 1):
        return None
    significado = _STATUS_CONTA.get(account_status, f"status {account_status} na Meta")
    return Disparo(
        "parado",
        f"conta:{mac_id}",
        f"Conta de anúncios fora do ar: {significado}.",
        {"mac_id": mac_id, "account_status": account_status, "disable_reason": disable_reason},
    )


def regra_campanha_sem_veicular(mcg_id, nome, status, impressoes_ontem) -> Disparo | None:
    if status != "ACTIVE" or impressoes_ontem != 0:
        return None
    return Disparo(
        "parado",
        f"campanha:{mcg_id}",
        "Campanha ativa sem nenhuma impressão ontem.",
        {"mcg_id": mcg_id},
    )


def regra_sem_contato(opo_id, titulo, contato, telefone, recebido_em, agora, horas, desde) -> Disparo | None:
    if recebido_em < desde or not agora - recebido_em > timedelta(hours=horas):
        return None
    decorridas = int((agora - recebido_em).total_seconds() // 3600)
    quem = contato or titulo
    msg = f"Lead {quem}"
    if telefone:
        msg += f" ({telefone})"
    msg += f" recebido há {decorridas} h sem contato."
    return Disparo(
        "sem_contato",
        f"lead:{opo_id}",
        msg,
        {"opo_id": opo_id, "contato": contato, "telefone": telefone, "horas": decorridas},
    )
