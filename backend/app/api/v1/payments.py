from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, desc
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
    payment_category: Optional[str] = "full" # "full" | "addon_only" | "plan_only" | "custom"
    include_aged_listings: Optional[bool] = None
    addon_aged_max_months: Optional[int] = 12
    addon_saved_searches: Optional[int] = None
    feature_watermark_free_images: Optional[bool] = None
    addon_image_requests_limit: Optional[int] = None
    include_crm_addon: Optional[bool] = None
    addon_crm_price: Optional[float] = None
    include_portfolio_addon: Optional[bool] = None
    addon_portfolio_limit: Optional[int] = None
    addon_portfolio_price: Optional[float] = None
    include_custom_domain_addon: Optional[bool] = None
    addon_custom_domain_price: Optional[float] = None
    use_referral_balance: bool = True
    notes: Optional[str] = None

class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    amount: float
    currency: str
    period_covered_start: Optional[datetime] = None
    period_covered_end: Optional[datetime] = None
    received_by: Optional[int] = None
    received_at: Optional[datetime] = None
    notes: Optional[str] = None

@router.get("", response_model=List[PaymentResponse])
async def list_payments(
    tenant_id: Optional[int] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """List all recorded cash payments."""
    stmt = select(Payment).order_by(desc(Payment.received_at)).limit(limit)
    if tenant_id:
        stmt = stmt.where(Payment.tenant_id == tenant_id)
    result = await db.execute(stmt)
    payments = result.scalars().all()
    return payments

async def process_tenant_cash_payment(
    db: AsyncSession,
    current_admin_id: int,
    tenant_id: int,
    amount: Optional[float] = None,
    currency: str = "AZN",
    days_covered: int = 30,
    plan: Optional[str] = None,
    payment_category: Optional[str] = "full",
    include_aged_listings: Optional[bool] = None,
    addon_aged_max_months: Optional[int] = 12,
    addon_saved_searches: Optional[int] = None,
    feature_watermark_free_images: Optional[bool] = None,
    addon_image_requests_limit: Optional[int] = None,
    include_crm_addon: Optional[bool] = None,
    addon_crm_price: Optional[float] = None,
    include_portfolio_addon: Optional[bool] = None,
    addon_portfolio_limit: Optional[int] = None,
    addon_portfolio_price: Optional[float] = None,
    include_custom_domain_addon: Optional[bool] = None,
    addon_custom_domain_price: Optional[float] = None,
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
        if getattr(db_plan, 'feature_watermark_free_images', False):
            tenant.feature_watermark_free_images = True

    # Calculate period multiplier
    if days_covered == 365:
        multiplier = 10.0
    elif days_covered == 180:
        multiplier = 5.0
    elif days_covered == 90:
        multiplier = 2.7
    elif days_covered == 60:
        multiplier = 2.0
    else:
        multiplier = max(1.0, round(days_covered / 30.0, 2))

    addon_price_per_month = getattr(db_plan, 'addon_aged_listings_price', 15.0) if db_plan else 15.0
    if addon_price_per_month is None or addon_price_per_month <= 0:
        addon_price_per_month = 15.0

    search_addon_price_per_pack = getattr(db_plan, 'addon_saved_searches_price', 10.0) if db_plan else 10.0
    if search_addon_price_per_pack is None or search_addon_price_per_pack <= 0:
        search_addon_price_per_pack = 10.0

    category = (payment_category or "full").lower().strip()

    search_addon_fee = 0.0
    if addon_saved_searches is not None:
        tenant.addon_saved_searches = int(addon_saved_searches)
        if addon_saved_searches > 0:
            search_addon_fee = round((addon_saved_searches / 5.0) * search_addon_price_per_pack * multiplier, 2)
            tenant.addon_saved_searches_price = search_addon_fee
        else:
            tenant.addon_saved_searches_price = 0.0

    image_addon_fee = 0.0
    if addon_image_requests_limit is not None:
        tenant.addon_image_requests_limit = int(addon_image_requests_limit)
        if addon_image_requests_limit > 0:
            tenant.feature_watermark_free_images = True
            tenant.addon_image_requests_used = 0
            image_addon_fee = round((addon_image_requests_limit / 25.0) * 10.0 * multiplier, 2)
            tenant.addon_image_requests_price = image_addon_fee
        else:
            tenant.addon_image_requests_price = 0.0
    if feature_watermark_free_images is not None:
        tenant.feature_watermark_free_images = bool(feature_watermark_free_images)

    crm_addon_fee = 0.0
    if include_crm_addon is not None:
        tenant.feature_crm = bool(include_crm_addon)
        if include_crm_addon:
            crm_price_per_month = addon_crm_price if (addon_crm_price is not None and addon_crm_price > 0) else (getattr(db_plan, 'addon_crm_price', 15.0) or 15.0)
            crm_addon_fee = round(crm_price_per_month * multiplier, 2)
            tenant.addon_crm_price = crm_price_per_month
        else:
            tenant.addon_crm_price = 0.0
    elif tenant.feature_crm:
        crm_price_per_month = tenant.addon_crm_price or 15.0
        crm_addon_fee = round(crm_price_per_month * multiplier, 2)

    portfolio_addon_fee = 0.0
    if include_portfolio_addon is not None:
        tenant.feature_portfolio = bool(include_portfolio_addon)
        if include_portfolio_addon:
            port_limit = addon_portfolio_limit or getattr(db_plan, 'addon_portfolio_limit', 25) or 25
            tenant.portfolio_limit = port_limit
            port_price_per_month = addon_portfolio_price if (addon_portfolio_price is not None and addon_portfolio_price > 0) else (getattr(db_plan, 'addon_portfolio_price', 15.0) or 15.0)
            portfolio_addon_fee = round(port_price_per_month * multiplier, 2)
            tenant.addon_portfolio_price = port_price_per_month
        else:
            tenant.addon_portfolio_price = 0.0
    elif tenant.feature_portfolio:
        port_price_per_month = tenant.addon_portfolio_price or 15.0
        portfolio_addon_fee = round(port_price_per_month * multiplier, 2)

    custom_domain_fee = 0.0
    if include_custom_domain_addon is not None:
        tenant.feature_custom_domain = bool(include_custom_domain_addon)
        if include_custom_domain_addon:
            domain_price_per_month = addon_custom_domain_price if (addon_custom_domain_price is not None and addon_custom_domain_price > 0) else (getattr(db_plan, 'addon_custom_domain_price', 5.0) or 5.0)
            custom_domain_fee = round(domain_price_per_month * multiplier, 2)
            tenant.addon_custom_domain_price = domain_price_per_month
        else:
            tenant.addon_custom_domain_price = 0.0
    elif tenant.feature_custom_domain:
        domain_price_per_month = tenant.addon_custom_domain_price or 5.0
        custom_domain_fee = round(domain_price_per_month * multiplier, 2)

    if category == "addon_only":
        # Addon only payment
        base_price = 0.0
        addon_fee = round(addon_price_per_month * multiplier, 2) if include_aged_listings else 0.0
        if include_aged_listings:
            tenant.feature_aged_listings = True
            if addon_aged_max_months:
                tenant.addon_aged_max_months = int(addon_aged_max_months)
        default_notes = f"Cash payment received for ADDONS ONLY ({days_covered} days coverage)"
    elif category == "plan_only":
        # Plan only payment
        base_price = round((db_plan.price if db_plan else 29.0) * multiplier, 2)
        addon_fee = 0.0
        if include_aged_listings is False:
            tenant.feature_aged_listings = False
        default_notes = f"Cash payment received for {plan_code.upper()} plan ({days_covered} days coverage)"
    else:
        # Full Plan + Addon (if selected or previously active)
        base_price = round((db_plan.price if db_plan else 29.0) * multiplier, 2)
        has_aged = include_aged_listings if include_aged_listings is not None else tenant.feature_aged_listings
        addon_fee = round(addon_price_per_month * multiplier, 2) if has_aged else 0.0
        if include_aged_listings is not None:
            tenant.feature_aged_listings = bool(include_aged_listings)
            if addon_aged_max_months:
                tenant.addon_aged_max_months = int(addon_aged_max_months)
        addon_label = f" + Aged Listings Addon ({tenant.addon_aged_max_months or 12} mo.)" if tenant.feature_aged_listings else ""
        search_label = f" + Extra {tenant.addon_saved_searches} Searches" if (tenant.addon_saved_searches and tenant.addon_saved_searches > 0) else ""
        image_label = f" + Extra {tenant.addon_image_requests_limit} Clean Images" if (tenant.addon_image_requests_limit and tenant.addon_image_requests_limit > 0) else ""
        crm_label = " + Telegram CRM Mini App Addon" if tenant.feature_crm else ""
        portfolio_label = f" + Agent Portfolio ({tenant.portfolio_limit or 25} listings)" if tenant.feature_portfolio else ""
        domain_label = f" + Custom Domain ({tenant.custom_domain})" if (tenant.feature_custom_domain and tenant.custom_domain) else (" + Custom Domain Addon" if tenant.feature_custom_domain else "")
        default_notes = f"Cash payment received for {plan_code.upper()} plan{addon_label}{search_label}{image_label}{crm_label}{portfolio_label}{domain_label} ({days_covered} days coverage)"

    final_amount = amount if (amount is not None and amount > 0) else round(base_price + addon_fee + search_addon_fee + image_addon_fee + crm_addon_fee + portfolio_addon_fee + custom_domain_fee, 2)
    pay_currency = currency or (db_plan.currency if db_plan else "AZN")

    # Referral bonus discount
    referral_discount = 0.0
    if use_referral_balance and tenant.referral_balance and tenant.referral_balance > 0:
        referral_discount = min(final_amount, tenant.referral_balance)
        final_amount = round(final_amount - referral_discount, 2)
        tenant.referral_balance = round(tenant.referral_balance - referral_discount, 2)

    now_utc = datetime.now(timezone.utc)

    # Calculate cumulative coverage period extension
    if tenant.plan_expires_at:
        curr_expires = tenant.plan_expires_at
        if curr_expires.tzinfo is None:
            curr_expires = curr_expires.replace(tzinfo=timezone.utc)
        if curr_expires > now_utc:
            period_start = curr_expires
            end_date = curr_expires + timedelta(days=days_covered)
        else:
            period_start = now_utc
            end_date = now_utc + timedelta(days=days_covered)
    else:
        period_start = now_utc
        end_date = now_utc + timedelta(days=days_covered)

    notes_str = notes or default_notes
    if referral_discount > 0:
        notes_str += f" [Applied {referral_discount} AZN referral bonus discount]"

    payment = Payment(
        tenant_id=tenant.id,
        amount=final_amount,
        currency=pay_currency,
        period_covered_start=period_start,
        period_covered_end=end_date,
        received_by=current_admin_id,
        received_at=now_utc,
        notes=notes_str
    )
    db.add(payment)

    # Update tenant plan expiration & status
    tenant.plan_expires_at = end_date
    tenant.status = "active"
    if tenant.feature_crm:
        tenant.crm_expires_at = end_date
    if tenant.feature_portfolio:
        tenant.portfolio_expires_at = end_date
    if tenant.feature_custom_domain:
        tenant.custom_domain_expires_at = end_date

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
            payment_category=body.payment_category,
            include_aged_listings=body.include_aged_listings,
            addon_aged_max_months=body.addon_aged_max_months,
            addon_saved_searches=body.addon_saved_searches,
            feature_watermark_free_images=body.feature_watermark_free_images,
            addon_image_requests_limit=body.addon_image_requests_limit,
            include_crm_addon=body.include_crm_addon,
            addon_crm_price=body.addon_crm_price,
            include_portfolio_addon=body.include_portfolio_addon,
            addon_portfolio_limit=body.addon_portfolio_limit,
            addon_portfolio_price=body.addon_portfolio_price,
            include_custom_domain_addon=body.include_custom_domain_addon,
            addon_custom_domain_price=body.addon_custom_domain_price,
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
