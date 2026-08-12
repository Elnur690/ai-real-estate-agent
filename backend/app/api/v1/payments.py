from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin
from app.models.tenant import Tenant
from app.models.payment import Payment

router = APIRouter(prefix="/payments", tags=["Payments"])

class CreatePaymentRequest(BaseModel):
    tenant_id: int
    amount: float
    currency: str = "AZN"
    days_covered: int = 30
    notes: Optional[str] = None

class PaymentResponse(BaseModel):
    id: int
    tenant_id: int
    amount: float
    currency: str
    period_covered_start: Optional[datetime] = None
    period_covered_end: Optional[datetime] = None
    received_by: Optional[int] = None
    received_at: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True

@router.get("", response_model=List[PaymentResponse])
async def list_payments(db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    stmt = select(Payment).order_by(Payment.id.desc())
    res = await db.execute(stmt)
    payments = res.scalars().all()
    return payments

@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_cash_payment(body: CreatePaymentRequest, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    stmt = select(Tenant).where(Tenant.id == body.tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    start_date = datetime.now(timezone.utc)
    # If existing plan hasn't expired yet, extend from current expiration date
    if tenant.plan_expires_at and tenant.plan_expires_at > start_date:
        end_date = tenant.plan_expires_at + timedelta(days=body.days_covered)
    else:
        end_date = start_date + timedelta(days=body.days_covered)

    payment = Payment(
        tenant_id=body.tenant_id,
        amount=body.amount,
        currency=body.currency,
        period_covered_start=start_date,
        period_covered_end=end_date,
        received_by=current_admin.id,
        received_at=start_date,
        notes=body.notes
    )
    db.add(payment)

    # Update tenant plan expiration & status
    tenant.plan_expires_at = end_date
    tenant.status = "active"

    await db.commit()
    await db.refresh(payment)
    return payment
