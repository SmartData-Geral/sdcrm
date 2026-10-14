from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.columns import IdColumnFactory
from ..database import Base


class MetaAdsContaOrigem(Base):
    """Origem ("Como conheceu") cujos leads contam como vindos daquela conta do Meta."""

    __tablename__ = "meta_ads_conta_origem"
    __table_args__ = (UniqueConstraint("mcoMacId", "mcoCcoId", name="uq_meta_ads_conta_origem"),)

    mcoId: Mapped[int] = IdColumnFactory.int_id("mcoId")
    mcoMacId: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_ads_conta.macId", ondelete="CASCADE"), nullable=False, index=True
    )
    mcoCcoId: Mapped[int] = mapped_column(
        Integer, ForeignKey("como_conheceu.ccoId", ondelete="CASCADE"), nullable=False, index=True
    )
