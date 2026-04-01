from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..exceptions import BadRequestError, NotFoundError
from ..models.contrato_modelo import ContratoModelo
from ..models.contrato_modelo_clausula import ContratoModeloClausula
from ..models.contrato_modelo_clausula_variacao import ContratoModeloClausulaVariacao
from ..schemas.contrato import (
    ContratoModeloClausulaCreate,
    ContratoModeloClausulaReordenarRequest,
    ContratoModeloClausulaResponse,
    ContratoModeloClausulaUpdate,
    ContratoModeloClausulaVariacaoListResponse,
    ContratoModeloClausulaVariacaoResponse,
    ContratoModeloClausulaVariacaoCreate,
    ContratoModeloClausulaVariacaoUpdate,
    ContratoModeloCreate,
    ContratoModeloListResponse,
    ContratoModeloResponse,
    ContratoModeloUpdate,
)


def _get_modelo(db: Session, company_id: int, modelo_id: int) -> ContratoModelo:
    modelo = db.scalars(
        select(ContratoModelo).where(
            ContratoModelo.ctmId == modelo_id,
            ContratoModelo.ctmEmpId == company_id,
        )
    ).first()
    if modelo is None:
        raise NotFoundError("Modelo de contrato não encontrado")
    return modelo


def list_modelos(db: Session, company_id: int, page: int, page_size: int) -> ContratoModeloListResponse:
    stmt = (
        select(ContratoModelo)
        .where(ContratoModelo.ctmEmpId == company_id)
        .order_by(ContratoModelo.ctmAtivo.desc(), ContratoModelo.ctmNome.asc())
    )
    total = (
        db.scalar(
            select(func.count())
            .select_from(ContratoModelo)
            .where(ContratoModelo.ctmEmpId == company_id)
        )
        or 0
    )
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return ContratoModeloListResponse(
        items=[ContratoModeloResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_modelo(db: Session, company_id: int, modelo_id: int) -> ContratoModeloResponse:
    return ContratoModeloResponse.model_validate(_get_modelo(db, company_id, modelo_id))


def create_modelo(db: Session, company_id: int, data: ContratoModeloCreate) -> ContratoModeloResponse:
    nome = (data.ctmNome or "").strip()
    if not nome:
        raise BadRequestError("Nome do modelo é obrigatório")
    modelo = ContratoModelo(
        ctmEmpId=company_id,
        ctmNome=nome,
        ctmDescricao=data.ctmDescricao,
        ctmAtivo=data.ctmAtivo,
    )
    db.add(modelo)
    db.commit()
    db.refresh(modelo)
    return ContratoModeloResponse.model_validate(modelo)


def update_modelo(db: Session, company_id: int, modelo_id: int, data: ContratoModeloUpdate) -> ContratoModeloResponse:
    modelo = _get_modelo(db, company_id, modelo_id)
    payload = data.model_dump(exclude_unset=True)
    if "ctmNome" in payload and payload["ctmNome"] is not None:
        payload["ctmNome"] = payload["ctmNome"].strip()
        if payload["ctmNome"] == "":
            raise BadRequestError("Nome do modelo não pode ficar vazio")
    for k, v in payload.items():
        setattr(modelo, k, v)
    db.add(modelo)
    db.commit()
    db.refresh(modelo)
    return ContratoModeloResponse.model_validate(modelo)


def set_modelo_ativo(db: Session, company_id: int, modelo_id: int, ativo: bool) -> ContratoModeloResponse:
    modelo = _get_modelo(db, company_id, modelo_id)
    modelo.ctmAtivo = ativo
    db.add(modelo)
    db.commit()
    db.refresh(modelo)
    return ContratoModeloResponse.model_validate(modelo)


def list_clausulas_modelo(
    db: Session, company_id: int, modelo_id: int
) -> list[ContratoModeloClausulaResponse]:
    # Retorna todas (ativas e inativas), para a UX poder mostrar status.
    _ = _get_modelo(db, company_id, modelo_id)
    clausulas = db.scalars(
        select(ContratoModeloClausula).where(
            ContratoModeloClausula.cmcCtmId == modelo_id,
            ContratoModeloClausula.cmcEmpId == company_id,
        )
    ).all()
    clausulas.sort(key=lambda c: (c.cmcOrdem, c.cmcId))
    return [ContratoModeloClausulaResponse.model_validate(c) for c in clausulas]


def create_clausula_modelo(
    db: Session, company_id: int, modelo_id: int, data: ContratoModeloClausulaCreate
) -> ContratoModeloClausulaResponse:
    _ = _get_modelo(db, company_id, modelo_id)

    titulo = (data.cmcTitulo or "").strip()
    texto = (data.cmcTextoPadrao or "").strip()
    if not titulo:
        raise BadRequestError("Título da cláusula é obrigatório")
    if not texto:
        raise BadRequestError("Texto padrão da cláusula é obrigatório")

    ordem = data.cmcOrdem
    if ordem is None:
        max_ordem = db.scalar(
            select(ContratoModeloClausula.cmcOrdem).where(
                ContratoModeloClausula.cmcCtmId == modelo_id,
                ContratoModeloClausula.cmcEmpId == company_id,
            ).order_by(ContratoModeloClausula.cmcOrdem.desc())
        )
        ordem = (max_ordem or 0) + 1
    clausula = ContratoModeloClausula(
        cmcEmpId=company_id,
        cmcCtmId=modelo_id,
        cmcTitulo=titulo,
        cmcTextoPadrao=texto,
        cmcUtilizarPadrao=data.cmcUtilizarPadrao,
        cmcOrdem=ordem,
        cmcAtivo=data.cmcAtivo,
    )
    db.add(clausula)
    db.commit()
    db.refresh(clausula)
    return ContratoModeloClausulaResponse.model_validate(clausula)


def update_clausula_modelo(
    db: Session,
    company_id: int,
    clausula_id: int,
    data: ContratoModeloClausulaUpdate,
) -> ContratoModeloClausulaResponse:
    clausula = db.scalars(
        select(ContratoModeloClausula).where(
            ContratoModeloClausula.cmcId == clausula_id,
            ContratoModeloClausula.cmcEmpId == company_id,
        )
    ).first()
    if clausula is None:
        raise NotFoundError("Cláusula do modelo não encontrada")

    payload = data.model_dump(exclude_unset=True)
    if "cmcTitulo" in payload and payload["cmcTitulo"] is not None:
        payload["cmcTitulo"] = payload["cmcTitulo"].strip()
        if payload["cmcTitulo"] == "":
            raise BadRequestError("Título da cláusula não pode ficar vazio")
    if "cmcTextoPadrao" in payload and payload["cmcTextoPadrao"] is not None:
        payload["cmcTextoPadrao"] = payload["cmcTextoPadrao"].strip()
        if payload["cmcTextoPadrao"] == "":
            raise BadRequestError("Texto padrão da cláusula não pode ficar vazio")
    for k, v in payload.items():
        setattr(clausula, k, v)
    db.add(clausula)
    db.commit()
    db.refresh(clausula)
    return ContratoModeloClausulaResponse.model_validate(clausula)


def set_clausula_ativa(db: Session, company_id: int, clausula_id: int, ativo: bool) -> ContratoModeloClausulaResponse:
    clausula = db.scalars(
        select(ContratoModeloClausula).where(
            ContratoModeloClausula.cmcId == clausula_id,
            ContratoModeloClausula.cmcEmpId == company_id,
        )
    ).first()
    if clausula is None:
        raise NotFoundError("Cláusula do modelo não encontrada")
    clausula.cmcAtivo = ativo
    db.add(clausula)
    db.commit()
    db.refresh(clausula)
    return ContratoModeloClausulaResponse.model_validate(clausula)


def _normalize_ordem_ativa_por_modelo(db: Session, company_id: int, modelo_id: int) -> None:
    clausulas_ativas = db.scalars(
        select(ContratoModeloClausula).where(
            ContratoModeloClausula.cmcCtmId == modelo_id,
            ContratoModeloClausula.cmcEmpId == company_id,
            ContratoModeloClausula.cmcAtivo.is_(True),
        ).order_by(ContratoModeloClausula.cmcOrdem.asc(), ContratoModeloClausula.cmcId.asc())
    ).all()
    for idx, c in enumerate(clausulas_ativas, start=1):
        c.cmcOrdem = idx
    db.commit()


def reordenar_clausula_modelo(
    db: Session,
    company_id: int,
    clausula_id: int,
    data: ContratoModeloClausulaReordenarRequest,
) -> ContratoModeloClausulaResponse:
    clausula = db.scalars(
        select(ContratoModeloClausula).where(
            ContratoModeloClausula.cmcId == clausula_id,
            ContratoModeloClausula.cmcEmpId == company_id,
        )
    ).first()
    if clausula is None:
        raise NotFoundError("Cláusula do modelo não encontrada")

    clausula.cmcOrdem = data.cmcOrdem
    db.add(clausula)
    db.commit()

    # Normaliza apenas cláusulas ativas (ordem final do contrato depende delas).
    _normalize_ordem_ativa_por_modelo(db, company_id, clausula.cmcCtmId)
    db.refresh(clausula)
    return ContratoModeloClausulaResponse.model_validate(clausula)


def list_variacoes_clausula_modelo(
    db: Session, company_id: int, clausula_id: int
) -> ContratoModeloClausulaVariacaoListResponse:
    _ = db.scalars(
        select(ContratoModeloClausula).where(
            ContratoModeloClausula.cmcId == clausula_id,
            ContratoModeloClausula.cmcEmpId == company_id,
        )
    ).first()
    if _ is None:
        raise NotFoundError("Cláusula do modelo não encontrada")

    variacoes = db.scalars(
        select(ContratoModeloClausulaVariacao).where(
            ContratoModeloClausulaVariacao.cmvCmcId == clausula_id,
            ContratoModeloClausulaVariacao.cmvEmpId == company_id,
        ).order_by(ContratoModeloClausulaVariacao.cmvDataCriacao.desc(), ContratoModeloClausulaVariacao.cmvId.asc())
    ).all()
    return ContratoModeloClausulaVariacaoListResponse(
        items=[ContratoModeloClausulaVariacaoResponse.model_validate(v) for v in variacoes],
    )


def create_variacao_clausula_modelo(
    db: Session,
    company_id: int,
    clausula_id: int,
    data: ContratoModeloClausulaVariacaoCreate,
) -> ContratoModeloClausulaVariacaoResponse:
    clausula = db.scalars(
        select(ContratoModeloClausula).where(
            ContratoModeloClausula.cmcId == clausula_id,
            ContratoModeloClausula.cmcEmpId == company_id,
        )
    ).first()
    if clausula is None:
        raise NotFoundError("Cláusula do modelo não encontrada")

    texto = (data.cmvTexto or "").strip()
    if not texto:
        raise BadRequestError("Texto da variação é obrigatório")
    titulo = data.cmvTitulo.strip() if data.cmvTitulo is not None else None
    nome = data.cmvNome.strip() if data.cmvNome is not None else None

    variacao = ContratoModeloClausulaVariacao(
        cmvEmpId=company_id,
        cmvCmcId=clausula_id,
        cmvNome=nome,
        cmvTitulo=titulo,
        cmvTexto=texto,
        cmvAtivo=data.cmvAtivo,
    )
    db.add(variacao)
    db.commit()
    db.refresh(variacao)
    return ContratoModeloClausulaVariacaoResponse.model_validate(variacao)


def update_variacao_clausula_modelo(
    db: Session,
    company_id: int,
    variacao_id: int,
    data: ContratoModeloClausulaVariacaoUpdate,
) -> ContratoModeloClausulaVariacaoResponse:
    variacao = db.scalars(
        select(ContratoModeloClausulaVariacao).where(
            ContratoModeloClausulaVariacao.cmvId == variacao_id,
            ContratoModeloClausulaVariacao.cmvEmpId == company_id,
        )
    ).first()
    if variacao is None:
        raise NotFoundError("Variação da cláusula não encontrada")

    payload = data.model_dump(exclude_unset=True)
    if "cmvTexto" in payload and payload["cmvTexto"] is not None:
        payload["cmvTexto"] = payload["cmvTexto"].strip()
        if payload["cmvTexto"] == "":
            raise BadRequestError("Texto da variação não pode ficar vazio")
    if "cmvTitulo" in payload and payload["cmvTitulo"] is not None:
        payload["cmvTitulo"] = payload["cmvTitulo"].strip()
    if "cmvNome" in payload and payload["cmvNome"] is not None:
        payload["cmvNome"] = payload["cmvNome"].strip()

    for k, v in payload.items():
        setattr(variacao, k, v)

    db.add(variacao)
    db.commit()
    db.refresh(variacao)
    return ContratoModeloClausulaVariacaoResponse.model_validate(variacao)


def set_variacao_clausula_ativa(
    db: Session,
    company_id: int,
    variacao_id: int,
    ativo: bool,
) -> ContratoModeloClausulaVariacaoResponse:
    variacao = db.scalars(
        select(ContratoModeloClausulaVariacao).where(
            ContratoModeloClausulaVariacao.cmvId == variacao_id,
            ContratoModeloClausulaVariacao.cmvEmpId == company_id,
        )
    ).first()
    if variacao is None:
        raise NotFoundError("Variação da cláusula não encontrada")
    variacao.cmvAtivo = ativo
    db.add(variacao)
    db.commit()
    db.refresh(variacao)
    return ContratoModeloClausulaVariacaoResponse.model_validate(variacao)

