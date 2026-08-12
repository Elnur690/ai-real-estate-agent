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
    try:
        stmt = select(Tenant).where(Tenant.id == body.tenant_id)
        res = await db.execute(stmt)
        tenant = res.scalars().first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        from app.models.plan import Plan

        plan_code = (tenant.plan or "free").lower().strip()

        # Look up plan price if body.amount <= 0
        stmt_p = select(Plan).where(Plan.code == plan_code)
        res_p = await db.execute(stmt_p)
        db_plan = res_p.scalars().first()

        amount = body.amount if body.amount > 0 else (db_plan.price if db_plan else 0.0)
        currency = body.currency or (db_plan.currency if db_plan else "AZN")

        start_date = datetime.now(timezone.utc)

        # Ensure timezone awareness for expiration comparison
        if tenant.plan_expires_at:
            curr_expires = tenant.plan_expires_at
            if curr_expires.tzinfo is None:
                curr_expires = curr_expires.replace(tzinfo=timezone.utc)
            if curr_expires > start_date:
                end_date = curr_expires + timedelta(days=body.days_covered)
            else:
                end_date = start_date + timedelta(days=body.days_covered)
        else:
            end_date = start_date + timedelta(days=body.days_covered)

        payment = Payment(
            tenant_id=body.tenant_id,
            amount=amount,
            currency=currency,
            period_covered_start=start_date,
            period_covered_end=end_date,
            received_by=current_admin.id,
            received_at=start_date,
            notes=body.notes or f"Cash payment received for {plan_code.upper()} plan ({body.days_covered} days coverage)"
        )
        db.add(payment)

        # Update tenant plan expiration & status
        tenant.plan_expires_at = end_date
        tenant.status = "active"

        await db.commit()
        await db.refresh(payment)
        return payment
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"[Record Payment Error] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to record payment: {str(e)}")
