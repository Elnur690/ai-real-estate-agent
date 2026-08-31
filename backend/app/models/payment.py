from datetime import datetime, timezone
from sqlalchemy import String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="AZN")

    period_covered_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_covered_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    received_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    tenant = relationship("Tenant", back_populates="payments", lazy="noload")
