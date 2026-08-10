from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_criteria_text: Mapped[str] = mapped_column(Text, nullable=False)

    district: Mapped[str | None] = mapped_column(String(255), nullable=True)
    min_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_area: Mapped[float | None] = mapped_column(Float, nullable=True)

    seller_type: Mapped[str] = mapped_column(String(50), default="any")  # owner | agency | any
    building_type: Mapped[str] = mapped_column(String(50), default="any")  # new | old | any

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    tenant = relationship("Tenant", back_populates="saved_searches")
    user = relationship("User", back_populates="saved_searches")
    matches = relationship("Match", back_populates="saved_search", cascade="all, delete-orphan")
