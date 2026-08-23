"""
Ingestao de leads vindos de integracoes externas.

Um lead NAO e uma entidade propria neste CRM: ele nasce como `oportunidade` na etapa
"Novo Lead" do pipeline default.

Este modulo NAO reusa oportunidade_service.create_oportunidade / update_oportunidade
de proposito: aquelas funcoes fazem commit proprio, e passar o lead por elas produziria
tres commits (oportunidade, historico, evento de webhook) com estado rasgado se o
processo morresse no meio. Aqui tudo cai num commit so.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.tempo import utcnow
from ..database import engine
from ..exceptions import BadRequestError, ConflictError
from ..models.como_conheceu import ComoConheceu
from ..models.etapa_kanban import EtapaKanban
from ..models.oportunidade import Oportunidade
from ..models.oportunidade_historico import OportunidadeHistorico
from ..models.usuario import Usuario
from . import webhook_emitter
from .lead_normalizacao import (
    normalizar_email,
    normalizar_telefone,
    origem_aceitavel,
    rotular_origem,
    slugificar,
    variantes_telefone,
)

logger = logging.getLogger(__name__)

STATUS_FECHADOS = ("ganho", "perdido", "stand-by")
TIMEOUT_LOCK_SEGUNDOS = 10

# Campos que a integracao jamais toca: sao trabalho humano.
CAMPOS_INTOCAVEIS = frozenset(
    {
        "opoUsuResponsavelId",
        "opoEtkId",
        "opoStatusFechamento",
        "opoDataFechamento",
        "opoValorFechado",
        "opoFechadoRecorrencia",
        "opoLeadScore",
        "opoTemperatura",
        "opoProId",
        "opoMcaId",
        "opoAtivo",
        "opoDataRecebimento",
        "opoComentarios",
        "opoDoresMotivadores",
    }
)


# ---------------------------------------------------------------------------------
# Funcoes puras -- e onde mora a logica que importa, e o que os testes exercitam.
# ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class DecisaoUpsert:
    acao: Literal["criar", "atualizar"]
    opo_id: Optional[int] = None
    deduped_by: Optional[Literal["external_id", "email", "phone"]] = None
    ciclo_anterior_id: Optional[int] = None


def decidir_acao(
    match_external: Optional[int],
    match_aberto: Optional[tuple],
    match_fechado: Optional[int],
) -> DecisaoUpsert:
    """
    A regra de dedup, isolada de qualquer acesso a banco.

    `external_id` tem precedencia por ser o sinal mais forte -- e literalmente a mesma
    linha da planilha voltando. Um match apenas com oportunidade FECHADA nunca vira
    atualizacao: ciclo encerrado e ciclo encerrado, abre-se uma nova apontando para a
    anterior.
    """
    if match_external is not None:
        return DecisaoUpsert("atualizar", match_external, "external_id", None)
    if match_aberto is not None:
        opo_id, motivo = match_aberto
        return DecisaoUpsert("atualizar", opo_id, motivo, None)
    return DecisaoUpsert("criar", None, None, match_fechado)


def derivar_titulo(
    name: Optional[str],
    company: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    source: str,
    external_id: Optional[str] = None,
) -> str:
    """opoTitulo e NOT NULL. Nunca devolve vazio, pois e-mail ou telefone e obrigatorio."""
    nome = (name or "").strip()
    empresa = (company or "").strip()
    if nome and empresa:
        titulo = nome + " - " + empresa
    elif nome:
        titulo = nome
    elif empresa:
        titulo = empresa
    elif (email or "").strip():
        titulo = email.strip().split("@")[0].replace(".", " ").title()
    elif (phone or "").strip():
        titulo = phone.strip()
    else:
        titulo = ("Lead " + source + " " + (external_id or "")).strip()
    return titulo.strip()[:300]


def aplicar_merge(existente: dict, payload: Any) -> tuple:
    """
    Decide o que muda numa oportunidade ja existente. Devolve (atributos, observacoes).

    Tres politicas:
      - sobrescreve sempre (se o novo valor nao for vazio): rastreio de origem e UTM;
      - preenche so se estiver vazio: dados de contato -- nunca apaga o que um humano
        digitou;
      - nao toca: etapa, responsavel, status, valores, score. Ver CAMPOS_INTOCAVEIS.
    """
    mudancas: dict = {}
    observacoes: list = []

    def _novo(valor):
        if isinstance(valor, str):
            limpo = valor.strip()
            return limpo or None
        return valor if valor is not None else None

    for campo, valor in (
        ("opoOrigemSistema", _novo(getattr(payload, "source", None))),
        ("opoOrigemExternalId", _novo(getattr(payload, "external_id", None))),
        ("opoUtmSource", _novo(getattr(payload, "utm_source", None))),
        ("opoUtmMedium", _novo(getattr(payload, "utm_medium", None))),
        ("opoUtmCampaign", _novo(getattr(payload, "utm_campaign", None))),
        ("opoUtmContent", _novo(getattr(payload, "utm_content", None))),
        ("opoUtmTerm", _novo(getattr(payload, "utm_term", None))),
    ):
        if valor is not None and existente.get(campo) != valor:
            mudancas[campo] = valor

    for campo, valor in (
        ("opoNomeContato", _novo(getattr(payload, "name", None))),
        ("opoEmpresaContato", _novo(getattr(payload, "company", None))),
    ):
        if valor is not None and not (existente.get(campo) or "").strip():
            mudancas[campo] = valor

    email_novo = _novo(getattr(payload, "email", None))
    email_norm = normalizar_email(email_novo)
    if email_novo:
        atual = (existente.get("opoEmail") or "").strip()
        if not atual:
            mudancas["opoEmail"] = email_novo
            mudancas["opoEmailNormalizado"] = email_norm
        elif email_norm and normalizar_email(atual) != email_norm:
            observacoes.append(
                "E-mail informado pela integracao difere do cadastrado: "
                + email_novo
                + " (mantido "
                + atual
                + ")."
            )

    fone_novo = _novo(getattr(payload, "phone", None))
    fone_norm = normalizar_telefone(fone_novo)
    if fone_novo:
        atual = (existente.get("opoTelefone") or "").strip()
        if not atual:
            mudancas["opoTelefone"] = fone_novo
            mudancas["opoTelefoneNormalizado"] = fone_norm
        elif fone_norm and normalizar_telefone(atual) != fone_norm:
            observacoes.append(
                "Telefone informado pela integracao difere do cadastrado: "
                + fone_novo
                + " (mantido "
                + atual
                + ")."
            )

    valor_novo = getattr(payload, "value", None)
    if valor_novo is not None and existente.get("opoValorOportunidade") in (None, 0):
        mudancas["opoValorOportunidade"] = valor_novo

    # Rede de seguranca: se alguem acrescentar um campo acima por engano, ele nao passa.
    for proibido in CAMPOS_INTOCAVEIS:
        mudancas.pop(proibido, None)

    return mudancas, observacoes


def resumo_para_historico(payload: Any) -> str:
    origem = getattr(payload, "source", None) or "?"
    partes = ['Lead recebido via integracao (origem "' + str(origem) + '")']
    if getattr(payload, "external_id", None):
        partes.append("external_id=" + str(payload.external_id))
    if getattr(payload, "utm_campaign", None):
        partes.append("campanha=" + str(payload.utm_campaign))
    return ". ".join(partes) + "."


def chave_de_lock(emp_id: int, email_norm: Optional[str], fone_norm: Optional[str]) -> str:
    """
    Nome do lock nomeado do MySQL, dentro do limite de 64 caracteres.

    Serializa por e-mail quando ha e-mail; caso contrario pelo telefone canonico.
    """
    base = email_norm or fone_norm or "sem-contato"
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:32]
    return "sdcrm_lead_" + str(emp_id) + "_" + digest


# ---------------------------------------------------------------------------------
# Acesso a banco
# ---------------------------------------------------------------------------------


def resolver_etapa_novo_lead(db: Session, emp_id: int) -> Optional[int]:
    """
    Etapa em que o lead entra.

    Casa pelo nome configurado primeiro e, se nao achar, usa a de menor ordem: o nome
    e editavel pelo usuario na tela de Etapas, a ordem e a semantica de verdade.
    """
    etapas = list(
        db.scalars(
            select(EtapaKanban)
            .where(
                EtapaKanban.etkEmpId == emp_id,
                EtapaKanban.etkPipeline == settings.LEADS_PIPELINE_PADRAO,
                EtapaKanban.etkAtivo.is_(True),
            )
            .order_by(EtapaKanban.etkOrdem.asc(), EtapaKanban.etkId.asc())
        ).all()
    )
    if not etapas:
        return None
    alvo = slugificar(settings.LEADS_ETAPA_PADRAO_NOME)
    for etapa in etapas:
        if slugificar(etapa.etkNome) == alvo:
            return etapa.etkId
    return etapas[0].etkId


def resolver_origem(db: Session, emp_id: int, source: str) -> Optional[int]:
    """
    Mapeia o `source` para como_conheceu.ccoId, criando a origem se necessario.

    A comparacao roda em Python sobre a lista da empresa (dezenas de linhas) para nao
    depender de collation e acentuacao do MySQL.
    """
    alvo = slugificar(source)
    if not alvo:
        return None
    origens = list(db.scalars(select(ComoConheceu).where(ComoConheceu.ccoEmpId == emp_id)).all())
    for origem in origens:
        if slugificar(origem.ccoNome) == alvo:
            return origem.ccoId

    if not settings.INTEGRACAO_AUTOCRIAR_ORIGEM or not origem_aceitavel(alvo):
        return None

    nova = ComoConheceu(ccoEmpId=emp_id, ccoNome=rotular_origem(alvo), ccoGrupo="Integracao")
    db.add(nova)
    db.flush()
    return nova.ccoId


def _match_external(db: Session, emp_id: int, source: str, external_id: str) -> Optional[int]:
    return db.scalar(
        select(Oportunidade.opoId)
        .where(
            Oportunidade.opoEmpId == emp_id,
            Oportunidade.opoAtivo.is_(True),
            Oportunidade.opoStatusFechamento.is_(None),
            Oportunidade.opoOrigemSistema == source,
            Oportunidade.opoOrigemExternalId == external_id,
        )
        .order_by(Oportunidade.opoDataCriacao.desc())
        .limit(1)
    )


def _condicoes_contato(email_norm: Optional[str], fones: set):
    """O OR do dedup so com os campos informados -- um IN () vazio e erro de sintaxe."""
    condicoes = []
    if email_norm:
        condicoes.append(Oportunidade.opoEmailNormalizado == email_norm)
    if fones:
        condicoes.append(Oportunidade.opoTelefoneNormalizado.in_(sorted(fones)))
    return condicoes


def _match_contato(
    db: Session, emp_id: int, email_norm: Optional[str], fones: set, aberta: bool
) -> Optional[tuple]:
    condicoes = _condicoes_contato(email_norm, fones)
    if not condicoes:
        return None

    stmt = select(
        Oportunidade.opoId,
        Oportunidade.opoEmailNormalizado,
        Oportunidade.opoTelefoneNormalizado,
    ).where(Oportunidade.opoEmpId == emp_id, or_(*condicoes))

    if aberta:
        stmt = stmt.where(
            Oportunidade.opoAtivo.is_(True), Oportunidade.opoStatusFechamento.is_(None)
        )
    else:
        stmt = stmt.where(
            or_(
                Oportunidade.opoAtivo.is_(False),
                Oportunidade.opoStatusFechamento.in_(STATUS_FECHADOS),
            )
        )

    linha = db.execute(stmt.order_by(Oportunidade.opoDataCriacao.desc()).limit(1)).first()
    if linha is None:
        return None
    opo_id, email_row, _fone_row = linha
    motivo = "email" if (email_norm and email_row == email_norm) else "phone"
    return opo_id, motivo


def _resolver_responsavel(db: Session, owner_email: Optional[str]) -> Optional[int]:
    email_norm = normalizar_email(owner_email)
    if not email_norm:
        return None
    return db.scalar(
        select(Usuario.usuId).where(Usuario.usuEmail == email_norm, Usuario.usuAtivo.is_(True))
    )


def _historico(db: Session, oportunidade: Oportunidade, conteudo: str) -> None:
    """
    Espelha oportunidade_service._registrar_historico_automatico, mas sem commit --
    quem chama controla a transacao.
    """
    registro = utcnow()
    db.add(
        OportunidadeHistorico(
            ophEmpId=oportunidade.opoEmpId,
            ophOpoId=oportunidade.opoId,
            ophUsuId=None,
            ophDataRegistro=registro,
            ophConteudo=conteudo,
        )
    )
    oportunidade.opoDataUltimoContato = registro.date()


# ---------------------------------------------------------------------------------
# Orquestracao
# ---------------------------------------------------------------------------------


@dataclass
class ResultadoIntake:
    status: str
    opo_id: int
    deduped_by: Optional[str] = None
    ciclo_anterior_id: Optional[int] = None
    avisos: Optional[list] = None


def processar_lead(
    db: Session, *, emp_id: int, ich_id: Optional[int], payload: Any
) -> ResultadoIntake:
    """
    Recebe um lead e devolve o resultado do upsert.

    A secao critica roda dentro de um lock nomeado do MySQL. Um SELECT ... FOR UPDATE
    nao serviria: ele trava as linhas RETORNADAS, e a corrida acontece justamente
    quando a consulta de dedup nao retorna nada.
    """
    email_norm = normalizar_email(getattr(payload, "email", None))
    fone_norm = normalizar_telefone(getattr(payload, "phone", None))
    fones = variantes_telefone(fone_norm)

    nome_lock = chave_de_lock(emp_id, email_norm, fone_norm)

    # Conexao propria e obrigatoria: um commit na Session devolve a conexao ao pool e
    # o lock vazaria para uma conexao reaproveitada por outra requisicao.
    with engine.connect() as conexao_lock:
        obteve = conexao_lock.exec_driver_sql(
            "SELECT GET_LOCK(%s, %s)", (nome_lock, TIMEOUT_LOCK_SEGUNDOS)
        ).scalar()
        if not obteve:
            raise ConflictError("Lead em processamento; tente novamente em instantes.")
        try:
            return _processar_com_lock(
                db,
                emp_id=emp_id,
                ich_id=ich_id,
                payload=payload,
                email_norm=email_norm,
                fone_norm=fone_norm,
                fones=fones,
            )
        finally:
            conexao_lock.exec_driver_sql("SELECT RELEASE_LOCK(%s)", (nome_lock,))


def _processar_com_lock(
    db: Session,
    *,
    emp_id: int,
    ich_id: Optional[int],
    payload: Any,
    email_norm: Optional[str],
    fone_norm: Optional[str],
    fones: set,
) -> ResultadoIntake:
    external_id = (getattr(payload, "external_id", None) or "").strip() or None
    source = payload.source.strip()

    match_ext = _match_external(db, emp_id, source, external_id) if external_id else None
    match_aberto = None
    match_fechado = None
    if match_ext is None:
        match_aberto = _match_contato(db, emp_id, email_norm, fones, aberta=True)
        if match_aberto is None:
            fechado = _match_contato(db, emp_id, email_norm, fones, aberta=False)
            match_fechado = fechado[0] if fechado else None

    decisao = decidir_acao(match_ext, match_aberto, match_fechado)

    if decisao.acao == "atualizar":
        return _atualizar(db, decisao, emp_id=emp_id, ich_id=ich_id, payload=payload)
    return _criar(
        db,
        decisao,
        emp_id=emp_id,
        ich_id=ich_id,
        payload=payload,
        email_norm=email_norm,
        fone_norm=fone_norm,
    )


def _criar(
    db: Session,
    decisao: DecisaoUpsert,
    *,
    emp_id: int,
    ich_id: Optional[int],
    payload: Any,
    email_norm: Optional[str],
    fone_norm: Optional[str],
) -> ResultadoIntake:
    avisos: list = []
    etapa_id = resolver_etapa_novo_lead(db, emp_id)
    if etapa_id is None:
        # Nao rejeitamos o lead por isso: perder um lead pago e pior que um card sem
        # etapa. O aviso aparece no log de integracao para alguem corrigir o cadastro.
        avisos.append(
            "Empresa sem etapa ativa no pipeline "
            + settings.LEADS_PIPELINE_PADRAO
            + "; oportunidade criada sem etapa."
        )

    oportunidade = Oportunidade(
        opoEmpId=emp_id,
        opoTitulo=derivar_titulo(
            getattr(payload, "name", None),
            getattr(payload, "company", None),
            getattr(payload, "email", None),
            getattr(payload, "phone", None),
            payload.source,
            getattr(payload, "external_id", None),
        ),
        opoNomeContato=getattr(payload, "name", None),
        opoEmpresaContato=getattr(payload, "company", None),
        opoEmail=getattr(payload, "email", None),
        opoEmailNormalizado=email_norm,
        opoTelefone=getattr(payload, "phone", None),
        opoTelefoneNormalizado=fone_norm,
        opoEtkId=etapa_id,
        opoCcoId=resolver_origem(db, emp_id, payload.source),
        opoUsuResponsavelId=_resolver_responsavel(db, getattr(payload, "owner_email", None)),
        opoOrigemSistema=payload.source.strip(),
        opoOrigemExternalId=(getattr(payload, "external_id", None) or None),
        opoUtmSource=getattr(payload, "utm_source", None),
        opoUtmMedium=getattr(payload, "utm_medium", None),
        opoUtmCampaign=getattr(payload, "utm_campaign", None),
        opoUtmContent=getattr(payload, "utm_content", None),
        opoUtmTerm=getattr(payload, "utm_term", None),
        opoValorOportunidade=getattr(payload, "value", None),
        opoComentarios=getattr(payload, "notes", None),
        opoIchId=ich_id,
        opoOpoAnteriorId=decisao.ciclo_anterior_id,
        opoDataRecebimento=date.today(),
    )
    db.add(oportunidade)
    db.flush()

    conteudo = resumo_para_historico(payload)
    if decisao.ciclo_anterior_id:
        anterior = db.get(Oportunidade, decisao.ciclo_anterior_id)
        detalhe = "encerrada"
        if anterior is not None:
            detalhe = anterior.opoStatusFechamento or (
                "inativa" if not anterior.opoAtivo else "encerrada"
            )
        conteudo += (
            " Ja houve um ciclo anterior para este contato: oportunidade #"
            + str(decisao.ciclo_anterior_id)
            + " ("
            + str(detalhe)
            + ")."
        )
        if anterior is not None:
            _historico(
                db,
                anterior,
                "Novo ciclo aberto para este contato: oportunidade #"
                + str(oportunidade.opoId)
                + ".",
            )
    _historico(db, oportunidade, conteudo)

    # Antes do commit, para o evento cair na MESMA transacao do lead.
    # lead.created e nao deal.created: esta linha nasceu pela integracao.
    webhook_emitter.enfileirar(
        db,
        tipo="lead.created",
        emp_id=emp_id,
        oportunidade=oportunidade,
        origem="api",
        chave_idempotencia=(
            "lead.created:" + str(oportunidade.opoId) if oportunidade.opoId else None
        ),
    )

    db.commit()
    db.refresh(oportunidade)
    return ResultadoIntake(
        status="created",
        opo_id=oportunidade.opoId,
        deduped_by=None,
        ciclo_anterior_id=decisao.ciclo_anterior_id,
        avisos=avisos or None,
    )


def _atualizar(
    db: Session,
    decisao: DecisaoUpsert,
    *,
    emp_id: int,
    ich_id: Optional[int],
    payload: Any,
) -> ResultadoIntake:
    oportunidade = db.get(Oportunidade, decisao.opo_id)
    if oportunidade is None or oportunidade.opoEmpId != emp_id:
        raise BadRequestError("Oportunidade alvo do dedup nao pertence a empresa da chave.")

    existente = {
        coluna: getattr(oportunidade, coluna) for coluna in Oportunidade.__table__.columns.keys()
    }
    mudancas, observacoes = aplicar_merge(existente, payload)
    if ich_id is not None:
        mudancas["opoIchId"] = ich_id

    if not oportunidade.opoCcoId:
        cco_id = resolver_origem(db, emp_id, payload.source)
        if cco_id:
            mudancas["opoCcoId"] = cco_id

    for campo, valor in mudancas.items():
        setattr(oportunidade, campo, valor)

    conteudo = resumo_para_historico(payload)
    if getattr(payload, "notes", None):
        conteudo += " Observacao: " + str(payload.notes)[:1000]
    for observacao in observacoes:
        conteudo += " " + observacao
    _historico(db, oportunidade, conteudo)

    webhook_emitter.enfileirar(
        db, tipo="lead.updated", emp_id=emp_id, oportunidade=oportunidade, origem="api"
    )

    db.add(oportunidade)
    db.commit()
    db.refresh(oportunidade)
    return ResultadoIntake(
        status="updated",
        opo_id=oportunidade.opoId,
        deduped_by=decisao.deduped_by,
        ciclo_anterior_id=None,
        avisos=observacoes or None,
    )
