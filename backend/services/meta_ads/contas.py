"""Cadastro das contas do Meta Ads de uma empresa, teste de conexao e log de sincronizacao."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ...core.cripto import cifrar, decifrar
from ...exceptions import BadRequestError, ConflictError, NotFoundError
from ...models.como_conheceu import ComoConheceu
from ...models.meta_ads_conta import (
    STATUS_PENDENTE,
    STATUS_SINCRONIZANDO,
    STATUS_TOKEN_INVALIDO,
    MetaAdsConta,
)
from ...models.meta_ads_conta_origem import MetaAdsContaOrigem
from ...models.meta_ads_sync_log import MetaAdsSyncLog
from ...schemas.meta_ads import (
    MetaAdsContaCreate,
    MetaAdsContaListResponse,
    MetaAdsContaResponse,
    MetaAdsContaUpdate,
    MetaAdsSyncLogListResponse,
    MetaAdsSyncLogResponse,
    MetaAdsTesteResponse,
)
from .cliente_graph import ClienteGraph, MetaGraphErro, normalizar_conta


def _origens(db: Session, mac_id: int) -> list[int]:
    return sorted(
        db.execute(
            select(MetaAdsContaOrigem.mcoCcoId).where(MetaAdsContaOrigem.mcoMacId == mac_id)
        ).scalars()
    )


def _resposta(db: Session, conta: MetaAdsConta) -> MetaAdsContaResponse:
    return MetaAdsContaResponse(
        macId=conta.macId,
        macNome=conta.macNome,
        macContaExterna=conta.macContaExterna,
        macTokenFinal=conta.macTokenFinal,
        macMoeda=conta.macMoeda,
        macFuso=conta.macFuso,
        macStatus=conta.macStatus,
        macMensagem=conta.macMensagem,
        macUltimaSync=conta.macUltimaSync,
        macCargaInicialFeita=conta.macCargaInicialFeita,
        macAtivo=conta.macAtivo,
        origens=_origens(db, conta.macId),
    )


def obter_conta_da_empresa(db: Session, emp_id: int, mac_id: int) -> MetaAdsConta:
    conta = db.get(MetaAdsConta, mac_id)
    if conta is None or conta.macEmpId != emp_id:
        raise NotFoundError("Conta de anúncios não encontrada")
    return conta


def _validar_origens(db: Session, emp_id: int, ids: list[int]) -> list[int]:
    unicos = sorted(set(ids))
    if not unicos:
        return []
    encontrados = db.execute(
        select(func.count(ComoConheceu.ccoId)).where(
            ComoConheceu.ccoEmpId == emp_id, ComoConheceu.ccoId.in_(unicos)
        )
    ).scalar_one()
    if encontrados != len(unicos):
        raise BadRequestError("Origem inválida para esta empresa")
    return unicos


def _definir_origens(db: Session, conta: MetaAdsConta, ids: list[int]) -> None:
    db.execute(delete(MetaAdsContaOrigem).where(MetaAdsContaOrigem.mcoMacId == conta.macId))
    for cco_id in ids:
        db.add(MetaAdsContaOrigem(mcoMacId=conta.macId, mcoCcoId=cco_id))


def listar_contas(db: Session, emp_id: int) -> MetaAdsContaListResponse:
    lista = db.execute(
        select(MetaAdsConta).where(MetaAdsConta.macEmpId == emp_id).order_by(MetaAdsConta.macNome)
    ).scalars()
    return MetaAdsContaListResponse(items=[_resposta(db, c) for c in lista])


def criar_conta(db: Session, emp_id: int, data: MetaAdsContaCreate) -> MetaAdsContaResponse:
    try:
        act = normalizar_conta(data.macContaExterna)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc
    origens = _validar_origens(db, emp_id, data.origens)
    existe = db.execute(
        select(MetaAdsConta.macId).where(
            MetaAdsConta.macEmpId == emp_id, MetaAdsConta.macContaExterna == act
        )
    ).first()
    if existe:
        raise ConflictError("Esta conta de anúncios já está cadastrada nesta empresa")
    conta = MetaAdsConta(
        macEmpId=emp_id,
        macNome=data.macNome.strip(),
        macContaExterna=act,
        macToken=cifrar(data.token),
        macTokenFinal=data.token[-4:],
        macStatus=STATUS_PENDENTE,
    )
    db.add(conta)
    db.flush()
    _definir_origens(db, conta, origens)
    db.commit()
    return _resposta(db, conta)


def atualizar_conta(
    db: Session, emp_id: int, mac_id: int, data: MetaAdsContaUpdate
) -> MetaAdsContaResponse:
    conta = obter_conta_da_empresa(db, emp_id, mac_id)
    if data.macNome is not None:
        conta.macNome = data.macNome.strip()
    if data.token is not None:
        conta.macToken = cifrar(data.token)
        conta.macTokenFinal = data.token[-4:]
        if conta.macStatus != STATUS_SINCRONIZANDO:
            # Durante uma sync em andamento a trava (status/inicio) nao pode ser liberada aqui.
            conta.macStatus = STATUS_PENDENTE
            conta.macMensagem = None
    if data.origens is not None:
        _definir_origens(db, conta, _validar_origens(db, emp_id, data.origens))
    if data.macAtivo is not None:
        conta.macAtivo = data.macAtivo
    db.commit()
    return _resposta(db, conta)


def testar_conta(
    db: Session, emp_id: int, mac_id: int, fabrica_cliente=ClienteGraph
) -> MetaAdsTesteResponse:
    conta = obter_conta_da_empresa(db, emp_id, mac_id)
    token = decifrar(conta.macToken)
    if token is None:
        return MetaAdsTesteResponse(
            ok=False, mensagem="Token ilegível (a chave de criptografia mudou) — cadastre o token de novo."
        )
    try:
        with fabrica_cliente(token, esperas=()) as cliente:
            info = cliente.obter_conta(conta.macContaExterna)
    except MetaGraphErro as exc:
        return MetaAdsTesteResponse(ok=False, mensagem=exc.mensagem)
    conta.macMoeda = info.moeda
    conta.macFuso = info.fuso
    if conta.macStatus == STATUS_TOKEN_INVALIDO:
        conta.macStatus = STATUS_PENDENTE
        conta.macMensagem = None
    db.commit()
    return MetaAdsTesteResponse(ok=True, nome=info.nome, moeda=info.moeda, fuso=info.fuso)


def listar_logs(db: Session, emp_id: int, mac_id: int, limite: int = 30) -> MetaAdsSyncLogListResponse:
    obter_conta_da_empresa(db, emp_id, mac_id)
    linhas = db.execute(
        select(MetaAdsSyncLog)
        .where(MetaAdsSyncLog.mslMacId == mac_id)
        .order_by(MetaAdsSyncLog.mslId.desc())
        .limit(limite)
    ).scalars()
    return MetaAdsSyncLogListResponse(items=[MetaAdsSyncLogResponse.model_validate(l) for l in linhas])


def ids_contas_ativas(db: Session, emp_id: int, mac_id: int | None) -> list[int]:
    stmt = select(MetaAdsConta.macId).where(
        MetaAdsConta.macEmpId == emp_id, MetaAdsConta.macAtivo.is_(True)
    )
    if mac_id is not None:
        stmt = stmt.where(MetaAdsConta.macId == mac_id)
    return list(db.execute(stmt.order_by(MetaAdsConta.macId)).scalars())
