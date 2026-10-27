from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import IdColumnFactory
from ..database import Base


class MetaAdsPerguntaUso(Base):
    """Perguntas feitas ao analista do cockpit por usuario e dia (America/Sao_Paulo), para o limite diario."""

    __tablename__ = "meta_ads_pergunta_uso"
    __table_args__ = (
        UniqueConstraint("mpuUsuId", "mpuData", name="uq_meta_ads_pergunta_uso_usuario_data"),
    )

    mpuId: Mapped[int] = IdColumnFactory.int_id("mpuId")
    mpuUsuId: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuario.usuId", ondelete="CASCADE"), nullable=False
    )
    mpuData: Mapped[date] = mapped_column(Date, nullable=False)
    mpuQuantidade: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
