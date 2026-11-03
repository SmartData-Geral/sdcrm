from typing import Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..exceptions import ConflictError, NotFoundError
from ..models.tag import Tag
from ..schemas.tag import TagCreate, TagListResponse, TagResponse, TagUpdate


def _validar_nome_disponivel(
    db: Session, nome: str, company_id: Optional[int], tag_id: Optional[int] = None
) -> None:
    stmt = select(Tag.tagId).where(Tag.tagEmpId == company_id, func.lower(Tag.tagNome) == nome.lower())
    if tag_id is not None:
        stmt = stmt.where(Tag.tagId != tag_id)
    if db.scalars(stmt).first() is not None:
        raise ConflictError("Já existe uma tag com esse nome")


def list_tags(
    db: Session,
    company_id: Optional[int] = None,
    nome: Optional[str] = None,
    status: Literal["ativos", "inativos", "todos"] = "ativos",
    page: int = 1,
    page_size: int = 20,
) -> TagListResponse:
    stmt = select(Tag)
    if company_id is not None:
        stmt = stmt.where(Tag.tagEmpId == company_id)
    if nome:
        stmt = stmt.where(Tag.tagNome.ilike(f"%{nome}%"))
    if status == "ativos":
        stmt = stmt.where(Tag.tagAtivo.is_(True))
    elif status == "inativos":
        stmt = stmt.where(Tag.tagAtivo.is_(False))
    stmt = stmt.order_by(Tag.tagNome)
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(total_stmt) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).all()
    return TagListResponse(
        items=[TagResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_tag(db: Session, tag_id: int, company_id: Optional[int] = None) -> Tag:
    stmt = select(Tag).where(Tag.tagId == tag_id)
    if company_id is not None:
        stmt = stmt.where(Tag.tagEmpId == company_id)
    row = db.scalars(stmt).first()
    if row is None:
        raise NotFoundError("Tag não encontrada")
    return row


def create_tag(db: Session, data: TagCreate, company_id: Optional[int] = None) -> TagResponse:
    _validar_nome_disponivel(db, data.tagNome, company_id)
    obj = Tag(tagEmpId=company_id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return TagResponse.model_validate(obj)


def update_tag(db: Session, tag_id: int, data: TagUpdate, company_id: Optional[int] = None) -> TagResponse:
    obj = get_tag(db, tag_id, company_id)
    if data.tagNome is not None:
        _validar_nome_disponivel(db, data.tagNome, obj.tagEmpId, tag_id)
    for k, v in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return TagResponse.model_validate(obj)


def set_tag_ativo(db: Session, tag_id: int, ativo: bool, company_id: Optional[int] = None) -> TagResponse:
    obj = get_tag(db, tag_id, company_id)
    obj.tagAtivo = ativo
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return TagResponse.model_validate(obj)
