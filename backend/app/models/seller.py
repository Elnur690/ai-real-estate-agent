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
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="seller_profile")
    packages = relationship("SellerPackage", back_populates="seller", cascade="all, delete-orphan")
    agents = relationship("Tenant", back_populates="seller")
    transactions = relationship("SellerTransaction", back_populates="seller", cascade="all, delete-orphan")


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
    max_searches: Mapped[int] = mapped_column(Integer, default=5)
    max_locations: Mapped[int] = mapped_column(Integer, default=5)
    
    # Feature flags enabled for this package
    feature_makler_detector: Mapped[bool] = mapped_column(Boolean, default=True)
    feature_avm_bargain_finder: Mapped[bool] = mapped_column(Boolean, default=True)
    feature_b2b_cobrokering: Mapped[bool] = mapped_column(Boolean, default=False)
    feature_backup_service: Mapped[bool] = mapped_column(Boolean, default=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    seller = relationship("Seller", back_populates="packages")
    subscribed_agents = relationship("Tenant", back_populates="seller_package")


class SellerTransaction(Base):
    __tablename__ = "seller_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    package_id: Mapped[int | None] = mapped_column(ForeignKey("seller_packages.id", ondelete="SET NULL"), nullable=True)
    
    amount: Mapped[float] = mapped_column(Float, nullable=False)  # Gross amount paid by agent in AZN
    commission_rate: Mapped[float] = mapped_column(Float, nullable=False)  # Commission rate % at time of sale
    seller_profit: Mapped[float] = mapped_column(Float, nullable=False)  # Profit earned by seller in AZN
    platform_fee: Mapped[float] = mapped_column(Float, nullable=False)  # Platform fee in AZN
    
    type: Mapped[str] = mapped_column(String(50), default="subscription_sale")  # subscription_sale | payout | adjustment
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    seller = relationship("Seller", back_populates="transactions")
    agent = relationship("Tenant")
    package = relationship("SellerPackage")
