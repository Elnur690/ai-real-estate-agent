from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class SellerPayoutRequest(Base):
    __tablename__ = "seller_payout_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False, index=True)

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    card_number: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. 4169 **** **** 1234
    card_holder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    iban: Mapped[str | None] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="pending") # pending | approved | paid | rejected
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    seller = relationship("Seller", backref="payout_requests")
