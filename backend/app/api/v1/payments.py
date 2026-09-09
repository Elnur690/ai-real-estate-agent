from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin
from app.models.tenant import Tenant
from app.models.payment import Payment
from app.models.seller import Seller, SellerPackage, SellerTransaction

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
    created_at: Optional[datetime] = None

    # Tenant Details
    tenant_name: Optional[str] = None
    tenant_phone: Optional[str] = None
    tenant_status: Optional[str] = None
    tenant_plan: Optional[str] = None
    preferred_channel: Optional[str] = None
    plan_expires_at: Optional[datetime] = None
    days_remaining: int = 0
    is_expired: bool = False
    subscription_status: str = "active" # "active" | "expiring_soon" | "expired"

    # Seller / Reseller Details
    seller_id: Optional[int] = None
    seller_name: Optional[str] = None
    seller_company: Optional[str] = None
    seller_phone: Optional[str] = None
    seller_rank: Optional[str] = None
    seller_commission_rate: Optional[float] = None
    is_reseller_sale: bool = False

    # Financial & Package Split Details
    package_id: Optional[int] = None
    package_name: Optional[str] = None
    package_duration_days: Optional[int] = None
    gross_amount: float = 0.0
    seller_profit: float = 0.0
    platform_fee: float = 0.0
    transaction_id: Optional[int] = None
    transaction_type: Optional[str] = None


@router.get("/analytics")
async def get_payments_analytics(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Returns comprehensive financial and subscription analytics for admin."""
    now_utc = datetime.now(timezone.utc)

    # 1. Fetch all payments
    res_payments = await db.execute(select(Payment).order_by(desc(Payment.received_at)))
    payments = res_payments.scalars().all()

    # 2. Fetch all tenants
    res_tenants = await db.execute(select(Tenant))
    tenants = res_tenants.scalars().all()
    tenant_map = {t.id: t for t in tenants}

    # 3. Fetch all sellers
    res_sellers = await db.execute(select(Seller))
    sellers = res_sellers.scalars().all()
    seller_map = {s.id: s for s in sellers}

    # 4. Fetch seller transactions
    res_txs = await db.execute(select(SellerTransaction).order_by(desc(SellerTransaction.id)))
    txs = res_txs.scalars().all()

    total_gross = sum(p.amount for p in payments)
    total_payments_count = len(payments)

    reseller_sales_volume = 0.0
    reseller_commissions_paid = 0.0
    direct_admin_revenue = 0.0

    # Per-seller stats accumulator
    seller_stats = {
        s.id: {
            "seller_id": s.id,
            "name": s.name,
            "company_name": s.company_name,
            "phone": s.phone,
            "rank": s.rank,
            "commission_rate": s.commission_rate,
            "total_sales_count": 0,
            "gross_volume": 0.0,
            "seller_profit": 0.0,
            "platform_fee": 0.0,
            "balance": s.balance
        }
        for s in sellers
    }

    # Group transactions by tenant
    tx_by_tenant = {}
    for tx in txs:
        if tx.tenant_id and tx.tenant_id not in tx_by_tenant:
            tx_by_tenant[tx.tenant_id] = tx

    for p in payments:
        t = tenant_map.get(p.tenant_id)
        if t and t.seller_id and t.seller_id in seller_map:
            seller = seller_map[t.seller_id]
            reseller_sales_volume += p.amount
            s_stat = seller_stats[seller.id]
            s_stat["total_sales_count"] += 1
            s_stat["gross_volume"] += p.amount

            tx = tx_by_tenant.get(p.tenant_id)
            if tx and tx.seller_profit is not None:
                profit = tx.seller_profit
                fee = tx.platform_fee if tx.platform_fee is not None else (p.amount - profit)
            else:
                comm_pct = seller.commission_rate
                profit = round(p.amount * (comm_pct / 100.0), 2)
                fee = round(p.amount - profit, 2)

            reseller_commissions_paid += profit
            s_stat["seller_profit"] += profit
            s_stat["platform_fee"] += fee
        else:
            direct_admin_revenue += p.amount

    platform_net_revenue = round(direct_admin_revenue + (reseller_sales_volume - reseller_commissions_paid), 2)

    # Subscription health metrics across all tenants
    active_count = 0
    expiring_soon_count = 0
    expired_count = 0

    for t in tenants:
        if t.plan_expires_at:
            exp = t.plan_expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp > now_utc:
                days_left = (exp - now_utc).days
                if days_left <= 5:
                    expiring_soon_count += 1
                else:
                    active_count += 1
            else:
                expired_count += 1
        else:
            expired_count += 1

    return {
        "total_gross_revenue": round(total_gross, 2),
        "total_payments_count": total_payments_count,
        "reseller_sales_volume": round(reseller_sales_volume, 2),
        "reseller_commissions_paid": round(reseller_commissions_paid, 2),
        "platform_net_revenue": platform_net_revenue,
        "direct_admin_revenue": round(direct_admin_revenue, 2),
        "subscription_health": {
            "active_count": active_count,
            "expiring_soon_count": expiring_soon_count,
            "expired_count": expired_count,
            "total_tenants": len(tenants)
        },
        "sellers_summary": list(seller_stats.values())
    }


@router.get("", response_model=List[PaymentResponse])
async def list_payments(
    tenant_id: Optional[int] = None,
    seller_id: Optional[int] = None,
    source: Optional[str] = "all",
    status_filter: Optional[str] = "all",
    search: Optional[str] = None,
    limit: int = 200,
    skip: int = 0,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """List all recorded cash payments with enhanced reseller attribution and subscription period tracking."""
    # 1. Fetch payments
    stmt = select(Payment).order_by(desc(Payment.received_at))
    if tenant_id:
        stmt = stmt.where(Payment.tenant_id == tenant_id)
    res_p = await db.execute(stmt)
    payments = res_p.scalars().all()

    # 2. Fetch tenants, sellers, packages, transactions
    res_t = await db.execute(select(Tenant))
    tenants = {t.id: t for t in res_t.scalars().all()}

    res_s = await db.execute(select(Seller))
    sellers = {s.id: s for s in res_s.scalars().all()}

    res_pkg = await db.execute(select(SellerPackage))
    packages = {p.id: p for p in res_pkg.scalars().all()}

    res_tx = await db.execute(select(SellerTransaction).order_by(desc(SellerTransaction.id)))
    all_txs = res_tx.scalars().all()
    tx_by_tenant = {}
    for tx in all_txs:
        if tx.tenant_id and tx.tenant_id not in tx_by_tenant:
            tx_by_tenant[tx.tenant_id] = tx

    now_utc = datetime.now(timezone.utc)
    items: List[PaymentResponse] = []

    for p in payments:
        t = tenants.get(p.tenant_id)
        seller = sellers.get(t.seller_id) if (t and t.seller_id) else None
        tx = tx_by_tenant.get(p.tenant_id) if t else None
        pkg = packages.get(t.seller_package_id) if (t and t.seller_package_id) else None
        if not pkg and tx and tx.package_id:
            pkg = packages.get(tx.package_id)

        is_reseller = bool(seller is not None)

        # Source filtering
        if source == "reseller" and not is_reseller:
            continue
        if source == "direct" and is_reseller:
            continue
        if seller_id and (not seller or seller.id != seller_id):
            continue

        # Subscription expiry calculation
        days_remaining = 0
        is_expired = False
        sub_status = "active"

        if t and t.plan_expires_at:
            exp = t.plan_expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp > now_utc:
                days_remaining = (exp - now_utc).days
                is_expired = False
                sub_status = "expiring_soon" if days_remaining <= 5 else "active"
            else:
                days_remaining = -((now_utc - exp).days)
                is_expired = True
                sub_status = "expired"
        else:
            is_expired = True
            sub_status = "expired"

        # Status filter
        if status_filter == "active" and sub_status != "active":
            continue
        if status_filter == "expiring_soon" and sub_status != "expiring_soon":
            continue
        if status_filter == "expired" and sub_status != "expired":
            continue

        # Financial breakdown
        gross = p.amount
        if is_reseller and tx and tx.seller_profit is not None:
            profit = tx.seller_profit
            fee = tx.platform_fee if tx.platform_fee is not None else round(gross - profit, 2)
            comm_rate = tx.commission_rate
            tx_id = tx.id
            tx_type = tx.type
        elif is_reseller and seller:
            comm_rate = seller.commission_rate
            profit = round(gross * (comm_rate / 100.0), 2)
            fee = round(gross - profit, 2)
            tx_id = None
            tx_type = "subscription_sale"
        else:
            comm_rate = 0.0
            profit = 0.0
            fee = gross
            tx_id = None
            tx_type = "direct_cash"

        pkg_name = pkg.name if pkg else (t.plan if t else None)
        pkg_duration = pkg.duration_days if pkg else 30

        # Search filter
        if search and search.strip():
            q = search.strip().lower()
            matches = (
                (t and t.name and q in t.name.lower()) or
                (t and t.phone and q in t.phone.lower()) or
                (seller and seller.name and q in seller.name.lower()) or
                (seller and seller.company_name and q in seller.company_name.lower()) or
                (p.notes and q in p.notes.lower()) or
                (pkg_name and q in pkg_name.lower()) or
                (str(p.id) == q)
            )
            if not matches:
                continue

        resp = PaymentResponse(
            id=p.id,
            tenant_id=p.tenant_id,
            amount=p.amount,
            currency=p.currency,
            period_covered_start=p.period_covered_start,
            period_covered_end=p.period_covered_end,
            received_by=p.received_by,
            received_at=p.received_at,
            notes=p.notes,
            created_at=p.received_at,
            tenant_name=t.name if t else f"Agent #{p.tenant_id}",
            tenant_phone=t.phone if t else None,
            tenant_status=t.status if t else None,
            tenant_plan=t.plan if t else None,
            preferred_channel=t.preferred_channel if t else "telegram",
            plan_expires_at=t.plan_expires_at if t else None,
            days_remaining=days_remaining,
            is_expired=is_expired,
            subscription_status=sub_status,
            seller_id=seller.id if seller else None,
            seller_name=seller.name if seller else None,
            seller_company=seller.company_name if seller else None,
            seller_phone=seller.phone if seller else None,
            seller_rank=seller.rank if seller else None,
            seller_commission_rate=comm_rate,
            is_reseller_sale=is_reseller,
            package_id=pkg.id if pkg else None,
            package_name=pkg_name,
            package_duration_days=pkg_duration,
            gross_amount=gross,
            seller_profit=profit,
            platform_fee=fee,
            transaction_id=tx_id,
            transaction_type=tx_type
        )
        items.append(resp)

    return items[skip:skip + limit]

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
