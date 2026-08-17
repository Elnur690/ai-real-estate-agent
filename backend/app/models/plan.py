from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, Boolean, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False) # e.g. free | starter | pro | agency | enterprise
    name: Mapped[str] = mapped_column(String(255), nullable=False) # e.g. "Pro Real Estate Agent"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    price: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="AZN")
    billing_period: Mapped[str] = mapped_column(String(50), default="monthly") # daily | monthly | quarterly | annual | lifetime
    trial_days: Mapped[int] = mapped_column(Integer, default=7)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_agents: Mapped[int] = mapped_column(Integer, default=1)
    max_saved_searches: Mapped[int] = mapped_column(Integer, default=10)

    # Feature Toggles & Add-ons
    feature_makler_detector: Mapped[bool] = mapped_column(Boolean, default=True)
    feature_avm_bargain_finder: Mapped[bool] = mapped_column(Boolean, default=True)
    feature_b2b_cobrokering: Mapped[bool] = mapped_column(Boolean, default=False)
    feature_social_brochure: Mapped[bool] = mapped_column(Boolean, default=True)
    feature_client_intake_bot: Mapped[bool] = mapped_column(Boolean, default=True)
    feature_multi_location: Mapped[bool] = mapped_column(Boolean, default=True)
    max_locations_per_search: Mapped[int] = mapped_column(Integer, default=5)
    feature_aged_listings: Mapped[bool] = mapped_column(Boolean, default=False)
    addon_aged_listings_price: Mapped[float] = mapped_column(Float, default=0.0) # Optional add-on price in AZN
    backup_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
