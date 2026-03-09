from datetime import datetime

from sqlalchemy.orm import Mapped


class AuditMixin:
    """
    Mixin conceitual para entidades com auditoria.

    As colunas concretas continuam seguindo o padrão Smart Data
    com alias de 3 letras, por isso os atributos aqui são apenas
    para tipagem e padronização de interface.
    """

    DataCriacao: Mapped[datetime]
    DataAtualizacao: Mapped[datetime | None]


class AtivoMixin:
    """
    Mixin conceitual para entidades com soft delete via campo Ativo.
    """

    Ativo: Mapped[bool]


class EmpresaMixin:
    """
    Mixin conceitual para entidades multiempresa via campo EmpId.
    """

    EmpId: Mapped[int | None]

