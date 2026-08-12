from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    saved_search_id: Mapped[int] = mapped_column(ForeignKey("saved_searches.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    score: Mapped[float] = mapped_column(Float, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_channel: Mapped[str] = mapped_column(String(20), default="telegram")  # whatsapp | telegram
    status: Mapped[str] = mapped_column(String(50), default="sent")  # sent | read | acted | ignored

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    listing = relationship("Listing", back_populates="matches")
    saved_search = relationship("SavedSearch", back_populates="matches")
    tenant = relationship("Tenant", back_populates="matches")
