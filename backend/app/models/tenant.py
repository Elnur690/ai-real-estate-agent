from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="individual_agent")  # individual_agent | agency
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    telegram_handle: Mapped[str | None] = mapped_column(String(100), nullable=True)

    plan: Mapped[str] = mapped_column(String(50), default="free")  # free | starter | pro | agency | enterprise
    plan_period: Mapped[str] = mapped_column(String(50), default="monthly")  # monthly | quarterly
    plan_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # active | expired | suspended | pending

    preferred_channel: Mapped[str] = mapped_column(String(20), default="telegram")  # whatsapp | telegram
    whatsapp_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    digest_mode: Mapped[str] = mapped_column(String(20), default="instant")  # instant | hourly | daily

    # Backup-as-a-Service Plan Options
    backup_enabled: Mapped[bool] = mapped_column(default=False)
    backup_frequency_days: Mapped[int] = mapped_column(default=7)  # 1 (daily) | 7 (weekly) | 30 (monthly)
    last_backup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 🚀 Killer Feature Plan & Add-on Options
    feature_makler_detector: Mapped[bool] = mapped_column(default=False)
    feature_avm_bargain_finder: Mapped[bool] = mapped_column(default=False)
    feature_b2b_cobrokering: Mapped[bool] = mapped_column(default=False)
    feature_social_brochure: Mapped[bool] = mapped_column(default=False)
    feature_client_intake_bot: Mapped[bool] = mapped_column(default=False)
    feature_multi_location: Mapped[bool] = mapped_column(default=True)
    max_locations_per_search: Mapped[int] = mapped_column(default=5)
    feature_aged_listings: Mapped[bool] = mapped_column(default=False)
    addon_aged_max_months: Mapped[int] = mapped_column(default=12) # Max historical lookback limit in months (1-24)
    addon_saved_searches: Mapped[int] = mapped_column(default=0) # Extra search slots purchased by agent
    addon_saved_searches_price: Mapped[float] = mapped_column(default=0.0) # Monthly price for search top-up add-on

    # 🎁 Referral System & Promo Code Reward Options
    referral_code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    referred_by_tenant_id: Mapped[int | None] = mapped_column(ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    referral_balance: Mapped[float] = mapped_column(Float, default=0.0) # Bonus credit in AZN

    # 👥 Multi-Agent Team Routing & Group Pairing
    parent_tenant_id: Mapped[int | None] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    assigned_districts: Mapped[list[Any] | None] = mapped_column(JSON, default=list)
    allowed_group_jids: Mapped[list[Any] | None] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    draft_search_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    saved_searches = relationship("SavedSearch", back_populates="tenant", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="tenant", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="tenant", cascade="all, delete-orphan")
