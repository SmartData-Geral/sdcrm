from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..core.columns import IdColumnFactory


class UsuarioEmpresa(Base):
    __tablename__ = "usuario_empresa"

    useId: Mapped[int] = IdColumnFactory.int_id("useId")
    useUsuId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuario.usuId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    useEmpId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.empId", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="empresas_vinculo")
    empresa: Mapped["Empresa"] = relationship("Empresa", back_populates="usuarios_vinculo")

