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
    plan: Optional[str] = None
    use_referral_balance: bool = True
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

        if body.plan:
            tenant.plan = body.plan.lower().strip()

        plan_code = (tenant.plan or "free").lower().strip()

        # Look up plan price if body.amount <= 0
        stmt_p = select(Plan).where(Plan.code == plan_code)
        res_p = await db.execute(stmt_p)
        db_plan = res_p.scalars().first()
        if db_plan:
            tenant.feature_makler_detector = db_plan.feature_makler_detector
            tenant.feature_avm_bargain_finder = db_plan.feature_avm_bargain_finder
            tenant.feature_social_brochure = db_plan.feature_social_brochure
            tenant.feature_client_intake_bot = db_plan.feature_client_intake_bot
            tenant.backup_enabled = db_plan.backup_enabled

        amount = body.amount if body.amount > 0 else (db_plan.price if db_plan else 0.0)
        currency = body.currency or (db_plan.currency if db_plan else "AZN")

        referral_discount = 0.0
        if body.use_referral_balance and tenant.referral_balance and tenant.referral_balance > 0:
            referral_discount = min(amount, tenant.referral_balance)
            amount = round(amount - referral_discount, 2)
            tenant.referral_balance = round(tenant.referral_balance - referral_discount, 2)

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

        notes_str = body.notes or f"Cash payment received for {plan_code.upper()} plan ({body.days_covered} days coverage)"
        if referral_discount > 0:
            notes_str += f" [Applied {referral_discount} AZN referral bonus discount]"

        payment = Payment(
            tenant_id=body.tenant_id,
            amount=amount,
            currency=currency,
            period_covered_start=start_date,
            period_covered_end=end_date,
            received_by=current_admin.id,
            received_at=start_date,
            notes=notes_str
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
