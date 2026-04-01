from __future__ import annotations

import secrets
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..exceptions import BadRequestError, NotFoundError
from ..models.contrato import Contrato
from ..models.contrato_clausula import ContratoClausula
from ..models.contrato_modelo import ContratoModelo
from ..models.contrato_modelo_clausula import ContratoModeloClausula
from ..models.contrato_modelo_clausula_variacao import ContratoModeloClausulaVariacao
from ..models.oportunidade import Oportunidade
from ..schemas.contrato import (
    ContratoClausulaResponse,
    ContratoClausulaVariacaoResponse,
    ContratoClausulaUpdate,
    ContratoCreate,
    ContratoListResponse,
    ContratoSalvarComoVariacaoRequest,
    ContratoResponse,
    ContratoUpdate,
)
from ..services.contrato_placeholders import render_placeholders


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_public_token() -> str:
    return secrets.token_urlsafe(24)


def _get_modelo_base_ativo(
    db: Session, company_id: int, contrato_modelo_id: int | None
) -> ContratoModelo:
    # Regra explícita (etapa atual): existe um "modelo base principal" por empresa.
    # Nesta fase não criamos constraint física; quando ctrCtmId não é informado,
    # selecionamos o modelo ativo mais recente da empresa.
    stmt = select(ContratoModelo).where(
        ContratoModelo.ctmEmpId == company_id,
        ContratoModelo.ctmAtivo.is_(True),
    )
    if contrato_modelo_id is not None:
        stmt = stmt.where(ContratoModelo.ctmId == contrato_modelo_id)
    stmt = stmt.order_by(ContratoModelo.ctmDataCriacao.desc())
    modelo = db.scalars(stmt).first()
    if modelo is None:
        raise NotFoundError("Modelo base de contrato não encontrado para a empresa")
    return modelo


def _get_contrato_ativo(db: Session, company_id: int, contrato_id: int) -> Contrato:
    contrato = db.scalars(
        select(Contrato).where(
            Contrato.ctrId == contrato_id,
            Contrato.ctrEmpId == company_id,
            Contrato.ctrAtivo.is_(True),
        )
    ).first()
    if contrato is None:
        raise NotFoundError("Contrato não encontrado")
    return contrato


def _recalcular_ordem_final_clausulas(db: Session, contrato_id: int) -> None:
    clausulas = db.scalars(
        select(ContratoClausula)
        .where(
            ContratoClausula.cclCtrId == contrato_id,
            ContratoClausula.cclAtivo.is_(True),
        )
        .order_by(ContratoClausula.cclOrdemBase.asc(), ContratoClausula.cclId.asc())
    ).all()

    ordem = 1
    for ccl in clausulas:
        if ccl.cclUtilizar and ccl.cclAtivo:
            ccl.cclOrdemFinal = ordem
            ordem += 1
        else:
            ccl.cclOrdemFinal = 0
    db.add_all(clausulas)
    db.commit()


def _build_placeholders_values(contrato: Contrato) -> dict[str, Any]:
    return {
        "razao_social": contrato.ctrRazaoSocial,
        "cnpj": contrato.ctrCnpj,
        "endereco": contrato.ctrEndereco,
        "responsavel_nome": contrato.ctrResponsavelNome,
        "responsavel_cpf": contrato.ctrResponsavelCpf,
        "objeto_contrato": contrato.ctrObjetoContrato,
        "valor_contrato": str(contrato.ctrValorContrato),
        "forma_pagamento": contrato.ctrFormaPagamento,
        "vigencia": contrato.ctrVigencia,
        "data_inicio": contrato.ctrDataInicio.isoformat() if contrato.ctrDataInicio else "",
        "foro": contrato.ctrForo,
        "reajuste": contrato.ctrReajuste or "",
    }


def render_contrato_text(text: str, contrato: Contrato) -> str:
    """Renderiza {{placeholders}} no texto da cláusula (HTML escaped)."""

    mapping = _build_placeholders_values(contrato)
    return render_placeholders(text, mapping)


def _build_clausula_response(
    db: Session, company_id: int, ccl: ContratoClausula
) -> ContratoClausulaResponse:
    base = db.scalars(
        select(ContratoModeloClausula).where(
            ContratoModeloClausula.cmcId == ccl.cclCmcId,
            ContratoModeloClausula.cmcEmpId == company_id,
        )
    ).first()
    if base is None:
        raise NotFoundError("Cláusula base do contrato não encontrada")

    variacoes = db.scalars(
        select(ContratoModeloClausulaVariacao).where(
            ContratoModeloClausulaVariacao.cmvCmcId == base.cmcId,
            ContratoModeloClausulaVariacao.cmvEmpId == company_id,
            ContratoModeloClausulaVariacao.cmvAtivo.is_(True),
        )
    ).all()

    return ContratoClausulaResponse(
        cclId=ccl.cclId,
        cclCmcId=ccl.cclCmcId,
        cclCmvId=ccl.cclCmvId,
        cclTitulo=ccl.cclTitulo,
        cclTexto=ccl.cclTexto,
        cclUtilizar=ccl.cclUtilizar,
        cclOrdemBase=ccl.cclOrdemBase,
        cclOrdemFinal=ccl.cclOrdemFinal,
        cclAtivo=ccl.cclAtivo,
        cmcTituloPadrao=base.cmcTitulo,
        cmcTextoPadrao=base.cmcTextoPadrao,
        variacoes=[
            ContratoClausulaVariacaoResponse(
                cmvId=v.cmvId,
                cmvNome=v.cmvNome,
                cmvTitulo=v.cmvTitulo,
                cmvTexto=v.cmvTexto,
                cmvAtivo=v.cmvAtivo,
            )
            for v in variacoes
        ],
    )


def listar_clausulas_contrato(
    db: Session, company_id: int, contrato_id: int
) -> list[ContratoClausulaResponse]:
    contrato = _get_contrato_ativo(db, company_id, contrato_id)
    _ = contrato  # contrato existe; garante controle de tenant

    clausulas = db.scalars(
        select(ContratoClausula)
        .where(
            ContratoClausula.cclCtrId == contrato_id,
            ContratoClausula.cclEmpId == company_id,
            ContratoClausula.cclAtivo.is_(True),
        )
        .order_by(ContratoClausula.cclOrdemBase.asc(), ContratoClausula.cclId.asc())
    ).all()

    return [_build_clausula_response(db=db, company_id=company_id, ccl=ccl) for ccl in clausulas]


def get_contrato(db: Session, company_id: int, contrato_id: int) -> ContratoResponse:
    contrato = _get_contrato_ativo(db, company_id, contrato_id)
    return ContratoResponse.model_validate(contrato)


def get_contrato_por_oportunidade(
    db: Session, company_id: int, oportunidade_id: int
) -> ContratoResponse:
    # Confirma que a oportunidade pertence ao tenant.
    opo = db.scalars(
        select(Oportunidade).where(
            Oportunidade.opoId == oportunidade_id,
            Oportunidade.opoEmpId == company_id,
        )
    ).first()
    if opo is None:
        raise NotFoundError("Oportunidade não encontrada para a empresa")

    contrato = db.scalars(
        select(Contrato).where(
            Contrato.ctrEmpId == company_id,
            Contrato.ctrOpoId == oportunidade_id,
            Contrato.ctrAtivo.is_(True),
        )
    ).first()
    if contrato is None:
        raise NotFoundError("Contrato não encontrado para a oportunidade")

    return ContratoResponse.model_validate(contrato)


def list_contratos(
    db: Session, company_id: int, page: int, page_size: int
) -> ContratoListResponse:
    total = db.scalar(
        select(func.count())
        .select_from(Contrato)
        .where(Contrato.ctrEmpId == company_id, Contrato.ctrAtivo.is_(True))
    ) or 0
    stmt = (
        select(Contrato)
        .where(Contrato.ctrEmpId == company_id, Contrato.ctrAtivo.is_(True))
        .order_by(Contrato.ctrDataCriacao.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = db.scalars(stmt).all()
    return ContratoListResponse(
        items=[ContratoResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def criar_contrato(
    db: Session, data: ContratoCreate, company_id: int
) -> ContratoResponse:
    contrato_modelo_id = data.ctrCtmId if data.ctrCtmId is not None else None
    modelo = _get_modelo_base_ativo(db, company_id, contrato_modelo_id)

    if data.ctrOpoId is not None:
        opo = db.scalars(
            select(Oportunidade).where(
                Oportunidade.opoId == data.ctrOpoId,
                Oportunidade.opoEmpId == company_id,
            )
        ).first()
        if opo is None:
            raise NotFoundError("Oportunidade não encontrada para a empresa")

        # Regra: apenas 1 contrato por oportunidade. Mesmo que exista contrato inativo,
        # a criação deve ser bloqueada para evitar violação da constraint.
        existente = db.scalars(
            select(Contrato).where(
                Contrato.ctrEmpId == company_id,
                Contrato.ctrOpoId == data.ctrOpoId,
            )
        ).first()
        if existente is not None:
            raise BadRequestError("Já existe contrato para esta oportunidade")

    # Garante um nome mesmo quando o front não informa.
    if data.ctrNome and data.ctrNome.strip():
        ctr_nome = data.ctrNome.strip()
    else:
        if data.ctrOpoId is not None:
            ctr_nome = f"Contrato - Oportunidade {data.ctrOpoId}"
        else:
            ctr_nome = "Contrato Avulso"

    contrato = Contrato(
        ctrEmpId=company_id,
        ctrOpoId=data.ctrOpoId,
        ctrCtmId=modelo.ctmId,
        ctrNome=ctr_nome,
        ctrStatus="pronto",
        ctrTokenPublico=_new_public_token(),
        ctrRazaoSocial=data.ctrRazaoSocial,
        ctrCnpj=data.ctrCnpj,
        ctrEndereco=data.ctrEndereco,
        ctrResponsavelNome=data.ctrResponsavelNome,
        ctrResponsavelCpf=data.ctrResponsavelCpf,
        ctrObjetoContrato=data.ctrObjetoContrato,
        ctrValorContrato=data.ctrValorContrato,
        ctrFormaPagamento=data.ctrFormaPagamento,
        ctrVigencia=data.ctrVigencia,
        ctrDataInicio=data.ctrDataInicio,
        ctrForo=data.ctrForo,
        ctrReajuste=data.ctrReajuste,
        ctrAtivo=True,
    )
    db.add(contrato)
    db.flush()

    base_clausulas = db.scalars(
        select(ContratoModeloClausula).where(
            ContratoModeloClausula.cmcCtmId == modelo.ctmId,
            ContratoModeloClausula.cmcEmpId == company_id,
            ContratoModeloClausula.cmcAtivo.is_(True),
        ).order_by(ContratoModeloClausula.cmcOrdem.asc(), ContratoModeloClausula.cmcId.asc())
    ).all()

    for cmc in base_clausulas:
        db.add(
            ContratoClausula(
                cclEmpId=company_id,
                cclCtrId=contrato.ctrId,
                cclCmcId=cmc.cmcId,
                cclCmvId=None,
                cclTitulo=cmc.cmcTitulo,
                cclTexto=cmc.cmcTextoPadrao,
                cclUtilizar=cmc.cmcUtilizarPadrao,
                cclOrdemBase=cmc.cmcOrdem,
                cclOrdemFinal=0,
                cclAtivo=True,
            )
        )

    db.commit()
    _recalcular_ordem_final_clausulas(db, contrato.ctrId)
    db.refresh(contrato)
    return ContratoResponse.model_validate(contrato)


def update_contrato(
    db: Session, company_id: int, contrato_id: int, data: ContratoUpdate
) -> ContratoResponse:
    contrato = _get_contrato_ativo(db, company_id, contrato_id)
    payload = data.model_dump(exclude_unset=True)

    for k, v in payload.items():
        # Map direto para atributos ctr*
        setattr(contrato, k, v)
    db.add(contrato)
    db.commit()
    db.refresh(contrato)
    return ContratoResponse.model_validate(contrato)


def set_status_contrato(
    db: Session, company_id: int, contrato_id: int, novo_status: str
) -> ContratoResponse:
    if novo_status not in {"pronto", "assinado"}:
        raise BadRequestError("Status de contrato inválido")
    contrato = _get_contrato_ativo(db, company_id, contrato_id)
    contrato.ctrStatus = novo_status
    db.add(contrato)
    db.commit()
    db.refresh(contrato)
    return ContratoResponse.model_validate(contrato)


def set_clausula_utilizar(
    db: Session,
    company_id: int,
    contrato_id: int,
    clausula_id: int,
    utilizar: bool,
) -> ContratoClausulaResponse:
    ccl = db.scalars(
        select(ContratoClausula).where(
            ContratoClausula.cclId == clausula_id,
            ContratoClausula.cclCtrId == contrato_id,
            ContratoClausula.cclEmpId == company_id,
            ContratoClausula.cclAtivo.is_(True),
        )
    ).first()
    if ccl is None:
        raise NotFoundError("Cláusula do contrato não encontrada")

    ccl.cclUtilizar = utilizar
    db.add(ccl)
    db.commit()
    _recalcular_ordem_final_clausulas(db, contrato_id)
    db.refresh(ccl)
    return _build_clausula_response(db=db, company_id=company_id, ccl=ccl)


def update_clausula_snapshot(
    db: Session,
    company_id: int,
    contrato_id: int,
    clausula_id: int,
    data: ContratoClausulaUpdate,
) -> ContratoClausulaResponse:
    ccl = db.scalars(
        select(ContratoClausula).where(
            ContratoClausula.cclId == clausula_id,
            ContratoClausula.cclCtrId == contrato_id,
            ContratoClausula.cclEmpId == company_id,
            ContratoClausula.cclAtivo.is_(True),
        )
    ).first()
    if ccl is None:
        raise NotFoundError("Cláusula do contrato não encontrada")

    base = db.scalars(
        select(ContratoModeloClausula).where(
            ContratoModeloClausula.cmcId == ccl.cclCmcId,
            ContratoModeloClausula.cmcEmpId == company_id,
            ContratoModeloClausula.cmcAtivo.is_(True),
        )
    ).first()
    if base is None:
        raise NotFoundError("Cláusula base do contrato não encontrada")

    payload = data.model_dump(exclude_unset=True)

    # 1) Seleção de versão (padrão ou variação) se o front mandou cclCmvId.
    if "cclCmvId" in payload:
        cmv_id = payload["cclCmvId"]
        if cmv_id is None:
            ccl.cclCmvId = None
            ccl.cclTitulo = base.cmcTitulo
            ccl.cclTexto = base.cmcTextoPadrao
        else:
            variacao = db.scalars(
                select(ContratoModeloClausulaVariacao).where(
                    ContratoModeloClausulaVariacao.cmvId == cmv_id,
                    ContratoModeloClausulaVariacao.cmvEmpId == company_id,
                    ContratoModeloClausulaVariacao.cmvCmcId == ccl.cclCmcId,
                    ContratoModeloClausulaVariacao.cmvAtivo.is_(True),
                )
            ).first()
            if variacao is None:
                raise NotFoundError("Variação da cláusula não encontrada")
            ccl.cclCmvId = variacao.cmvId
            ccl.cclTitulo = variacao.cmvTitulo or base.cmcTitulo
            ccl.cclTexto = variacao.cmvTexto

    # 2) Edição livre do snapshot (título/texto).
    if "cclTitulo" in payload and payload["cclTitulo"] is not None:
        ccl.cclTitulo = payload["cclTitulo"]
    if "cclTexto" in payload and payload["cclTexto"] is not None:
        ccl.cclTexto = payload["cclTexto"]

    # 3) Utilização (ativo no contrato) e recálculo de numeração.
    recalc = False
    if "cclUtilizar" in payload and payload["cclUtilizar"] is not None:
        if ccl.cclUtilizar != payload["cclUtilizar"]:
            recalc = True
        ccl.cclUtilizar = payload["cclUtilizar"]

    db.add(ccl)
    db.commit()

    if recalc:
        _recalcular_ordem_final_clausulas(db, contrato_id)

    db.refresh(ccl)
    return _build_clausula_response(db=db, company_id=company_id, ccl=ccl)


def salvar_clausula_como_variacao(
    db: Session,
    company_id: int,
    contrato_id: int,
    clausula_id: int,
    data: ContratoSalvarComoVariacaoRequest,
) -> ContratoClausulaResponse:
    ccl = db.scalars(
        select(ContratoClausula).where(
            ContratoClausula.cclId == clausula_id,
            ContratoClausula.cclCtrId == contrato_id,
            ContratoClausula.cclEmpId == company_id,
            ContratoClausula.cclAtivo.is_(True),
        )
    ).first()
    if ccl is None:
        raise NotFoundError("Cláusula do contrato não encontrada")

    if not ccl.cclTitulo.strip():
        raise BadRequestError("Título da cláusula não pode ficar vazio para salvar como variação")
    if not ccl.cclTexto.strip():
        raise BadRequestError("Texto da cláusula não pode ficar vazio para salvar como variação")

    base_id = ccl.cclCmcId
    cmv = ContratoModeloClausulaVariacao(
        cmvEmpId=company_id,
        cmvCmcId=base_id,
        cmvNome=data.cmvNome,
        cmvTitulo=ccl.cclTitulo,
        cmvTexto=ccl.cclTexto,
        cmvAtivo=True,
    )
    db.add(cmv)
    db.flush()

    # Passa a usar a variação recém-criada no snapshot (mantém title/text atuais).
    ccl.cclCmvId = cmv.cmvId
    db.add(ccl)
    db.commit()
    db.refresh(cmv)
    db.refresh(ccl)

    return _build_clausula_response(db=db, company_id=company_id, ccl=ccl)

