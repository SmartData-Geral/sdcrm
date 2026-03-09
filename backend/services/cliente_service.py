from typing import Iterable, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..exceptions import NotFoundError
from ..models.cliente import Cliente
from ..schemas.cliente import ClienteCreate, ClienteListResponse, ClienteResponse, ClienteUpdate


def list_clientes(
    db: Session,
    company_id: Optional[int] = None,
    nome: Optional[str] = None,
    status: str = "ativos",
    page: int = 1,
    page_size: int = 20,
) -> ClienteListResponse:
    stmt = select(Cliente)
    if company_id is not None:
        stmt = stmt.where(Cliente.cliEmpId == company_id)
    if nome:
        stmt = stmt.where(Cliente.cliNome.ilike(f"%{nome}%"))

    if status == "ativos":
        stmt = stmt.where(Cliente.cliAtivo.is_(True))
    elif status == "inativos":
        stmt = stmt.where(Cliente.cliAtivo.is_(False))
    # status == "todos" não aplica filtro por cliAtivo

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(total_stmt) or 0

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).all()

    return ClienteListResponse(
        items=[ClienteResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_cliente(db: Session, cli_id: int, company_id: Optional[int] = None) -> Cliente:
    stmt = select(Cliente).where(Cliente.cliId == cli_id)
    if company_id is not None:
        stmt = stmt.where(Cliente.cliEmpId == company_id)
    cliente = db.scalars(stmt).first()
    if cliente is None:
        raise NotFoundError("Cliente não encontrado")
    return cliente


def create_cliente(
    db: Session,
    data: ClienteCreate,
    company_id: Optional[int] = None,
) -> ClienteResponse:
    cliente = Cliente(
        cliEmpId=company_id,
        **data.model_dump(),
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return ClienteResponse.model_validate(cliente)


def update_cliente(
    db: Session,
    cli_id: int,
    data: ClienteUpdate,
    company_id: Optional[int] = None,
) -> ClienteResponse:
    cliente = get_cliente(db, cli_id, company_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cliente, field, value)
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return ClienteResponse.model_validate(cliente)


def delete_cliente(
    db: Session,
    cli_id: int,
    company_id: Optional[int] = None,
) -> None:
    cliente = get_cliente(db, cli_id, company_id)
    cliente.cliAtivo = False
    db.add(cliente)
    db.commit()

