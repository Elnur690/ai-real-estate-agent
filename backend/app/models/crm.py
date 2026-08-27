from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Float, Integer, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class CrmClient(Base):
    __tablename__ = "crm_clients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    whatsapp_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    telegram_handle: Mapped[str | None] = mapped_column(String(100), nullable=True)

    client_type: Mapped[str] = mapped_column(String(50), default="buyer")  # buyer | renter | seller | landlord
    budget_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    rooms_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rooms_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    districts: Mapped[List[str] | None] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    tenant = relationship("Tenant", back_populates="crm_clients")
    deals = relationship("CrmDeal", back_populates="client", cascade="all, delete-orphan")


class CrmDeal(Base):
    __tablename__ = "crm_deals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("crm_clients.id", ondelete="SET NULL"), nullable=True, index=True)
    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id", ondelete="SET NULL"), nullable=True, index=True)

    # Ingested Listing Snapshot
    listing_title: Mapped[str] = mapped_column(String(500), nullable=False)
    listing_price: Mapped[float] = mapped_column(Float, default=0.0)
    listing_currency: Mapped[str] = mapped_column(String(10), default="AZN")
    listing_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    listing_image: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    listing_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # CRM Stage & Pipeline State
    # stages: new | offered | viewing | negotiation | closed | lost
    stage: Mapped[str] = mapped_column(String(50), default="new", index=True)
    custom_offer_price: Mapped[float | None] = mapped_column(Float, nullable=True) # Custom price proposed to buyer
    commission_amount: Mapped[float | None] = mapped_column(Float, nullable=True) # Expected / earned commission in AZN
    commission_percent: Mapped[float | None] = mapped_column(Float, nullable=True) # Commission %
    
    # Private Makler Notes (key codes, owner real lowest price, notes)
    private_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_viewing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    tenant = relationship("Tenant", back_populates="crm_deals")
    client = relationship("CrmClient", back_populates="deals")
    listing = relationship("Listing")
    activities = relationship("CrmActivity", back_populates="deal", cascade="all, delete-orphan")


class CrmActivity(Base):
    __tablename__ = "crm_activities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False)
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("crm_deals.id", ondelete="CASCADE"), index=True, nullable=True)
    
    action_type: Mapped[str] = mapped_column(String(50), default="note") # note | stage_change | viewing_scheduled | call | whatsapp_sent
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    deal = relationship("CrmDeal", back_populates="activities")
