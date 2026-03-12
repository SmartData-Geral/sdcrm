from datetime import date, datetime, timezone
from typing import Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..exceptions import NotFoundError
from ..models.etapa_kanban import EtapaKanban
from ..models.oportunidade import Oportunidade
from ..models.oportunidade_historico import OportunidadeHistorico
from ..schemas.oportunidade import (
    OportunidadeCreate,
    OportunidadeLeadScoreRequest,
    OportunidadeListResponse,
    OportunidadeMoverEtapaRequest,
    OportunidadeResponse,
    OportunidadeStandByRequest,
    OportunidadeTemperaturaRequest,
    OportunidadeUpdate,
)


def _registrar_historico_automatico(db: Session, oportunidade: Oportunidade, conteudo: str) -> None:
    data_registro = datetime.now(timezone.utc)
    historico = OportunidadeHistorico(
        ophEmpId=oportunidade.opoEmpId,
        ophOpoId=oportunidade.opoId,
        ophUsuId=None,
        ophDataRegistro=data_registro,
        ophConteudo=conteudo,
    )
    oportunidade.opoDataUltimoContato = data_registro.date()
    db.add(historico)


def _get_nome_etapa(db: Session, etapa_id: int | None, company_id: Optional[int]) -> str:
    if etapa_id is None:
        return "Sem etapa"
    stmt = select(EtapaKanban.etkNome).where(EtapaKanban.etkId == etapa_id)
    if company_id is not None:
        stmt = stmt.where(EtapaKanban.etkEmpId == company_id)
    nome = db.scalar(stmt)
    return nome or f"Etapa #{etapa_id}"


def _reativar_standby_vencidos(db: Session, oportunidades: list[Oportunidade]) -> bool:
    today = date.today()
    houve_alteracao = False
    for oportunidade in oportunidades:
        data_retorno = oportunidade.opoDataUltimoContato
        if oportunidade.opoStatusFechamento != "stand-by" or data_retorno is None:
            continue
        if data_retorno > today:
            continue
        oportunidade.opoStatusFechamento = None
        oportunidade.opoDataFechamento = None
        _registrar_historico_automatico(
            db,
            oportunidade,
            'Retorno automático do stand-by: oportunidade voltou para o funil.',
        )
        db.add(oportunidade)
        houve_alteracao = True
    return houve_alteracao


def list_oportunidades(
    db: Session,
    company_id: Optional[int] = None,
    titulo: Optional[str] = None,
    status: Literal["ativos", "inativos", "todos"] = "ativos",
    etapa_id: Optional[int] = None,
    responsavel_id: Optional[int] = None,
    pro_id: Optional[int] = None,
    data_ultimo_contato_inicio: Optional[date] = None,
    data_ultimo_contato_fim: Optional[date] = None,
    status_fechamento: Optional[Literal["ativo", "ganho", "perdido", "stand-by"]] = None,
    page: int = 1,
    page_size: int = 20,
) -> OportunidadeListResponse:
    stmt = select(Oportunidade)
    if company_id is not None:
        stmt = stmt.where(Oportunidade.opoEmpId == company_id)
    if titulo:
        stmt = stmt.where(Oportunidade.opoTitulo.ilike(f"%{titulo}%"))
    if status == "ativos":
        stmt = stmt.where(Oportunidade.opoAtivo.is_(True))
    elif status == "inativos":
        stmt = stmt.where(Oportunidade.opoAtivo.is_(False))
    if etapa_id is not None:
        stmt = stmt.where(Oportunidade.opoEtkId == etapa_id)
    if responsavel_id is not None:
        stmt = stmt.where(Oportunidade.opoUsuResponsavelId == responsavel_id)
    if pro_id is not None:
        stmt = stmt.where(Oportunidade.opoProId == pro_id)
    if data_ultimo_contato_inicio is not None:
        stmt = stmt.where(Oportunidade.opoDataUltimoContato >= data_ultimo_contato_inicio)
    if data_ultimo_contato_fim is not None:
        stmt = stmt.where(Oportunidade.opoDataUltimoContato <= data_ultimo_contato_fim)
    if status_fechamento == "ativo":
        stmt = stmt.where(Oportunidade.opoStatusFechamento.is_(None))
    elif status_fechamento == "ganho":
        stmt = stmt.where(Oportunidade.opoStatusFechamento == "ganho")
    elif status_fechamento == "perdido":
        stmt = stmt.where(Oportunidade.opoStatusFechamento == "perdido")
    elif status_fechamento == "stand-by":
        stmt = stmt.where(Oportunidade.opoStatusFechamento == "stand-by")
    stmt = stmt.order_by(Oportunidade.opoDataCriacao.desc())
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(total_stmt) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).all()
    if _reativar_standby_vencidos(db, items):
        db.commit()
    return OportunidadeListResponse(
        items=[OportunidadeResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_oportunidade(db: Session, opo_id: int, company_id: Optional[int] = None) -> Oportunidade:
    stmt = select(Oportunidade).where(Oportunidade.opoId == opo_id)
    if company_id is not None:
        stmt = stmt.where(Oportunidade.opoEmpId == company_id)
    row = db.scalars(stmt).first()
    if row is None:
        raise NotFoundError("Oportunidade não encontrada")
    if _reativar_standby_vencidos(db, [row]):
        db.commit()
        db.refresh(row)
    return row


def create_oportunidade(
    db: Session,
    data: OportunidadeCreate,
    company_id: Optional[int] = None,
) -> OportunidadeResponse:
    obj = Oportunidade(opoEmpId=company_id, **data.model_dump())
    db.add(obj)
    db.flush()
    _registrar_historico_automatico(db, obj, "Oportunidade criada.")
    db.commit()
    db.refresh(obj)
    return OportunidadeResponse.model_validate(obj)


def update_oportunidade(
    db: Session,
    opo_id: int,
    data: OportunidadeUpdate,
    company_id: Optional[int] = None,
) -> OportunidadeResponse:
    obj = get_oportunidade(db, opo_id, company_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return OportunidadeResponse.model_validate(obj)


def set_oportunidade_status_fechamento(
    db: Session,
    opo_id: int,
    status: str,
    company_id: Optional[int] = None,
) -> OportunidadeResponse:
    obj = get_oportunidade(db, opo_id, company_id)
    status_anterior = obj.opoStatusFechamento
    obj.opoStatusFechamento = status
    obj.opoDataFechamento = date.today()
    if status_anterior != status:
        _registrar_historico_automatico(
            db,
            obj,
            f'Status alterado para "{status}".',
        )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return OportunidadeResponse.model_validate(obj)


def set_oportunidade_stand_by(
    db: Session,
    opo_id: int,
    data: OportunidadeStandByRequest,
    company_id: Optional[int] = None,
) -> OportunidadeResponse:
    obj = get_oportunidade(db, opo_id, company_id)
    data_retorno = data.opoDataUltimoContato
    obj.opoStatusFechamento = "stand-by"
    obj.opoDataFechamento = date.today()
    obj.opoDataUltimoContato = data_retorno
    _registrar_historico_automatico(
        db,
        obj,
        f'Oportunidade em stand-by até {data_retorno.strftime("%d/%m/%Y")}.',
    )
    obj.opoDataUltimoContato = data_retorno
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return OportunidadeResponse.model_validate(obj)


def mover_etapa(
    db: Session,
    opo_id: int,
    data: OportunidadeMoverEtapaRequest,
    company_id: Optional[int] = None,
) -> OportunidadeResponse:
    obj = get_oportunidade(db, opo_id, company_id)
    etapa_anterior = obj.opoEtkId
    obj.opoEtkId = data.opoEtkId
    if etapa_anterior != data.opoEtkId:
        nome_etapa_anterior = _get_nome_etapa(db, etapa_anterior, company_id)
        nome_etapa_nova = _get_nome_etapa(db, data.opoEtkId, company_id)
        _registrar_historico_automatico(
            db,
            obj,
            f'Etapa alterada de "{nome_etapa_anterior}" para "{nome_etapa_nova}".',
        )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return OportunidadeResponse.model_validate(obj)


def set_lead_score(
    db: Session,
    opo_id: int,
    data: OportunidadeLeadScoreRequest,
    company_id: Optional[int] = None,
) -> OportunidadeResponse:
    obj = get_oportunidade(db, opo_id, company_id)
    obj.opoLeadScore = data.opoLeadScore
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return OportunidadeResponse.model_validate(obj)


def set_temperatura(
    db: Session,
    opo_id: int,
    data: OportunidadeTemperaturaRequest,
    company_id: Optional[int] = None,
) -> OportunidadeResponse:
    obj = get_oportunidade(db, opo_id, company_id)
    obj.opoTemperatura = data.opoTemperatura
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return OportunidadeResponse.model_validate(obj)


def set_reuniao_confirmada(
    db: Session,
    opo_id: int,
    confirmada: bool,
    company_id: Optional[int] = None,
) -> OportunidadeResponse:
    obj = get_oportunidade(db, opo_id, company_id)
    obj.opoReuniaoConfirmada = confirmada
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return OportunidadeResponse.model_validate(obj)


def set_proposta_enviada(
    db: Session,
    opo_id: int,
    enviada: bool,
    company_id: Optional[int] = None,
) -> OportunidadeResponse:
    obj = get_oportunidade(db, opo_id, company_id)
    obj.opoPropostaEnviada = enviada
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return OportunidadeResponse.model_validate(obj)


def inativar_oportunidade(
    db: Session,
    opo_id: int,
    company_id: Optional[int] = None,
) -> OportunidadeResponse:
    obj = get_oportunidade(db, opo_id, company_id)
    if obj.opoAtivo:
        _registrar_historico_automatico(db, obj, "Oportunidade inativada.")
    obj.opoAtivo = False
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return OportunidadeResponse.model_validate(obj)
