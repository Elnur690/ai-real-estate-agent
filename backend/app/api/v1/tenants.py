from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin
from app.models.tenant import Tenant
from app.models.payment import Payment
from app.models.saved_search import SavedSearch

router = APIRouter(prefix="/tenants", tags=["Tenants"])

class CreateTenantRequest(BaseModel):
    name: str
    phone: str
    type: str = "individual_agent" # individual_agent | agency
    preferred_channel: str = "telegram" # whatsapp | telegram
    telegram_handle: Optional[str] = None
    whatsapp_number: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    plan: str = "starter" # free | starter | pro | agency | enterprise
    plan_period: str = "monthly"
    trial_days: int = 7 # Daily free trial length (e.g. 7 days or 14 days)
    backup_enabled: bool = False
    backup_frequency_days: int = 7 # 1 (daily) | 7 (weekly) | 30 (monthly)
    feature_makler_detector: bool = False
    feature_avm_bargain_finder: bool = False
    feature_social_brochure: bool = False
    feature_client_intake_bot: bool = False
    feature_multi_location: bool = True
    max_locations_per_search: int = 5
    feature_aged_listings: bool = False
    addon_aged_max_months: int = 12
    addon_saved_searches: int = 0
    addon_saved_searches_price: float = 0.0
    feature_watermark_free_images: bool = False
    addon_image_requests_limit: int = 0
    addon_image_requests_price: float = 0.0
    feature_crm: bool = False
    addon_crm_price: float = 0.0
    feature_portfolio: bool = False
    portfolio_limit: int = 25
    addon_portfolio_price: float = 15.0
    portfolio_slug: Optional[str] = None
    feature_custom_domain: bool = False
    custom_domain: Optional[str] = None
    custom_domain_enabled: bool = False
    custom_domain_status: str = "disabled"
    addon_custom_domain_price: float = 5.0

class UpdateTenantRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    telegram_handle: Optional[str] = None
    status: Optional[str] = None # active | expired | suspended | pending
    plan: Optional[str] = None
    plan_period: Optional[str] = None
    preferred_channel: Optional[str] = None
    preferred_billing_day: Optional[int] = None
    whatsapp_number: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    backup_enabled: Optional[bool] = None
    backup_frequency_days: Optional[int] = None
    feature_makler_detector: Optional[bool] = None
    feature_avm_bargain_finder: Optional[bool] = None
    feature_social_brochure: Optional[bool] = None
    feature_client_intake_bot: Optional[bool] = None
    feature_multi_location: Optional[bool] = None
    max_locations_per_search: Optional[int] = None
    feature_aged_listings: Optional[bool] = None
    addon_aged_max_months: Optional[int] = None
    addon_saved_searches: Optional[int] = None
    addon_saved_searches_price: Optional[float] = None
    feature_watermark_free_images: Optional[bool] = None
    addon_image_requests_limit: Optional[int] = None
    addon_image_requests_used: Optional[int] = None
    addon_image_requests_price: Optional[float] = None
    feature_crm: Optional[bool] = None
    addon_crm_price: Optional[float] = None
    feature_portfolio: Optional[bool] = None
    portfolio_limit: Optional[int] = None
    addon_portfolio_price: Optional[float] = None
    portfolio_slug: Optional[str] = None
    feature_custom_domain: Optional[bool] = None
    custom_domain: Optional[str] = None
    custom_domain_enabled: Optional[bool] = None
    custom_domain_status: Optional[str] = None
    addon_custom_domain_price: Optional[float] = None

class TenantResponse(BaseModel):
    id: int
    name: str
    type: str
    phone: str
    telegram_handle: Optional[str] = None
    plan: str
    plan_period: str
    plan_started_at: Optional[datetime] = None
    plan_expires_at: Optional[datetime] = None
    preferred_billing_day: Optional[int] = 1
    status: str
    preferred_channel: str
    whatsapp_number: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    digest_mode: str
    backup_enabled: bool
    backup_frequency_days: int
    last_backup_at: Optional[datetime] = None
    feature_makler_detector: bool
    feature_avm_bargain_finder: bool
    feature_social_brochure: bool
    feature_client_intake_bot: bool
    feature_multi_location: bool = True
    max_locations_per_search: int = 5
    feature_aged_listings: bool = False
    addon_aged_max_months: int = 12
    aged_expires_at: Optional[datetime] = None
    addon_saved_searches: int = 0
    feature_watermark_free_images: bool = False
    addon_image_requests_limit: int = 0
    addon_image_requests_used: int = 0
    addon_image_requests_price: float = 0.0
    feature_crm: bool = False
    addon_crm_price: float = 0.0
    crm_expires_at: Optional[datetime] = None
    feature_portfolio: bool = False
    portfolio_limit: int = 25
    addon_portfolio_price: float = 15.0
    portfolio_expires_at: Optional[datetime] = None
    portfolio_slug: Optional[str] = None
    portfolio_vitrin_url: Optional[str] = None
    feature_custom_domain: bool = False
    custom_domain: Optional[str] = None
    custom_domain_enabled: bool = False
    custom_domain_status: str = "disabled"
    addon_custom_domain_price: float = 5.0
    custom_domain_expires_at: Optional[datetime] = None
    active_searches_count: int = 0
    max_saved_searches: int = 10
    referral_code: Optional[str] = None
    referral_balance: float
    seller_id: Optional[int] = None
    seller_name: Optional[str] = None
    seller_company: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

@router.get("", response_model=List[TenantResponse])
async def list_tenants(db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    from app.models.saved_search import SavedSearch
    from app.models.plan import Plan
    from app.models.seller import Seller
    from sqlalchemy import func

    # Fetch plans
    stmt_p = select(Plan)
    res_p = await db.execute(stmt_p)
    plans = {p.code: getattr(p, 'max_saved_searches', 10) for p in res_p.scalars().all()}

    # Fetch sellers
    stmt_s = select(Seller)
    res_s = await db.execute(stmt_s)
    sellers_dict = {s.id: s for s in res_s.scalars().all()}

    # Fetch active search counts
    stmt_c = select(SavedSearch.tenant_id, func.count(SavedSearch.id)).where(SavedSearch.is_active == True).group_by(SavedSearch.tenant_id)
    res_c = await db.execute(stmt_c)
    counts = dict(res_c.all())

    stmt = select(Tenant).order_by(Tenant.id.desc())
    res = await db.execute(stmt)
    tenants = res.scalars().all()

    resp = []
    for t in tenants:
        base_lim = plans.get(t.plan, 10)
        total_lim = base_lim + (t.addon_saved_searches or 0)
        t_resp = TenantResponse.model_validate(t)
        t_resp.active_searches_count = counts.get(t.id, 0)
        t_resp.max_saved_searches = total_lim
        
        seller_obj = sellers_dict.get(t.seller_id) if t.seller_id else None
        t_resp.seller_id = t.seller_id
        t_resp.seller_name = seller_obj.name if seller_obj else None
        t_resp.seller_company = seller_obj.company_name if seller_obj else None
        if t.feature_custom_domain and t.custom_domain_enabled and t.custom_domain:
            t_resp.portfolio_vitrin_url = f"https://{t.custom_domain}/v/{t.portfolio_slug or t.id}"
        elif seller_obj and seller_obj.custom_domain_enabled and seller_obj.custom_domain:
            t_resp.portfolio_vitrin_url = f"https://{seller_obj.custom_domain}/v/{t.portfolio_slug or t.id}"
        else:
            t_resp.portfolio_vitrin_url = f"/v/{t.portfolio_slug or t.id}"
        
        resp.append(t_resp)

    return resp

async def ensure_unique_slug(db: AsyncSession, base_slug: str, tenant_id: Optional[int] = None) -> str:
    """Ensures a tenant portfolio slug is strictly unique across the database."""
    from app.models.tenant import Tenant
    clean_base = base_slug.strip().lower() or "agent"
    slug = clean_base
    idx = 1
    while True:
        stmt = select(Tenant).where(Tenant.portfolio_slug == slug)
        if tenant_id:
            stmt = stmt.where(Tenant.id != tenant_id)
        res = await db.execute(stmt)
        if not res.scalars().first():
            return slug
        idx += 1
        slug = f"{clean_base}-{idx}"

@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(body: CreateTenantRequest, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    from app.models.plan import Plan
    from app.models.payment import Payment
    from app.models.tenant import slugify_portfolio_name
    
    plan_code = body.plan.lower().strip()
    is_free = plan_code == "free"

    # Fetch Plan details from database if available
    stmt_p = select(Plan).where(Plan.code == plan_code)
    res_p = await db.execute(stmt_p)
    db_plan = res_p.scalars().first()

    now_utc = datetime.now(timezone.utc)
    trial_days_count = body.trial_days if (body.trial_days and body.trial_days > 0) else (7 if is_free else 30)
    expires_at = now_utc + timedelta(days=trial_days_count)

    # Normalize telegram handle and chat_id
    raw_handle = body.telegram_handle.strip().lstrip('@') if body.telegram_handle else None
    raw_chat_id = body.telegram_chat_id.strip() if body.telegram_chat_id else None
    
    if raw_handle and raw_handle.isdigit() and not raw_chat_id:
        raw_chat_id = raw_handle
    elif raw_chat_id and raw_chat_id.isdigit() and not raw_handle:
        raw_handle = raw_chat_id

    has_crm = getattr(db_plan, 'feature_crm', False) or body.feature_crm
    crm_exp = expires_at if has_crm else None

    has_portfolio = getattr(db_plan, 'feature_portfolio', False) or body.feature_portfolio
    portfolio_limit = getattr(db_plan, 'addon_portfolio_limit', 25) or body.portfolio_limit or 25
    portfolio_price = (body.addon_portfolio_price or getattr(db_plan, 'addon_portfolio_price', 15.0) or 15.0) if has_portfolio else 0.0
    portfolio_exp = expires_at if has_portfolio else None

    raw_slug = slugify_portfolio_name(body.portfolio_slug or body.name or "agent")
    unique_slug = await ensure_unique_slug(db, raw_slug)
    
    tenant = Tenant(
        name=body.name,
        type=body.type,
        phone=body.phone,
        telegram_handle=raw_handle,
        preferred_channel=body.preferred_channel,
        whatsapp_number=body.whatsapp_number,
        telegram_chat_id=raw_chat_id,
        plan=plan_code,
        plan_period=body.plan_period,
        backup_enabled=db_plan.backup_enabled if db_plan else body.backup_enabled,
        backup_frequency_days=body.backup_frequency_days,
        feature_makler_detector=db_plan.feature_makler_detector if db_plan else True,
        feature_avm_bargain_finder=db_plan.feature_avm_bargain_finder if db_plan else True,
        feature_social_brochure=db_plan.feature_social_brochure if db_plan else True,
        feature_client_intake_bot=db_plan.feature_client_intake_bot if db_plan else True,
        feature_multi_location=db_plan.feature_multi_location if db_plan else body.feature_multi_location,
        max_locations_per_search=db_plan.max_locations_per_search if db_plan else body.max_locations_per_search,
        feature_aged_listings=getattr(db_plan, 'feature_aged_listings', False) or body.feature_aged_listings,
        addon_aged_max_months=body.addon_aged_max_months or 12,
        aged_expires_at=expires_at if (getattr(db_plan, 'feature_aged_listings', False) or body.feature_aged_listings) else None,
        feature_crm=has_crm,
        addon_crm_price=getattr(db_plan, 'addon_crm_price', 0.0) if body.addon_crm_price == 0.0 else body.addon_crm_price,
        crm_expires_at=crm_exp,
        feature_portfolio=has_portfolio,
        portfolio_limit=portfolio_limit,
        portfolio_expires_at=portfolio_exp,
        addon_portfolio_price=portfolio_price,
        portfolio_slug=unique_slug,
        plan_started_at=now_utc,
        plan_expires_at=expires_at,
        status="active"
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    # Automatically create confirmed initial Payment record
    plan_price = db_plan.price if (db_plan and not is_free) else 0.0
    crm_price = (body.addon_crm_price or getattr(db_plan, 'addon_crm_price', 15.0) or 15.0) if has_crm else 0.0
    aged_price = (getattr(db_plan, 'addon_aged_listings_price', 15.0) or 15.0) if tenant.feature_aged_listings else 0.0
    port_fee = portfolio_price if has_portfolio else 0.0
    total_amount = round(plan_price + crm_price + aged_price + port_fee, 2)

    pay_record = Payment(
        tenant_id=tenant.id,
        amount=total_amount,
        currency="AZN",
        period_covered_start=now_utc,
        period_covered_end=expires_at,
        received_by=current_admin.id,
        received_at=now_utc,
        notes=f"Initial Provisioning: {tenant.name} ({plan_code.upper()} Plan) [CRM: {'Active' if has_crm else 'Off'}, Portfel: {'Active (' + str(portfolio_limit) + ')' if has_portfolio else 'Off'}]"
    )
    db.add(pay_record)
    await db.commit()

    return tenant

@router.get("/{tenant_id}")
async def get_tenant_detail(tenant_id: int, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get active saved searches count
    stmt_s = select(SavedSearch).where(SavedSearch.tenant_id == tenant_id, SavedSearch.is_active == True)
    res_s = await db.execute(stmt_s)
    searches = res_s.scalars().all()

    return {
        "tenant": TenantResponse.model_validate(tenant),
        "saved_searches": searches
    }

@router.delete("/{tenant_id}/saved-searches/{search_id}")
async def delete_saved_search(tenant_id: int, search_id: int, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    from sqlalchemy import update
    stmt = update(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.tenant_id == tenant_id).values(is_active=False)
    await db.execute(stmt)
    await db.commit()
    return {"status": "deleted", "search_id": search_id}

@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(tenant_id: int, body: UpdateTenantRequest, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    update_data = body.model_dump(exclude_unset=True)

    # Handle telegram username and chat_id normalization
    if "telegram_handle" in update_data:
        h = (update_data["telegram_handle"] or "").strip().lstrip('@')
        tenant.telegram_handle = h or None
        if h and h.isdigit() and not update_data.get("telegram_chat_id"):
            tenant.telegram_chat_id = h

    if "telegram_chat_id" in update_data:
        cid = (update_data["telegram_chat_id"] or "").strip()
        tenant.telegram_chat_id = cid or None
        if cid and cid.isdigit() and not tenant.telegram_handle:
            tenant.telegram_handle = cid

    now_utc = datetime.now(timezone.utc)

    # CRM feature update & payment creation if newly activated
    if "feature_crm" in update_data:
        new_crm = bool(update_data["feature_crm"])
        was_crm = tenant.feature_crm
        tenant.feature_crm = new_crm
        if new_crm:
            if not tenant.crm_expires_at or tenant.crm_expires_at < now_utc:
                tenant.crm_expires_at = tenant.plan_expires_at or (now_utc + timedelta(days=30))
            if not was_crm:
                crm_price = tenant.addon_crm_price if (tenant.addon_crm_price and tenant.addon_crm_price > 0) else 15.0
                pay_record = Payment(
                    tenant_id=tenant.id,
                    amount=round(crm_price, 2),
                    currency="AZN",
                    period_covered_start=now_utc,
                    period_covered_end=tenant.crm_expires_at,
                    received_by=current_admin.id,
                    received_at=now_utc,
                    notes=f"Add-on Activation: CRM Mini App for {tenant.name}"
                )
                db.add(pay_record)
        else:
            tenant.addon_crm_price = 0.0

    # Portfolio feature update & payment creation if newly activated
    if "feature_portfolio" in update_data:
        new_portfolio = bool(update_data["feature_portfolio"])
        was_portfolio = tenant.feature_portfolio
        tenant.feature_portfolio = new_portfolio
        if new_portfolio:
            if not tenant.portfolio_expires_at or tenant.portfolio_expires_at < now_utc:
                tenant.portfolio_expires_at = tenant.plan_expires_at or (now_utc + timedelta(days=30))
            if "portfolio_limit" in update_data and update_data["portfolio_limit"]:
                tenant.portfolio_limit = int(update_data["portfolio_limit"])
            if "addon_portfolio_price" in update_data and update_data["addon_portfolio_price"] is not None:
                tenant.addon_portfolio_price = float(update_data["addon_portfolio_price"])
            if not was_portfolio:
                port_price = tenant.addon_portfolio_price if (tenant.addon_portfolio_price and tenant.addon_portfolio_price > 0) else 15.0
                pay_record = Payment(
                    tenant_id=tenant.id,
                    amount=round(port_price, 2),
                    currency="AZN",
                    period_covered_start=now_utc,
                    period_covered_end=tenant.portfolio_expires_at,
                    received_by=current_admin.id,
                    received_at=now_utc,
                    notes=f"Add-on Activation: Agent Portfolio ({tenant.portfolio_limit or 25} elan) for {tenant.name}"
                )
                db.add(pay_record)
        else:
            tenant.addon_portfolio_price = 0.0

    # Portfolio slug customization
    if "portfolio_slug" in update_data and update_data["portfolio_slug"]:
        from app.models.tenant import slugify_portfolio_name
        req_slug = slugify_portfolio_name(str(update_data["portfolio_slug"]))
        tenant.portfolio_slug = await ensure_unique_slug(db, req_slug, tenant_id=tenant.id)
    elif not tenant.portfolio_slug and tenant.name:
        from app.models.tenant import slugify_portfolio_name
        tenant.portfolio_slug = await ensure_unique_slug(db, slugify_portfolio_name(tenant.name), tenant_id=tenant.id)

    # If plan is updated, fetch new plan features if available
    if "plan" in update_data and update_data["plan"]:
        plan_code = update_data["plan"].lower().strip()
        from app.models.plan import Plan
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
            if getattr(db_plan, 'feature_aged_listings', False):
                tenant.feature_aged_listings = True
            if getattr(db_plan, 'feature_crm', False):
                tenant.feature_crm = True
                if not tenant.crm_expires_at:
                    tenant.crm_expires_at = tenant.plan_expires_at or (datetime.now(timezone.utc) + timedelta(days=30))
            if getattr(db_plan, 'feature_portfolio', False):
                tenant.feature_portfolio = True
                tenant.portfolio_limit = getattr(db_plan, 'addon_portfolio_limit', 25) or 25
                if not tenant.portfolio_expires_at:
                    tenant.portfolio_expires_at = tenant.plan_expires_at or (datetime.now(timezone.utc) + timedelta(days=30))
            if getattr(db_plan, 'feature_custom_domain', False):
                tenant.feature_custom_domain = True
                if not tenant.custom_domain_expires_at:
                    tenant.custom_domain_expires_at = tenant.plan_expires_at or (datetime.now(timezone.utc) + timedelta(days=30))

    if "custom_domain" in update_data and update_data["custom_domain"]:
        from app.services.domain_service import clean_domain_string
        update_data["custom_domain"] = clean_domain_string(update_data["custom_domain"])

    for field, val in update_data.items():
        if field not in ["telegram_handle", "telegram_chat_id", "feature_crm", "feature_portfolio"]:
            setattr(tenant, field, val)

    await db.commit()
    await db.refresh(tenant)
    return tenant

class TenantCashPaymentRequest(BaseModel):
    plan: Optional[str] = None
    duration_days: int = 30
    amount_paid: Optional[float] = None
    amount: Optional[float] = None
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

@router.post("/{tenant_id}/cash-payment")
async def record_tenant_cash_payment(
    tenant_id: int,
    body: TenantCashPaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    from app.api.v1.payments import process_tenant_cash_payment
    amt = body.amount_paid if body.amount_paid is not None else body.amount
    payment = await process_tenant_cash_payment(
        db=db,
        current_admin_id=current_admin.id,
        tenant_id=tenant_id,
        amount=amt,
        days_covered=body.duration_days,
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
    return {
        "status": "success",
        "payment_id": payment.id,
        "amount": payment.amount,
        "period_covered_start": payment.period_covered_start,
        "period_covered_end": payment.period_covered_end
    }

@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(tenant_id: int, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    await db.delete(tenant)
    await db.commit()
    return None

class CreateSubAgentRequest(BaseModel):
    name: str
    phone: str
    preferred_channel: str = "telegram"
    whatsapp_number: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    assigned_districts: List[str] = []

@router.post("/{tenant_id}/sub-agents", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_sub_agent(tenant_id: int, body: CreateSubAgentRequest, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    res = await db.execute(stmt)
    parent = res.scalars().first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent Agency tenant not found")

    # Validate max_agents limit
    from app.models.plan import Plan
    stmt_plan = select(Plan).where(Plan.code == parent.plan)
    res_plan = await db.execute(stmt_plan)
    plan_obj = res_plan.scalars().first()
    max_seats = plan_obj.max_agents if plan_obj else 1

    stmt_count = select(Tenant).where(Tenant.parent_tenant_id == parent.id)
    res_count = await db.execute(stmt_count)
    existing_sub_agents = res_count.scalars().all()

    if len(existing_sub_agents) + 1 >= max_seats:
        raise HTTPException(
            status_code=400,
            detail=f"Maksimum agent limiti ({max_seats} nəfər) dolub. Yeni agent əlavə etmək üçün planı yüksəldin."
        )

    sub_agent = Tenant(
        name=body.name,
        type="individual_agent",
        phone=body.phone,
        preferred_channel=body.preferred_channel,
        whatsapp_number=body.whatsapp_number,
        telegram_chat_id=body.telegram_chat_id,
        parent_tenant_id=parent.id,
        assigned_districts=body.assigned_districts,
        plan=parent.plan,
        status="active"
    )
    db.add(sub_agent)
    await db.commit()
    await db.refresh(sub_agent)
    return sub_agent

@router.get("/{tenant_id}/sub-agents", response_model=List[TenantResponse])
async def list_sub_agents(tenant_id: int, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    stmt = select(Tenant).where(Tenant.parent_tenant_id == tenant_id)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/{tenant_id}/backup")
async def trigger_tenant_backup(tenant_id: int, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Trigger manual instant data backup export for a specific tenant."""
    from app.services.backup import BackupService
    res = await BackupService.create_tenant_backup(db, tenant_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Tenant backup failed"))
    return res

@router.post("/check-trials")
async def trigger_trial_check(db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Check for expired free trials, mark status expired, and send automated plan offer notifications."""
    from app.services.trial_tracker import TrialTrackerService
    await TrialTrackerService.check_and_notify_expired_trials(db)
    return {"status": "completed", "message": "Trial expiration check complete."}


class MoveTenantSellerRequest(BaseModel):
    seller_id: Optional[int] = None  # None to unassign to direct platform


@router.put("/{tenant_id}/seller")
async def move_tenant_seller(
    tenant_id: int,
    body: MoveTenantSellerRequest,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    Admin-only: Move/Reassign an agent to a different seller or to direct platform.
    Agent's active searches, plans, and preferences stay completely intact and unaffected.
    """
    from app.models.seller import Seller
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Agent tapılmadı")

    seller_name = "Direkt Platforma"
    if body.seller_id is not None:
        s_stmt = select(Seller).where(Seller.id == body.seller_id)
        s_res = await db.execute(s_stmt)
        seller = s_res.scalars().first()
        if not seller:
            raise HTTPException(status_code=404, detail="Satıcı tapılmadı")
        seller_name = seller.name

    tenant.seller_id = body.seller_id
    await db.commit()
    await db.refresh(tenant)

    return {
        "status": "success",
        "message": f"Agent uğurla '{seller_name}' hesabına köçürüldü. Agentin axtarışları və planı toxunulmaz qaldı.",
        "tenant_id": tenant.id,
        "seller_id": tenant.seller_id,
        "seller_name": seller_name
    }
