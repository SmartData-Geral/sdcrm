"""Alertas do monitoramento Meta: regras puras, coleta das metricas e persistencia.

Cada regra devolve um `Disparo` quando a condição vale, ou `None`. Só
`regra_sem_contato` leva nome e telefone na mensagem/dados.

Persistencia: no maximo um alerta nao resolvido por (empresa, tipo, chave). Quem avalia passa
os tipos avaliados e os disparos; alerta daqueles tipos sem disparo vira "resolvido", exceto as
chaves em `preservar` (conta que nao pode ser avaliada por erro da Meta ou dados incompletos).

Avaliacao diaria (depois da sync): cpl, gasto e ctr pelo banco; frequencia pela Meta.
Avaliacao de hora em hora: parado (status frescos da Meta) e sem_contato.
Datas gravadas e comparadas em UTC naive.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.tempo import utcnow
from ...exceptions import BadRequestError, NotFoundError
from ...models.meta_ads_alerta import (
    STATUS_ABERTO,
    STATUS_CIENTE,
    STATUS_RESOLVIDO,
    MetaAdsAlerta,
)
from ...models.meta_ads_anuncio import MetaAdsAnuncio
from ...models.meta_ads_campanha import MetaAdsCampanha
from ...models.meta_ads_conta import (
    STATUS_AVISO,
    STATUS_ERRO,
    STATUS_PERMISSAO_EXCESSIVA,
    STATUS_TOKEN_INVALIDO,
    MetaAdsConta,
)
from ...models.meta_ads_insight_anuncio_diario import MetaAdsInsightAnuncioDiario
from ...models.meta_ads_insight_diario import MetaAdsInsightDiario
from ...models.oportunidade import Oportunidade
from ...schemas.meta_ads import STATUS_ALERTA, MetaAdsAlertaResponse
from . import funil, sincronizacao
from .cliente_graph import ClienteGraph, MetaGraphErro, TokenInvalidoErro
from .config_monitor import obter_config
from .rastreio import tem_sinal_meta

logger = logging.getLogger(__name__)

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
    if ctr_inicial <= 0:
        return None
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


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------

TIPOS_DIARIOS = ("cpl", "gasto", "frequencia", "ctr")
TIPOS_HORARIOS = ("parado", "sem_contato")
_TIPOS_DO_BANCO = frozenset({"cpl", "gasto", "ctr"})
_COLUNA_LIGADO = {
    "cpl": "mmcAlertaCpl",
    "gasto": "mmcAlertaGasto",
    "frequencia": "mmcAlertaFrequencia",
    "ctr": "mmcAlertaCtr",
    "parado": "mmcAlertaParado",
    "sem_contato": "mmcAlertaSemContato",
}
# Conta que a Meta recusa ate trocarem o token: nem tentamos chamar.
_TOKEN_RUIM = frozenset({STATUS_TOKEN_INVALIDO, STATUS_PERMISSAO_EXCESSIVA})
# Ultima sync falhou: os insights do banco estao incompletos para a conta.
_SYNC_FALHOU = frozenset({STATUS_ERRO, STATUS_AVISO, *_TOKEN_RUIM})
LIMITE_LISTA = 500


def _utc_naive(dt: datetime | None) -> datetime | None:
    if dt is None or dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def sincronizar_disparos(
    db: Session,
    emp_id: int,
    tipos: set[str],
    disparos: list[Disparo],
    agora: datetime,
    *,
    preservar: set[tuple[str, str]] = frozenset(),
) -> dict:
    """Aplica os disparos dos `tipos` avaliados. Disparo de tipo fora de `tipos` e ignorado.

    Novo -> "aberto"; ja existente e nao resolvido -> atualiza mensagem/dados/ultimo (mantem
    "ciente"); nao resolvido sem disparo -> "resolvido", salvo (tipo, chave) em `preservar`.
    """
    agora = _utc_naive(agora)
    tipos = set(tipos)
    contagem = {"criados": 0, "atualizados": 0, "resolvidos": 0}
    if not tipos:
        return contagem

    def _resolver(alerta: MetaAdsAlerta) -> None:
        alerta.malStatus = STATUS_RESOLVIDO
        alerta.malResolvidoEm = agora
        contagem["resolvidos"] += 1

    existentes: dict[tuple[str, str], MetaAdsAlerta] = {}
    for alerta in db.execute(
        select(MetaAdsAlerta)
        .where(
            MetaAdsAlerta.malEmpId == emp_id,
            MetaAdsAlerta.malTipo.in_(sorted(tipos)),
            MetaAdsAlerta.malStatus != STATUS_RESOLVIDO,
        )
        .order_by(MetaAdsAlerta.malId)
    ).scalars():
        chave = (alerta.malTipo, alerta.malChave)
        if chave in existentes:
            _resolver(alerta)  # duplicado (avaliacoes concorrentes): fica o mais antigo
        else:
            existentes[chave] = alerta

    novos = {(d.tipo, d.chave[:60]): d for d in disparos if d.tipo in tipos}
    for (tipo, chave), d in novos.items():
        alerta = existentes.pop((tipo, chave), None)
        if alerta is None:
            db.add(
                MetaAdsAlerta(
                    malEmpId=emp_id,
                    malTipo=tipo,
                    malChave=chave,
                    malStatus=STATUS_ABERTO,
                    malMensagem=d.mensagem[:500],
                    malDados=dict(d.dados),
                    malPrimeiroEm=agora,
                    malUltimoEm=agora,
                )
            )
            contagem["criados"] += 1
        else:
            alerta.malMensagem = d.mensagem[:500]
            alerta.malDados = dict(d.dados)
            alerta.malUltimoEm = agora
            contagem["atualizados"] += 1
    for chave, alerta in existentes.items():
        if chave not in preservar:
            _resolver(alerta)
    db.commit()
    return contagem


# ---------------------------------------------------------------------------
# Coleta
# ---------------------------------------------------------------------------


def _ligados(cfg, tipos) -> set[str]:
    return {t for t in tipos if getattr(cfg, _COLUNA_LIGADO[t])}


def _contas_ativas(db: Session, emp_id: int) -> list[MetaAdsConta]:
    return list(
        db.execute(
            select(MetaAdsConta)
            .where(MetaAdsConta.macEmpId == emp_id, MetaAdsConta.macAtivo.is_(True))
            .order_by(MetaAdsConta.macId)
        ).scalars()
    )


def _ids_anuncios(db: Session, mac_id: int) -> list[int]:
    return list(
        db.execute(select(MetaAdsAnuncio.manId).where(MetaAdsAnuncio.manMacId == mac_id)).scalars()
    )


def _ids_campanhas(db: Session, mac_id: int) -> list[int]:
    return list(
        db.execute(select(MetaAdsCampanha.mcgId).where(MetaAdsCampanha.mcgMacId == mac_id)).scalars()
    )


def _registrar_falha(mac_id: int, exc: Exception) -> None:
    if isinstance(exc, MetaGraphErro):
        # Mensagens do cliente ja vem sem o token.
        logger.warning("Alertas Meta: conta %s nao avaliada (%s)", mac_id, exc.mensagem)
    else:
        logger.exception("Alertas Meta: falha ao avaliar a conta %s", mac_id)


def _exigir_token_bom(conta: MetaAdsConta) -> None:
    if conta.macStatus in _TOKEN_RUIM:
        raise TokenInvalidoErro("Token da conta precisa ser trocado; conta não avaliada.")


def _zero() -> dict:
    return {
        "gasto_ontem": 0.0, "leads_ontem": 0, "gasto_base": 0.0, "leads_base": 0,
        "gasto_7d": 0.0, "leads_7d": 0, "imp_7d": 0, "cliques_7d": 0,
    }


def _disparos_do_banco(db, emp_id, mac_ids, ontem: date, cfg, ligados) -> list[Disparo]:
    """cpl, gasto e ctr a partir de meta_ads_insight_anuncio_diario."""
    ini_base, fim_base = ontem - timedelta(days=7), ontem - timedelta(days=1)
    ini_7d = ontem - timedelta(days=6)
    soma: dict[int, dict] = defaultdict(_zero)
    ins = MetaAdsInsightAnuncioDiario
    for man_id, dia, inv, imp, cliques, leads in db.execute(
        select(
            ins.miaManId, ins.miaData, ins.miaInvestimento, ins.miaImpressoes, ins.miaCliques,
            ins.miaLeadsMeta,
        ).where(
            ins.miaEmpId == emp_id,
            ins.miaMacId.in_(mac_ids),
            ins.miaData >= ini_base,
            ins.miaData <= ontem,
        )
    ).all():
        s = soma[man_id]
        inv = float(inv or 0)
        if dia == ontem:
            s["gasto_ontem"] += inv
            s["leads_ontem"] += leads
        if ini_base <= dia <= fim_base:
            s["gasto_base"] += inv
            s["leads_base"] += leads
        if dia >= ini_7d:
            s["gasto_7d"] += inv
            s["leads_7d"] += leads
            s["imp_7d"] += imp
            s["cliques_7d"] += cliques
    if not soma:
        return []
    anuncios = {
        a.manId: a
        for a in db.execute(
            select(MetaAdsAnuncio).where(MetaAdsAnuncio.manId.in_(sorted(soma)))
        ).scalars()
    }
    iniciais = _janelas_iniciais(db, anuncios.values(), ontem) if "ctr" in ligados else {}

    disparos: list[Disparo] = []
    for man_id in sorted(soma):
        s, anu = soma[man_id], anuncios.get(man_id)
        nome = anu.manNome if anu else str(man_id)
        candidatos = []
        if "cpl" in ligados:
            candidatos.append(regra_cpl(
                man_id, nome, s["gasto_ontem"], s["leads_ontem"], s["gasto_base"], s["leads_base"],
                float(cfg.mmcCplFator),
            ))
        if "gasto" in ligados:
            candidatos.append(
                regra_gasto(man_id, nome, s["gasto_7d"], s["leads_7d"], float(cfg.mmcGastoSemLead))
            )
        if man_id in iniciais:
            imp_ini, cliques_ini, dias = iniciais[man_id]
            candidatos.append(regra_ctr(
                man_id,
                nome,
                cliques_ini / imp_ini * 100 if imp_ini else 0.0,
                imp_ini,
                s["cliques_7d"] / s["imp_7d"] * 100 if s["imp_7d"] else 0.0,
                s["imp_7d"],
                dias,
                cfg.mmcQuedaCtrPct,
            ))
        disparos.extend(d for d in candidatos if d is not None)
    return disparos


def _janelas_iniciais(db, anuncios, ontem: date) -> dict[int, tuple[int, int, int]]:
    """Por anuncio com 14+ dias de veiculacao: (impressoes, cliques, dias) dos 7 primeiros dias."""
    primeiro = {
        a.manId: a.manPrimeiroDia
        for a in anuncios
        if a.manPrimeiroDia is not None and (ontem - a.manPrimeiroDia).days + 1 >= _DIAS_MIN_CTR
    }
    if not primeiro:
        return {}
    res = {man_id: [0, 0, (ontem - p).days + 1] for man_id, p in primeiro.items()}
    ins = MetaAdsInsightAnuncioDiario
    for man_id, dia, imp, cliques in db.execute(
        select(ins.miaManId, ins.miaData, ins.miaImpressoes, ins.miaCliques).where(
            ins.miaManId.in_(sorted(primeiro)),
            ins.miaData >= min(primeiro.values()),
            ins.miaData <= max(primeiro.values()) + timedelta(days=6),
        )
    ).all():
        p = primeiro[man_id]
        if p <= dia <= p + timedelta(days=6):
            res[man_id][0] += imp
            res[man_id][1] += cliques
    return {k: tuple(v) for k, v in res.items()}


def _disparos_frequencia(db, conta: MetaAdsConta, ontem: date, cfg, fabrica_cliente) -> list[Disparo]:
    _exigir_token_bom(conta)
    mac_id, act = conta.macId, conta.macContaExterna
    with sincronizacao.cliente_da_conta(db, mac_id, fabrica_cliente=fabrica_cliente) as cliente:
        frequencias = cliente.frequencia_7_dias(act, ontem - timedelta(days=6), ontem)
    anuncios = {
        a.manAnuncioExterno: a
        for a in db.execute(select(MetaAdsAnuncio).where(MetaAdsAnuncio.manMacId == mac_id)).scalars()
    }
    disparos = []
    for f in frequencias:
        anu = anuncios.get(f.anuncio_id)
        if anu is None:
            continue
        d = regra_frequencia(anu.manId, anu.manNome, f.frequencia, float(cfg.mmcFrequenciaMax))
        if d is not None:
            disparos.append(d)
    return disparos


def avaliar_diarios(db: Session, emp_id: int, hoje: date, fabrica_cliente=ClienteGraph) -> dict:
    """cpl, gasto, frequencia e ctr do dia anterior a `hoje`.

    Tipo desligado na config tem os alertas nao resolvidos encerrados. Conta com a ultima
    sync falhada nao tem alertas do banco resolvidos; erro da Meta na frequencia de uma conta
    nao resolve os alertas de frequencia dela.
    """
    cfg = obter_config(db, emp_id)
    ligados = _ligados(cfg, TIPOS_DIARIOS)
    contas = _contas_ativas(db, emp_id)
    ontem = hoje - timedelta(days=1)
    disparos: list[Disparo] = []
    preservar: set[tuple[str, str]] = set()
    erros = 0

    do_banco = ligados & _TIPOS_DO_BANCO
    if do_banco and contas:
        for conta in contas:
            if conta.macStatus in _SYNC_FALHOU:
                preservar |= {
                    (tipo, f"anuncio:{man_id}")
                    for man_id in _ids_anuncios(db, conta.macId)
                    for tipo in do_banco
                }
        disparos += _disparos_do_banco(db, emp_id, [c.macId for c in contas], ontem, cfg, do_banco)

    if "frequencia" in ligados:
        for conta in contas:
            mac_id = conta.macId
            try:
                disparos += _disparos_frequencia(db, conta, ontem, cfg, fabrica_cliente)
            except Exception as exc:
                erros += 1
                _registrar_falha(mac_id, exc)
                preservar |= {("frequencia", f"anuncio:{m}") for m in _ids_anuncios(db, mac_id)}

    resultado = sincronizar_disparos(
        db, emp_id, set(TIPOS_DIARIOS), disparos, utcnow(), preservar=preservar
    )
    resultado["erros"] = erros
    return resultado


def _chaves_parado_da_conta(db: Session, mac_id: int) -> set[tuple[str, str]]:
    return {
        ("parado", f"conta:{mac_id}"),
        *(("parado", f"anuncio:{m}") for m in _ids_anuncios(db, mac_id)),
        *(("parado", f"campanha:{c}") for c in _ids_campanhas(db, mac_id)),
    }


def _disparos_parado(db, conta: MetaAdsConta, agora: datetime, fabrica_cliente, preservar) -> list[Disparo]:
    """Status de conta, anuncios e campanhas lidos agora da Meta (nunca os gravados na sync)."""
    _exigir_token_bom(conta)
    mac_id, act, nome_conta = conta.macId, conta.macContaExterna, conta.macNome
    with sincronizacao.cliente_da_conta(db, mac_id, fabrica_cliente=fabrica_cliente) as cliente:
        campanhas = cliente.listar_campanhas(act)
        anuncios = cliente.listar_anuncios(act)
        status = cliente.obter_status_conta(act)

    disparos = [regra_conta(mac_id, nome_conta, status.account_status, status.disable_reason)]
    anuncios_banco = {
        externo: (man_id, nome)
        for man_id, externo, nome in db.execute(
            select(MetaAdsAnuncio.manId, MetaAdsAnuncio.manAnuncioExterno, MetaAdsAnuncio.manNome)
            .where(MetaAdsAnuncio.manMacId == mac_id)
        ).all()
    }
    for a in anuncios:
        # Anuncio ainda nao sincronizado (sem manId) entra na avaliacao depois da proxima sync.
        if a.id in anuncios_banco:
            man_id, nome = anuncios_banco[a.id]
            disparos.append(regra_anuncio_reprovado(man_id, nome, a.status, a.motivo))

    campanhas_banco = {
        externo: (mcg_id, nome)
        for mcg_id, externo, nome in db.execute(
            select(MetaAdsCampanha.mcgId, MetaAdsCampanha.mcgCampanhaExterna, MetaAdsCampanha.mcgNome)
            .where(MetaAdsCampanha.mcgMacId == mac_id)
        ).all()
    }
    hoje_local = sincronizacao.hoje_da_conta(conta, agora)
    ultima_sync = _utc_naive(conta.macUltimaSync)
    if ultima_sync is None or sincronizacao.hoje_da_conta(conta, ultima_sync) < hoje_local:
        # Sem sync bem-sucedida hoje, o "ontem" do banco esta parcial: campanhas ficam como estao.
        preservar |= {("parado", f"campanha:{mcg_id}") for mcg_id, _ in campanhas_banco.values()}
    else:
        ontem = hoje_local - timedelta(days=1)
        impressoes = dict(
            db.execute(
                select(MetaAdsInsightDiario.midMcgId, func.sum(MetaAdsInsightDiario.midImpressoes))
                .where(MetaAdsInsightDiario.midMacId == mac_id, MetaAdsInsightDiario.midData == ontem)
                .group_by(MetaAdsInsightDiario.midMcgId)
            ).all()
        )
        for c in campanhas:
            if c.id in campanhas_banco:
                mcg_id, nome = campanhas_banco[c.id]
                # Campanha ativa sem linha de insight ontem conta como 0 impressao.
                disparos.append(regra_campanha_sem_veicular(
                    mcg_id, nome, c.status, int(impressoes.get(mcg_id) or 0)
                ))
    return [d for d in disparos if d is not None]


def _disparos_sem_contato(db: Session, emp_id: int, agora: datetime, cfg) -> list[Disparo]:
    desde = _utc_naive(cfg.mmcSemContatoDesde)
    if desde is None:
        return []
    leads = db.execute(
        select(
            Oportunidade.opoId,
            Oportunidade.opoTitulo,
            Oportunidade.opoNomeContato,
            Oportunidade.opoTelefone,
            Oportunidade.opoDataCriacao,
        ).where(
            Oportunidade.opoEmpId == emp_id,
            Oportunidade.opoAtivo.is_(True),
            Oportunidade.opoStatusFechamento.is_(None),
            tem_sinal_meta,
            # Folga de um dia no SQL (valores naive e aware misturados); o corte exato e na regra.
            Oportunidade.opoDataCriacao >= desde - timedelta(days=1),
        )
    ).all()
    if not leads:
        return []
    interacoes = funil.primeira_interacao(db, emp_id)
    disparos = []
    for opo_id, titulo, contato, telefone, criado in leads:
        if opo_id in interacoes or criado is None:
            continue
        d = regra_sem_contato(
            opo_id, titulo, contato, telefone, _utc_naive(criado), agora, cfg.mmcHorasSemContato, desde
        )
        if d is not None:
            disparos.append(d)
    return disparos


def avaliar_horarios(db: Session, emp_id: int, agora: datetime, fabrica_cliente=ClienteGraph) -> dict:
    """parado (status frescos da Meta) e sem_contato.

    Tipo desligado na config tem os alertas nao resolvidos encerrados. Conta que nao pode ser
    avaliada (erro da Meta, token ruim) nao tem os alertas "parado" dela resolvidos.
    """
    agora = _utc_naive(agora)
    cfg = obter_config(db, emp_id)
    ligados = _ligados(cfg, TIPOS_HORARIOS)
    disparos: list[Disparo] = []
    preservar: set[tuple[str, str]] = set()
    erros = 0

    if "parado" in ligados:
        for conta in _contas_ativas(db, emp_id):
            mac_id = conta.macId
            try:
                disparos += _disparos_parado(db, conta, agora, fabrica_cliente, preservar)
            except Exception as exc:
                erros += 1
                _registrar_falha(mac_id, exc)
                preservar |= _chaves_parado_da_conta(db, mac_id)
    if "sem_contato" in ligados:
        disparos += _disparos_sem_contato(db, emp_id, agora, cfg)

    resultado = sincronizar_disparos(
        db, emp_id, set(TIPOS_HORARIOS), disparos, agora, preservar=preservar
    )
    resultado["erros"] = erros
    return resultado


# ---------------------------------------------------------------------------
# Leitura e "ciente"
# ---------------------------------------------------------------------------


def _respostas(db: Session, emp_id: int, alertas: list[MetaAdsAlerta]) -> list[MetaAdsAlertaResponse]:
    ids: dict[str, set[int]] = {"anuncio": set(), "campanha": set(), "conta": set()}
    for alerta in alertas:
        alvo, _, numero = alerta.malChave.partition(":")
        if alvo in ids and numero.isdigit():
            ids[alvo].add(int(numero))
    colunas = {
        "anuncio": (MetaAdsAnuncio.manId, MetaAdsAnuncio.manNome, MetaAdsAnuncio.manEmpId),
        "campanha": (MetaAdsCampanha.mcgId, MetaAdsCampanha.mcgNome, MetaAdsCampanha.mcgEmpId),
        "conta": (MetaAdsConta.macId, MetaAdsConta.macNome, MetaAdsConta.macEmpId),
    }
    nomes: dict[tuple[str, int], str] = {}
    for alvo, (col_id, col_nome, col_emp) in colunas.items():
        if ids[alvo]:
            for id_, nome in db.execute(
                select(col_id, col_nome).where(col_emp == emp_id, col_id.in_(sorted(ids[alvo])))
            ).all():
                nomes[(alvo, id_)] = nome

    def _nome(chave: str) -> str | None:
        alvo, _, numero = chave.partition(":")
        return nomes.get((alvo, int(numero))) if numero.isdigit() else None

    return [
        MetaAdsAlertaResponse(
            malId=x.malId,
            malTipo=x.malTipo,
            malChave=x.malChave,
            malStatus=x.malStatus,
            malMensagem=x.malMensagem,
            malDados=x.malDados,
            malPrimeiroEm=x.malPrimeiroEm,
            malUltimoEm=x.malUltimoEm,
            malResolvidoEm=x.malResolvidoEm,
            alvoNome=_nome(x.malChave),
        )
        for x in alertas
    ]


def listar(db: Session, emp_id: int, status: str | None) -> list[MetaAdsAlertaResponse]:
    """Alertas da empresa, mais recentes primeiro (ate LIMITE_LISTA); `status` None = todos."""
    if status is not None and status not in STATUS_ALERTA:
        raise BadRequestError("Status de alerta inválido")
    q = select(MetaAdsAlerta).where(MetaAdsAlerta.malEmpId == emp_id)
    if status is not None:
        q = q.where(MetaAdsAlerta.malStatus == status)
    alertas = list(
        db.execute(
            q.order_by(MetaAdsAlerta.malUltimoEm.desc(), MetaAdsAlerta.malId.desc()).limit(LIMITE_LISTA)
        ).scalars()
    )
    return _respostas(db, emp_id, alertas)


def marcar_ciente(db: Session, emp_id: int, mal_id: int) -> MetaAdsAlertaResponse:
    """Aberto -> ciente. Ciente ou resolvido ficam como estao. Outra empresa -> 404."""
    alerta = db.execute(
        select(MetaAdsAlerta).where(MetaAdsAlerta.malId == mal_id, MetaAdsAlerta.malEmpId == emp_id)
    ).scalar_one_or_none()
    if alerta is None:
        raise NotFoundError("Alerta não encontrado")
    if alerta.malStatus == STATUS_ABERTO:
        alerta.malStatus = STATUS_CIENTE
        db.commit()
    return _respostas(db, emp_id, [alerta])[0]


# ---------------------------------------------------------------------------
# Rodadas do worker
# ---------------------------------------------------------------------------


def empresas_com_conta_ativa(db: Session) -> list[int]:
    return list(
        db.execute(
            select(MetaAdsConta.macEmpId)
            .where(MetaAdsConta.macAtivo.is_(True))
            .distinct()
            .order_by(MetaAdsConta.macEmpId)
        ).scalars()
    )


def _para_cada_empresa(avaliar, fabrica_sessao, rodada: str) -> int:
    """Uma sessao por empresa; falha numa empresa nao impede as outras. Devolve quantas rodaram."""
    if fabrica_sessao is None:
        from ...database import SessionLocal

        fabrica_sessao = SessionLocal
    with fabrica_sessao() as db:
        ids = empresas_com_conta_ativa(db)
    ok = 0
    for emp_id in ids:
        try:
            with fabrica_sessao() as db:
                avaliar(db, emp_id)
            ok += 1
        except Exception:
            logger.exception("Alertas Meta: falha na avaliacao %s da empresa %s", rodada, emp_id)
    return ok


def avaliar_diarios_todas(hoje: date, *, fabrica_sessao=None) -> int:
    return _para_cada_empresa(lambda db, e: avaliar_diarios(db, e, hoje), fabrica_sessao, "diaria")


def avaliar_horarios_todas(agora: datetime, *, fabrica_sessao=None) -> int:
    """Rodada horaria por empresa: alertas e, se for a hora, o resumo diario (mesmo try/except)."""

    def avaliar(db: Session, emp_id: int) -> None:
        from . import resumo

        avaliar_horarios(db, emp_id, agora)
        resumo.gerar_se_devido(db, emp_id, agora)

    return _para_cada_empresa(avaliar, fabrica_sessao, "horaria")
