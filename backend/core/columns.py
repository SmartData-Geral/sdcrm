from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column


class IdColumnFactory:
    @staticmethod
    def int_id(name: str) -> Mapped[int]:
        return mapped_column(name, Integer, primary_key=True, autoincrement=True)


class AtivoColumnFactory:
    @staticmethod
    def bool_ativo(name: str) -> Mapped[bool]:
        return mapped_column(name, Boolean, default=True, nullable=False)


class AuditColumnFactory:
    @staticmethod
    def datetime_criacao(name: str) -> Mapped[datetime]:
        return mapped_column(
            name,
            DateTime(timezone=True),
            default=datetime.utcnow,
            nullable=False,
        )

    @staticmethod
    def datetime_atualizacao(name: str) -> Mapped[datetime | None]:
        return mapped_column(
            name,
            DateTime(timezone=True),
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=True,
        )


class EmpIdColumnFactory:
    @staticmethod
    def int_emp_id(name: str) -> Mapped[int | None]:
        return mapped_column(name, Integer, nullable=True, index=True)

