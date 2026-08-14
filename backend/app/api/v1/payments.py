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
    amount: Optional[float] = None
    currency: str = "AZN"
    days_covered: int = 30
    duration_days: Optional[int] = None # Alias for days_covered
    plan: Optional[str] = None
    include_aged_listings: Optional[bool] = None
    addon_aged_max_months: Optional[int] = 12
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

async def process_tenant_cash_payment(
    db: AsyncSession,
    current_admin_id: int,
    tenant_id: int,
    amount: Optional[float] = None,
    currency: str = "AZN",
    days_covered: int = 30,
    plan: Optional[str] = None,
    include_aged_listings: Optional[bool] = None,
    addon_aged_max_months: Optional[int] = 12,
    use_referral_balance: bool = True,
    notes: Optional[str] = None
) -> Payment:
    """Core logic to record cash payment, activate subscription, and enable plan/addon features."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    from app.models.plan import Plan

    if plan:
        tenant.plan = plan.lower().strip()

    plan_code = (tenant.plan or "starter").lower().strip()

    # Look up plan details from DB
    stmt_p = select(Plan).where(Plan.code == plan_code)
    res_p = await db.execute(stmt_p)
    db_plan = res_p.scalars().first()

    if db_plan:
        tenant.feature_makler_detector = db_plan.feature_makler_detector
        tenant.feature_avm_bargain_finder = db_plan.feature_avm_bargain_finder
        tenant.feature_social_brochure = db_plan.feature_social_brochure
        tenant.feature_client_intake_bot = db_plan.feature_client_intake_bot
        tenant.feature_multi_location = getattr(db_plan, 'feature_multi_location', True)
        tenant.max_locations_per_search = getattr(db_plan, 'max_locations_per_search', 5)
        tenant.backup_enabled = db_plan.backup_enabled

    # Handle Aged Listings Add-on
    if include_aged_listings is not None:
        tenant.feature_aged_listings = bool(include_aged_listings)
        if addon_aged_max_months:
            tenant.addon_aged_max_months = int(addon_aged_max_months)
    else:
        if db_plan and getattr(db_plan, 'feature_aged_listings', False):
            tenant.feature_aged_listings = True
        # If tenant already had it active, keep it active!

    # Calculate default price if not explicitly given or <= 0
    multiplier = 10 if days_covered == 365 else (5 if days_covered == 180 else (2.7 if days_covered == 90 else 1))
    base_price = (db_plan.price if db_plan else 29.0) * multiplier
    addon_fee = ((getattr(db_plan, 'addon_aged_listings_price', 15.0) or 15.0) * multiplier) if tenant.feature_aged_listings else 0.0

    final_amount = amount if (amount is not None and amount > 0) else round(base_price + addon_fee, 2)
    pay_currency = currency or (db_plan.currency if db_plan else "AZN")

    # Referral bonus discount
    referral_discount = 0.0
    if use_referral_balance and tenant.referral_balance and tenant.referral_balance > 0:
        referral_discount = min(final_amount, tenant.referral_balance)
        final_amount = round(final_amount - referral_discount, 2)
        tenant.referral_balance = round(tenant.referral_balance - referral_discount, 2)

    start_date = datetime.now(timezone.utc)

    # Ensure timezone awareness for expiration calculation
    if tenant.plan_expires_at:
        curr_expires = tenant.plan_expires_at
        if curr_expires.tzinfo is None:
            curr_expires = curr_expires.replace(tzinfo=timezone.utc)
        if curr_expires > start_date:
            end_date = curr_expires + timedelta(days=days_covered)
        else:
            end_date = start_date + timedelta(days=days_covered)
    else:
        end_date = start_date + timedelta(days=days_covered)

    addon_label = f" + Aged Listings Addon ({tenant.addon_aged_max_months or 12} mo.)" if tenant.feature_aged_listings else ""
    notes_str = notes or f"Cash payment received for {plan_code.upper()} plan{addon_label} ({days_covered} days coverage)"
    if referral_discount > 0:
        notes_str += f" [Applied {referral_discount} AZN referral bonus discount]"

    payment = Payment(
        tenant_id=tenant.id,
        amount=final_amount,
        currency=pay_currency,
        period_covered_start=start_date,
        period_covered_end=end_date,
        received_by=current_admin_id,
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

@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_cash_payment(body: CreatePaymentRequest, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    try:
        days = body.duration_days or body.days_covered or 30
        payment = await process_tenant_cash_payment(
            db=db,
            current_admin_id=current_admin.id,
            tenant_id=body.tenant_id,
            amount=body.amount,
            currency=body.currency,
            days_covered=days,
            plan=body.plan,
            include_aged_listings=body.include_aged_listings,
            addon_aged_max_months=body.addon_aged_max_months,
            use_referral_balance=body.use_referral_balance,
            notes=body.notes
        )
        return payment
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"[Record Payment Error] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to record payment: {str(e)}")
