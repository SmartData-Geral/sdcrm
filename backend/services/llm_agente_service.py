from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..exceptions import BadRequestError, NotFoundError
from ..models.empresa import Empresa
from ..models.llm_agente import LlmAgente
from ..schemas.llm_agente import LlmAgenteListResponse, LlmAgenteResponse, LlmAgenteUpdate
from .llm_agente_defaults import AGENT_SEED_SPECS


def resolve_company_id(db: Session, company_id: Optional[int]) -> int:
    if company_id is not None:
        return company_id
    row = db.scalars(select(Empresa).where(Empresa.empAtivo.is_(True)).order_by(Empresa.empId.asc()).limit(1)).first()
    if row is None:
        raise BadRequestError("Nenhuma empresa ativa cadastrada para resolver agentes de IA.")
    return row.empId


def ensure_agents_seeded_for_company(db: Session, emp_id: int) -> bool:
    """Garante os agentes padrão. Faz commit se inserir linhas (sessão deve estar consistente). Retorna True se houve inserção."""
    existing = db.scalars(select(LlmAgente.agnCodigo).where(LlmAgente.agnEmpId == emp_id)).all()
    codes = {c for c in existing}
    inserted = False
    for spec in AGENT_SEED_SPECS:
        if spec["codigo"] in codes:
            continue
        db.add(
            LlmAgente(
                agnEmpId=emp_id,
                agnCodigo=spec["codigo"],
                agnNome=spec["nome"],
                agnDescricao=spec.get("descricao"),
                agnSystemPrompt=spec["prompt"],
                agnLlmProvider="openai",
                agnLlmModel=None,
                agnRespostaJsonEstruturada=bool(spec.get("estruturada", True)),
                agnAvisoEstrutura=None,
            )
        )
        inserted = True
    if inserted:
        db.commit()
    return inserted


def list_llm_agentes(db: Session, company_id: Optional[int]) -> LlmAgenteListResponse:
    emp_id = resolve_company_id(db, company_id)
    ensure_agents_seeded_for_company(db, emp_id)
    stmt = select(LlmAgente).where(LlmAgente.agnEmpId == emp_id, LlmAgente.agnAtivo.is_(True)).order_by(
        LlmAgente.agnNome.asc()
    )
    rows = db.scalars(stmt).all()
    return LlmAgenteListResponse(
        items=[LlmAgenteResponse.model_validate(r) for r in rows],
        total=len(rows),
    )


def get_llm_agente(db: Session, agn_id: int, company_id: Optional[int]) -> LlmAgente:
    emp_id = resolve_company_id(db, company_id)
    stmt = select(LlmAgente).where(LlmAgente.agnId == agn_id, LlmAgente.agnEmpId == emp_id)
    row = db.scalars(stmt).first()
    if row is None:
        raise NotFoundError("Agente não encontrado.")
    return row


def update_llm_agente(db: Session, agn_id: int, data: LlmAgenteUpdate, company_id: Optional[int]) -> LlmAgenteResponse:
    emp_id = resolve_company_id(db, company_id)
    ensure_agents_seeded_for_company(db, emp_id)
    obj = get_llm_agente(db, agn_id, company_id)
    if data.agnLlmProvider != "openai":
        raise BadRequestError("Neste momento apenas o provider 'openai' é suportado.")
    obj.agnSystemPrompt = data.agnSystemPrompt
    obj.agnLlmProvider = data.agnLlmProvider
    obj.agnLlmModel = data.agnLlmModel
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return LlmAgenteResponse.model_validate(obj)


def seed_agents_for_new_company(db: Session, emp_id: int) -> None:
    """Chamado ao criar empresa para já ter agentes na listagem."""
    ensure_agents_seeded_for_company(db, emp_id)


@dataclass
class ResolvedLlmAgent:
    system_prompt: str
    llm_provider: str
    llm_model: str


def get_agent_by_codigo(db: Session, company_id: Optional[int], codigo: str) -> ResolvedLlmAgent:
    emp_id = resolve_company_id(db, company_id)
    _ = ensure_agents_seeded_for_company(db, emp_id)
    row = db.scalars(
        select(LlmAgente).where(
            LlmAgente.agnEmpId == emp_id,
            LlmAgente.agnCodigo == codigo,
            LlmAgente.agnAtivo.is_(True),
        )
    ).first()
    if row is None:
        # fallback textual do módulo defaults
        spec = next((s for s in AGENT_SEED_SPECS if s["codigo"] == codigo), None)
        if spec is None:
            raise BadRequestError(f"Agente '{codigo}' não configurado.")
        return ResolvedLlmAgent(
            system_prompt=spec["prompt"],
            llm_provider="openai",
            llm_model=settings.LLM_OPENAI_MODEL,
        )
    model = (row.agnLlmModel or "").strip() or settings.LLM_OPENAI_MODEL
    return ResolvedLlmAgent(
        system_prompt=row.agnSystemPrompt,
        llm_provider=row.agnLlmProvider,
        llm_model=model,
    )
