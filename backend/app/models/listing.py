from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, Float, Integer, Boolean, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class ListingSource(Base):
    __tablename__ = "listing_sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # website | telegram_channel
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url_or_handle: Mapped[str] = mapped_column(String(500), nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="active")  # active | error | blocked
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    listings = relationship("Listing", back_populates="source", cascade="all, delete-orphan", lazy="noload")


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        Index("idx_listings_matching_perf", "is_active", "seller_type", "offer_type", "property_type", "district", "price"),
        Index("idx_listings_phone_lookup", "phone_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("listing_sources.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="AZN")
    price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    district: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metro_station: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_raw: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_floors: Mapped[int | None] = mapped_column(Integer, nullable=True)

    building_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # new | old
    seller_type: Mapped[str | None] = mapped_column(String(50), nullable=True)    # owner | agency
    offer_type: Mapped[str] = mapped_column(String(50), default="sale")            # sale | rent | daily_rent
    property_type: Mapped[str] = mapped_column(String(50), default="apartment")   # apartment | house | office | commercial | land
    photos: Mapped[list[Any] | None] = mapped_column(JSON, default=list)

    # 🚀 Killer Feature Analytics Fields
    is_first_posting: Mapped[bool] = mapped_column(Boolean, default=True)
    is_makler: Mapped[bool] = mapped_column(Boolean, default=False)
    earlier_posting_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    makler_score: Mapped[float] = mapped_column(Float, default=0.0) # 0.0 (genuine owner) to 1.0 (masked agency)
    
    price_per_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    district_avg_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    bargain_percentage: Mapped[float | None] = mapped_column(Float, nullable=True) # e.g. -15.0 for 15% below market

    # 👥 Multi-Broker Duplicate Clustering
    duplicate_group_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=1)
    duplicate_listings: Mapped[list[Any] | None] = mapped_column(JSON, default=list)

    listing_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    price_history: Mapped[list[Any] | None] = mapped_column(JSON, default=list)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    source = relationship("ListingSource", back_populates="listings", lazy="noload")
    matches = relationship("Match", back_populates="listing", cascade="all, delete-orphan", lazy="noload")
