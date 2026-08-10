from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text
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
    plan_started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # active | expired | suspended | pending

    preferred_channel: Mapped[str] = mapped_column(String(20), default="telegram")  # whatsapp | telegram
    whatsapp_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    digest_mode: Mapped[str] = mapped_column(String(20), default="instant")  # instant | hourly | daily

    # Backup-as-a-Service Plan Options
    backup_enabled: Mapped[bool] = mapped_column(default=False)
    backup_frequency_days: Mapped[int] = mapped_column(default=7)  # 1 (daily) | 7 (weekly) | 30 (monthly)
    last_backup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    saved_searches = relationship("SavedSearch", back_populates="tenant", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="tenant", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="tenant", cascade="all, delete-orphan")
