from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class AgentPhone(Base):
    __tablename__ = "agent_phones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    phone_clean: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    phone_raw: Mapped[str | None] = mapped_column(String(50), nullable=True)
    agency_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    listing_count: Mapped[int] = mapped_column(Integer, default=1)
    is_blocked_makler: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(100), default="makler_detector")  # portal_profile | duplicate_cluster | phone_sharing | user_report
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
