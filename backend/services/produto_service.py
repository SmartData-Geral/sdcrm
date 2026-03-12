from typing import Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..exceptions import NotFoundError
from ..models.produto import Produto
from ..schemas.produto import ProdutoCreate, ProdutoListResponse, ProdutoResponse, ProdutoUpdate


def list_produtos(
    db: Session,
    company_id: Optional[int] = None,
    nome: Optional[str] = None,
    status: Literal["ativos", "inativos", "todos"] = "ativos",
    page: int = 1,
    page_size: int = 20,
) -> ProdutoListResponse:
    stmt = select(Produto)
    if company_id is not None:
        stmt = stmt.where(Produto.proEmpId == company_id)
    if nome:
        stmt = stmt.where(Produto.proNome.ilike(f"%{nome}%"))
    if status == "ativos":
        stmt = stmt.where(Produto.proAtivo.is_(True))
    elif status == "inativos":
        stmt = stmt.where(Produto.proAtivo.is_(False))
    stmt = stmt.order_by(Produto.proNome)
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(total_stmt) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).all()
    return ProdutoListResponse(
        items=[ProdutoResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_produto(db: Session, pro_id: int, company_id: Optional[int] = None) -> Produto:
    stmt = select(Produto).where(Produto.proId == pro_id)
    if company_id is not None:
        stmt = stmt.where(Produto.proEmpId == company_id)
    row = db.scalars(stmt).first()
    if row is None:
        raise NotFoundError("Produto não encontrado")
    return row


def create_produto(
    db: Session,
    data: ProdutoCreate,
    company_id: Optional[int] = None,
) -> ProdutoResponse:
    obj = Produto(proEmpId=company_id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return ProdutoResponse.model_validate(obj)


def update_produto(
    db: Session,
    pro_id: int,
    data: ProdutoUpdate,
    company_id: Optional[int] = None,
) -> ProdutoResponse:
    obj = get_produto(db, pro_id, company_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return ProdutoResponse.model_validate(obj)


def set_produto_ativo(
    db: Session,
    pro_id: int,
    ativo: bool,
    company_id: Optional[int] = None,
) -> ProdutoResponse:
    obj = get_produto(db, pro_id, company_id)
    obj.proAtivo = ativo
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return ProdutoResponse.model_validate(obj)
