from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Revenue share percentage configured by platform Admin (e.g. 70.0 means 70% to Seller, 30% to Platform)
    commission_rate: Mapped[float] = mapped_column(Float, default=70.0)
    
    # Seller Performance Rank Tier: Bronze | Silver | Gold | Platinum | Diamond
    rank: Mapped[str] = mapped_column(String(50), default="Bronze")
    status: Mapped[str] = mapped_column(String(50), default="active")  # active | suspended | pending
    
    # Financial metrics
    balance: Mapped[float] = mapped_column(Float, default=0.0)  # Current available profit in AZN
    total_earnings: Mapped[float] = mapped_column(Float, default=0.0)  # Lifetime profit in AZN
    total_sales_volume: Mapped[float] = mapped_column(Float, default=0.0)  # Lifetime gross sales in AZN
    platform_fee_settled: Mapped[float] = mapped_column(Float, default=0.0)  # Platform fee collected by Admin in AZN
    
    # Custom White-label Domain settings
    custom_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)  # e.g., "agent.bakuemlak.az"
    custom_domain_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    domain_status: Mapped[str] = mapped_column(String(50), default="disabled")  # disabled | pending_dns | active
    custom_brand_title: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Custom SaaS App Title
    custom_brand_logo: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Custom Logo URL
    
    # Free Trial Offer configuration customizable by Seller (not a package, but a seller offer)
    free_trial_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    free_trial_duration_days: Mapped[int] = mapped_column(Integer, default=7)
    free_trial_max_searches: Mapped[int] = mapped_column(Integer, default=3)
    free_trial_max_locations: Mapped[int] = mapped_column(Integer, default=3)
    free_trial_feature_makler: Mapped[bool] = mapped_column(Boolean, default=True)
    free_trial_feature_avm: Mapped[bool] = mapped_column(Boolean, default=True)
    free_trial_feature_social_brochure: Mapped[bool] = mapped_column(Boolean, default=True)
    free_trial_feature_multi_location: Mapped[bool] = mapped_column(Boolean, default=True)
    free_trial_feature_watermark_images: Mapped[bool] = mapped_column(Boolean, default=False)
    free_trial_image_requests: Mapped[int] = mapped_column(Integer, default=5)
    free_trial_feature_crm: Mapped[bool] = mapped_column(Boolean, default=False)
    free_trial_feature_portfolio: Mapped[bool] = mapped_column(Boolean, default=False)
    free_trial_portfolio_limit: Mapped[int] = mapped_column(Integer, default=25)
    free_trial_feature_custom_domain: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="seller_profile", lazy="noload")
    packages = relationship("SellerPackage", back_populates="seller", cascade="all, delete-orphan", lazy="noload")
    agents = relationship("Tenant", back_populates="seller", lazy="noload")
    transactions = relationship("SellerTransaction", back_populates="seller", cascade="all, delete-orphan", lazy="noload")


class SellerPackage(Base):
    __tablename__ = "seller_packages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Standart Paket", "VIP Agent"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)  # Custom price in AZN
    period: Mapped[str] = mapped_column(String(50), default="monthly")  # monthly | quarterly | semi_annual | annual
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    
    # Package Quotas & Limits
    max_searches: Mapped[int] = mapped_column(Integer, default=10)
    max_locations: Mapped[int] = mapped_column(Integer, default=5)
    
    # Feature flags enabled for this package
    feature_makler_detector: Mapped[bool] = mapped_column(Boolean, default=True)
    feature_avm_bargain_finder: Mapped[bool] = mapped_column(Boolean, default=True)
    feature_social_brochure: Mapped[bool] = mapped_column(Boolean, default=True)
    feature_multi_location: Mapped[bool] = mapped_column(Boolean, default=True)
    feature_client_intake_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    feature_backup_service: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Add-on features and custom multi-tier pricing configured by seller (no minimum enforced)
    feature_aged_listings: Mapped[bool] = mapped_column(Boolean, default=False)
    addon_aged_listings_price: Mapped[float] = mapped_column(Float, default=15.0)
    addon_aged_max_months: Mapped[int] = mapped_column(Integer, default=12)
    addon_aged_tiers: Mapped[list[dict] | None] = mapped_column(JSON, default=list)  # e.g. [{"months": 3, "price": 10.0}, {"months": 6, "price": 20.0}]

    addon_saved_searches: Mapped[int] = mapped_column(Integer, default=0) # e.g. +5 extra searches
    addon_saved_searches_price: Mapped[float] = mapped_column(Float, default=10.0)
    addon_search_tiers: Mapped[list[dict] | None] = mapped_column(JSON, default=list) # e.g. [{"searches": 5, "price": 10.0}, {"searches": 10, "price": 18.0}]

    # 🖼️ Watermark-Free Listing Photos Add-on & Quota
    feature_watermark_free_images: Mapped[bool] = mapped_column(Boolean, default=False)
    included_image_requests: Mapped[int] = mapped_column(Integer, default=0)
    addon_image_requests_price: Mapped[float] = mapped_column(Float, default=10.0)
    addon_image_tiers: Mapped[list[dict] | None] = mapped_column(JSON, default=list) # e.g. [{"images": 25, "price": 10.0}, {"images": 50, "price": 18.0}]
    
    # 💼 Telegram Mini App & Real Estate CRM Add-on
    feature_crm: Mapped[bool] = mapped_column(Boolean, default=False)
    addon_crm_price: Mapped[float] = mapped_column(Float, default=15.0)
    addon_crm_tiers: Mapped[list[dict] | None] = mapped_column(JSON, default=list) # e.g. [{"months": 1, "price": 15.0}, {"months": 3, "price": 35.0}]

    # 🗂️ Agent Portfolio & Showcase Add-on
    feature_portfolio: Mapped[bool] = mapped_column(Boolean, default=False)
    addon_portfolio_price: Mapped[float] = mapped_column(Float, default=15.0)
    addon_portfolio_limit: Mapped[int] = mapped_column(Integer, default=25)
    addon_portfolio_tiers: Mapped[list[dict] | None] = mapped_column(JSON, default=list) # e.g. [{"listings": 25, "price": 15.0}, {"listings": 50, "price": 25.0}]
    
    # 🌐 Custom Domain Add-on
    feature_custom_domain: Mapped[bool] = mapped_column(Boolean, default=False)
    addon_custom_domain_price: Mapped[float] = mapped_column(Float, default=5.0)
    
    # 🏷️ Promotional Sale & Discount Campaign Features
    sale_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    sale_price: Mapped[float | None] = mapped_column(Float, nullable=True) # e.g. 39.0 AZN
    sale_discount_percent: Mapped[float | None] = mapped_column(Float, nullable=True) # e.g. 20.0%
    sale_type: Mapped[str] = mapped_column(String(50), default="permanent") # permanent | first_month | first_3_months | first_6_months | limited_time
    sale_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sale_badge_label: Mapped[str | None] = mapped_column(String(100), nullable=True) # e.g. "🔥 25% Xüsusi Endirim"

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    seller = relationship("Seller", back_populates="packages", lazy="noload")
    subscribed_agents = relationship("Tenant", back_populates="seller_package", lazy="noload")


class SellerTransaction(Base):
    __tablename__ = "seller_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    package_id: Mapped[int | None] = mapped_column(ForeignKey("seller_packages.id", ondelete="SET NULL"), nullable=True)
    
    amount: Mapped[float] = mapped_column(Float, nullable=False)  # Gross amount paid by agent or negative payout in AZN
    commission_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # Commission rate % at time of sale
    seller_profit: Mapped[float | None] = mapped_column(Float, nullable=True)  # Profit earned by seller in AZN
    platform_fee: Mapped[float | None] = mapped_column(Float, nullable=True)  # Platform fee in AZN
    
    type: Mapped[str] = mapped_column(String(50), default="subscription_sale")  # subscription_sale | payout | adjustment
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    seller = relationship("Seller", back_populates="transactions", lazy="noload")
    agent = relationship("Tenant", lazy="noload")
    package = relationship("SellerPackage", lazy="noload")


SELLER_RANK_CONFIG: Dict[str, Dict[str, Any]] = {
    "Bronze": {
        "min_sales": 0.0,
        "bonus_commission": 0.0,
        "max_packages": 5,
        "custom_domain_allowed": False,
        "badge_emoji": "🥉",
        "label": "Bronze Seller",
        "description": "Başlanğıc satıcı səviyyəsi. 5 fərdi paket yaratmaq imkanı.",
        "next_rank": "Silver",
        "next_sales_target": 500.0
    },
    "Silver": {
        "min_sales": 500.0,
        "bonus_commission": 3.0,
        "max_packages": 10,
        "custom_domain_allowed": False,
        "badge_emoji": "🥈",
        "label": "Silver Seller",
        "description": "+3% Əlavə komissiya bonusu və 10 fərdi paket limiti.",
        "next_rank": "Gold",
        "next_sales_target": 2000.0
    },
    "Gold": {
        "min_sales": 2000.0,
        "bonus_commission": 5.0,
        "max_packages": 20,
        "custom_domain_allowed": True,
        "badge_emoji": "🥇",
        "label": "Gold Seller",
        "description": "+5% Komissiya bonusu, 20 paket limiti və Fərdi Domen (White-label) hüququ.",
        "next_rank": "Platinum",
        "next_sales_target": 5000.0
    },
    "Platinum": {
        "min_sales": 5000.0,
        "bonus_commission": 8.0,
        "max_packages": 50,
        "custom_domain_allowed": True,
        "badge_emoji": "💠",
        "label": "Platinum Seller",
        "description": "+8% Komissiya bonusu, 50 paket limiti, Fərdi Domen və 24/7 Prioritet Dəstək.",
        "next_rank": "Diamond",
        "next_sales_target": 10000.0
    },
    "Diamond": {
        "min_sales": 10000.0,
        "bonus_commission": 10.0,
        "max_packages": 999,
        "custom_domain_allowed": True,
        "badge_emoji": "💎",
        "label": "Diamond Seller",
        "description": "+10% Komissiya bonusu, Limitsiz paketlər, Fərdi Domen və VIP Partnyor statusu.",
        "next_rank": None,
        "next_sales_target": None
    }
}
