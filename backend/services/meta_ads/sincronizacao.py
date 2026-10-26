"""
Sincronizacao de uma conta de anuncios: campanhas + insights diarios + vinculo dos leads.

Protocolo: quem dispara pega a trava com `reivindicar` (UPDATE condicional, seguro entre
requisicoes concorrentes) e so entao chama `sincronizar_conta`, que SEMPRE libera a trava
e grava uma linha em meta_ads_sync_log. Dados novos e status "ok" entram no mesmo commit;
em qualquer erro ha rollback e nada parcial fica gravado.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from ...core.cripto import decifrar
from ...core.tempo import utcnow
from ...models.meta_ads_anuncio import MetaAdsAnuncio
from ...models.meta_ads_campanha import MetaAdsCampanha
from ...models.meta_ads_conjunto import MetaAdsConjunto
from ...models.meta_ads_conta import (
    STATUS_AVISO,
    STATUS_ERRO,
    STATUS_OK,
    STATUS_PERMISSAO_EXCESSIVA,
    STATUS_SINCRONIZANDO,
    STATUS_TOKEN_INVALIDO,
    MetaAdsConta,
)
from ...models.meta_ads_insight_anuncio_diario import MetaAdsInsightAnuncioDiario
from ...models.meta_ads_insight_diario import MetaAdsInsightDiario
from ...models.meta_ads_sync_log import MetaAdsSyncLog
from . import vinculo
from .cliente_graph import (
    MENSAGEM_PERMISSAO_EXCESSIVA,
    ClienteGraph,
    ErroTemporario,
    MetaGraphErro,
    PermissaoExcessivaErro,
    TokenInvalidoErro,
    permissoes_de_escrita,
)

logger = logging.getLogger(__name__)

JANELA_DIAS = 30
CARGA_INICIAL_DIAS = 90
MAX_DIAS_PERIODO = 366
TRAVA_MINUTOS = 30
FUSO_PADRAO = "America/Sao_Paulo"


@dataclass
class ResultadoSync:
    status: str
    linhas: int = 0
    leads_vinculados: int = 0
    erro: str | None = None


def hoje_da_conta(conta, agora_utc: datetime | None = None) -> date:
    try:
        fuso = ZoneInfo(conta.macFuso or FUSO_PADRAO)
    except (ZoneInfoNotFoundError, ValueError):
        fuso = ZoneInfo(FUSO_PADRAO)
    agora = (agora_utc or utcnow()).replace(tzinfo=timezone.utc)
    return agora.astimezone(fuso).date()


def janela_padrao(conta, hoje: date) -> tuple[date, date]:
    dias = JANELA_DIAS if conta.macCargaInicialFeita else CARGA_INICIAL_DIAS
    return hoje - timedelta(days=dias), hoje


def reivindicar(db: Session, mac_id: int) -> bool:
    agora = utcnow()
    resultado = db.execute(
        update(MetaAdsConta)
        .where(
            MetaAdsConta.macId == mac_id,
            MetaAdsConta.macAtivo.is_(True),
            or_(
                MetaAdsConta.macStatus != STATUS_SINCRONIZANDO,
                MetaAdsConta.macSyncIniciadaEm.is_(None),
                MetaAdsConta.macSyncIniciadaEm < agora - timedelta(minutes=TRAVA_MINUTOS),
            ),
        )
        .values(macStatus=STATUS_SINCRONIZANDO, macSyncIniciadaEm=agora)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return resultado.rowcount == 1


def sincronizar_conta(
    db: Session,
    mac_id: int,
    *,
    origem: str,
    inicio: date | None = None,
    fim: date | None = None,
    fabrica_cliente=ClienteGraph,
) -> ResultadoSync:
    # populate_existing: o UPDATE de `reivindicar` nao sincroniza o identity map; sem isto
    # a conta em memoria pode estar velha e a liberacao da trava nao seria gravada.
    conta = db.get(MetaAdsConta, mac_id, populate_existing=True)
    t0 = time.perf_counter()
    janela_explicita = inicio is not None and fim is not None
    if not janela_explicita:
        inicio, fim = janela_padrao(conta, hoje_da_conta(conta))
        if not conta.macCargaInicialFeita:
            origem = "carga_inicial"
    try:
        token = decifrar(conta.macToken)
        if token is None:
            raise TokenInvalidoErro(
                "Token ilegível (a chave de criptografia mudou) — cadastre o token de novo."
            )
        conta_externa = conta.macContaExterna
        # Encerra a transacao de leitura antes do HTTP demorado: evita snapshot velho
        # (REPEATABLE READ) ao vincular leads depois.
        db.rollback()
        with fabrica_cliente(token) as cliente:
            if permissoes_de_escrita(cliente.listar_permissoes()):
                raise PermissaoExcessivaErro(MENSAGEM_PERMISSAO_EXCESSIVA)
            campanhas = cliente.listar_campanhas(conta_externa)
            insights = cliente.listar_insights(conta_externa, inicio, fim)
            conjuntos = cliente.listar_conjuntos(conta_externa)
            anuncios = cliente.listar_anuncios(conta_externa)
            insights_anuncio = cliente.listar_insights_anuncios(conta_externa, inicio, fim)
            status_conta = cliente.obter_status_conta(conta_externa)
        conta = db.get(MetaAdsConta, mac_id, populate_existing=True)
        linhas = _gravar(
            db, conta, campanhas, insights, inicio, fim, conjuntos, anuncios, insights_anuncio
        )
        conta.macAccountStatus = status_conta.account_status
        conta.macDisableReason = status_conta.disable_reason
        vinculados = vinculo.vincular_pendentes(db, conta.macEmpId)
        resultado = ResultadoSync(STATUS_OK, linhas, vinculados)
    except TokenInvalidoErro as exc:
        db.rollback()
        resultado = ResultadoSync(STATUS_TOKEN_INVALIDO, erro=exc.mensagem)
    except PermissaoExcessivaErro as exc:
        db.rollback()
        resultado = ResultadoSync(STATUS_PERMISSAO_EXCESSIVA, erro=exc.mensagem)
    except ErroTemporario as exc:
        db.rollback()
        resultado = ResultadoSync(STATUS_AVISO, erro=exc.mensagem)
    except MetaGraphErro as exc:
        db.rollback()
        resultado = ResultadoSync(STATUS_ERRO, erro=exc.mensagem)
    except Exception as exc:
        db.rollback()
        logger.exception("Falha interna na sincronizacao Meta Ads da conta %s", mac_id)
        resultado = ResultadoSync(
            STATUS_ERRO, erro=f"Falha interna na sincronização ({type(exc).__name__})."
        )
    duracao_ms = int((time.perf_counter() - t0) * 1000)
    _finalizar(db, mac_id, resultado, inicio, fim, origem, duracao_ms, not janela_explicita)
    return resultado


def _gravar(
    db: Session,
    conta: MetaAdsConta,
    campanhas,
    insights,
    inicio: date,
    fim: date,
    conjuntos=(),
    anuncios=(),
    insights_anuncio=(),
) -> int:
    existentes = {
        c.mcgCampanhaExterna: c
        for c in db.execute(
            select(MetaAdsCampanha).where(MetaAdsCampanha.mcgMacId == conta.macId)
        ).scalars()
    }

    def _obter(externa: str, nome: str) -> MetaAdsCampanha:
        camp = existentes.get(externa)
        if camp is None:
            camp = MetaAdsCampanha(
                mcgEmpId=conta.macEmpId, mcgMacId=conta.macId, mcgCampanhaExterna=externa
            )
            db.add(camp)
            existentes[externa] = camp
            camp.mcgNome = nome[:400]
            camp.mcgNomeNormalizado = vinculo.normalizar_nome(nome)[:400]
        return camp

    for c in campanhas:
        camp = _obter(c.id, c.nome)
        camp.mcgNome = c.nome[:400]
        camp.mcgNomeNormalizado = vinculo.normalizar_nome(c.nome)[:400]
        camp.mcgObjetivo = c.objetivo
        camp.mcgStatus = c.status
    for i in insights:
        _obter(i.campanha_id, i.campanha_nome)
    # Campanha so citada no nivel de conjunto/anuncio (ex.: ja excluida): nasce com o id como nome.
    for item in (*conjuntos, *anuncios, *insights_anuncio):
        _obter(item.campanha_id, item.campanha_id)
    db.flush()

    db.execute(
        delete(MetaAdsInsightDiario).where(
            MetaAdsInsightDiario.midMacId == conta.macId,
            MetaAdsInsightDiario.midData >= inicio,
            MetaAdsInsightDiario.midData <= fim,
        )
    )
    # Defensivo: se o Meta repetir campanha x dia, soma em vez de violar a chave unica.
    por_chave: dict[tuple[int, date], MetaAdsInsightDiario] = {}
    for i in insights:
        mcg_id = existentes[i.campanha_id].mcgId
        linha = por_chave.get((mcg_id, i.dia))
        if linha is None:
            linha = MetaAdsInsightDiario(
                midEmpId=conta.macEmpId,
                midMacId=conta.macId,
                midMcgId=mcg_id,
                midData=i.dia,
                midInvestimento=0,
                midImpressoes=0,
                midCliques=0,
                midAlcance=0,
                midLeadsMeta=0,
            )
            por_chave[(mcg_id, i.dia)] = linha
            db.add(linha)
        linha.midInvestimento = float(linha.midInvestimento) + float(i.investimento)
        linha.midImpressoes += i.impressoes
        linha.midCliques += i.cliques
        linha.midAlcance += i.alcance
        linha.midLeadsMeta += i.leads
    db.flush()
    campanha_ids = {externa: camp.mcgId for externa, camp in existentes.items()}
    anuncios_por_externo = _gravar_conjuntos_e_anuncios(
        db, conta, campanha_ids, conjuntos, anuncios, insights_anuncio
    )
    _gravar_insights_anuncio(db, conta, anuncios_por_externo, insights_anuncio, inicio, fim)
    return len(por_chave)


def _gravar_conjuntos_e_anuncios(
    db: Session, conta: MetaAdsConta, campanha_ids: dict[str, int], conjuntos, anuncios, insights
) -> dict[str, MetaAdsAnuncio]:
    """Upsert de conjuntos e anuncios (os que so aparecem nos insights nascem com o nome dali)."""
    conj_existentes = {
        c.mcjConjuntoExterno: c
        for c in db.execute(
            select(MetaAdsConjunto).where(MetaAdsConjunto.mcjMacId == conta.macId)
        ).scalars()
    }
    anu_existentes = {
        a.manAnuncioExterno: a
        for a in db.execute(
            select(MetaAdsAnuncio).where(MetaAdsAnuncio.manMacId == conta.macId)
        ).scalars()
    }

    def _conjunto(externo: str, campanha_externa: str, nome: str | None = None) -> MetaAdsConjunto:
        conj = conj_existentes.get(externo)
        if conj is None:
            conj = MetaAdsConjunto(
                mcjEmpId=conta.macEmpId,
                mcjMacId=conta.macId,
                mcjMcgId=campanha_ids[campanha_externa],
                mcjConjuntoExterno=externo,
                mcjNome=(nome or externo)[:400],
            )
            db.add(conj)
            conj_existentes[externo] = conj
        return conj

    for c in conjuntos:
        conj = _conjunto(c.id, c.campanha_id, c.nome)
        conj.mcjNome = c.nome[:400]
        conj.mcjMcgId = campanha_ids[c.campanha_id]
        conj.mcjStatus = c.status
    for a in (*anuncios, *insights):
        _conjunto(a.conjunto_id, a.campanha_id)
    db.flush()

    def _anuncio(externo: str, conjunto_externo: str, campanha_externa: str, nome: str) -> MetaAdsAnuncio:
        anu = anu_existentes.get(externo)
        if anu is None:
            anu = MetaAdsAnuncio(
                manEmpId=conta.macEmpId,
                manMacId=conta.macId,
                manAnuncioExterno=externo,
                manNome=nome[:400],
            )
            db.add(anu)
            anu_existentes[externo] = anu
        anu.manMcgId = campanha_ids[campanha_externa]
        anu.manMcjId = conj_existentes[conjunto_externo].mcjId
        return anu

    for a in anuncios:
        anu = _anuncio(a.id, a.conjunto_id, a.campanha_id, a.nome)
        anu.manNome = a.nome[:400]
        anu.manStatus = a.status
        anu.manMotivo = a.motivo[:300] if a.motivo else None
        anu.manCriadoEmMeta = a.criado_em
    for i in insights:
        _anuncio(i.anuncio_id, i.conjunto_id, i.campanha_id, i.anuncio_nome)
    # manPrimeiroDia so recua: menor dia com impressao ja visto.
    for i in insights:
        if i.impressoes > 0:
            anu = anu_existentes[i.anuncio_id]
            if anu.manPrimeiroDia is None or i.dia < anu.manPrimeiroDia:
                anu.manPrimeiroDia = i.dia
    db.flush()
    return anu_existentes


def _gravar_insights_anuncio(
    db: Session,
    conta: MetaAdsConta,
    anuncios: dict[str, MetaAdsAnuncio],
    insights,
    inicio: date,
    fim: date,
) -> None:
    db.execute(
        delete(MetaAdsInsightAnuncioDiario).where(
            MetaAdsInsightAnuncioDiario.miaMacId == conta.macId,
            MetaAdsInsightAnuncioDiario.miaData >= inicio,
            MetaAdsInsightAnuncioDiario.miaData <= fim,
        )
    )
    # Defensivo: se o Meta repetir anuncio x dia, soma em vez de violar a chave unica.
    por_chave: dict[tuple[int, date], MetaAdsInsightAnuncioDiario] = {}
    for i in insights:
        man_id = anuncios[i.anuncio_id].manId
        linha = por_chave.get((man_id, i.dia))
        if linha is None:
            linha = MetaAdsInsightAnuncioDiario(
                miaEmpId=conta.macEmpId,
                miaMacId=conta.macId,
                miaManId=man_id,
                miaData=i.dia,
                miaInvestimento=0,
                miaImpressoes=0,
                miaAlcance=0,
                miaCliques=0,
                miaCliquesLink=0,
                miaLeadsMeta=0,
            )
            por_chave[(man_id, i.dia)] = linha
            db.add(linha)
        linha.miaInvestimento = float(linha.miaInvestimento) + float(i.investimento)
        linha.miaImpressoes += i.impressoes
        linha.miaAlcance += i.alcance
        linha.miaCliques += i.cliques
        linha.miaCliquesLink += i.cliques_link
        linha.miaLeadsMeta += i.leads
    db.flush()


def _finalizar(
    db: Session,
    mac_id: int,
    resultado: ResultadoSync,
    inicio: date,
    fim: date,
    origem: str,
    duracao_ms: int,
    marcar_carga_inicial: bool,
) -> None:
    conta = db.get(MetaAdsConta, mac_id)
    conta.macStatus = resultado.status
    conta.macMensagem = resultado.erro[:500] if resultado.erro else None
    conta.macSyncIniciadaEm = None
    if resultado.status == STATUS_OK:
        conta.macUltimaSync = utcnow()
        if marcar_carga_inicial:
            conta.macCargaInicialFeita = True
    db.add(
        MetaAdsSyncLog(
            mslMacId=mac_id,
            mslInicio=inicio,
            mslFim=fim,
            mslOrigem=origem,
            mslStatus=(
                STATUS_ERRO
                if resultado.status in (STATUS_TOKEN_INVALIDO, STATUS_PERMISSAO_EXCESSIVA)
                else resultado.status
            ),
            mslLinhas=resultado.linhas,
            mslLeadsVinculados=resultado.leads_vinculados,
            mslErro=resultado.erro[:500] if resultado.erro else None,
            mslDuracaoMs=duracao_ms,
        )
    )
    db.commit()


def executar_em_sessao_propria(
    mac_id: int, origem: str, inicio: date | None = None, fim: date | None = None
) -> ResultadoSync:
    """Para BackgroundTasks e worker: a sessao da requisicao ja foi fechada."""
    from ...database import SessionLocal

    with SessionLocal() as db:
        return sincronizar_conta(db, mac_id, origem=origem, inicio=inicio, fim=fim)


def contas_da_rodada_diaria(db: Session) -> list[int]:
    return list(
        db.execute(
            select(MetaAdsConta.macId)
            .where(
                MetaAdsConta.macAtivo.is_(True),
                MetaAdsConta.macStatus.notin_([STATUS_TOKEN_INVALIDO, STATUS_PERMISSAO_EXCESSIVA]),
            )
            .order_by(MetaAdsConta.macId)
        ).scalars()
    )


def sincronizar_todas_agendadas() -> int:
    """Rodada diaria. Uma conta com problema nao impede as demais. Devolve quantas rodaram."""
    from ...database import SessionLocal

    with SessionLocal() as db:
        ids = contas_da_rodada_diaria(db)
    rodadas = 0
    for mac_id in ids:
        try:
            with SessionLocal() as db:
                if reivindicar(db, mac_id):
                    sincronizar_conta(db, mac_id, origem="agendada")
                    rodadas += 1
        except Exception:
            logger.exception("Falha na rodada diaria Meta Ads da conta %s", mac_id)
    return rodadas
