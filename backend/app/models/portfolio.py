from datetime import datetime, timezone
from typing import Any
import secrets
from sqlalchemy import String, Float, Integer, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

def generate_share_code() -> str:
    """Generate a unique URL-safe share token."""
    return secrets.token_urlsafe(8)

class PortfolioListing(Base):
    __tablename__ = "portfolio_listings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False)
    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id", ondelete="SET NULL"), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="AZN")
    price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    district: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metro_station: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_floors: Mapped[int | None] = mapped_column(Integer, nullable=True)

    building_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # new | old
    property_type: Mapped[str] = mapped_column(String(50), default="apartment")  # apartment | house | office | commercial | land
    offer_type: Mapped[str] = mapped_column(String(50), default="sale")  # sale | rent | daily_rent

    photos: Mapped[list[Any] | None] = mapped_column(JSON, default=list)

    # Branded contact info (customizable per listing, defaults to agent profile)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Agent internal private notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Public client share token
    share_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, default=generate_share_code)

    # Status and limit tracking (active listings count against portfolio limit)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active | sold | expired | archived

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    tenant = relationship("Tenant", back_populates="portfolio_listings", lazy="noload")
    listing = relationship("Listing", lazy="noload")
