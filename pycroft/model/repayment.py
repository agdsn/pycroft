from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from pycroft.model.base import IntegerIdModel


class RepaymentRequest(IntegerIdModel):
    """A request for transferring back excess membership contributions"""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    beneficiary: Mapped[str] = mapped_column(nullable=False)
    iban: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Decimal, nullable=False)
