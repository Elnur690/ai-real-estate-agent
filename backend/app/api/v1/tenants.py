from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin
from app.models.tenant import Tenant
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

class UpdateTenantRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None # active | expired | suspended | pending
    plan: Optional[str] = None
    plan_period: Optional[str] = None
    preferred_channel: Optional[str] = None
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
    addon_saved_searches: int = 0
    active_searches_count: int = 0
    max_saved_searches: int = 10
    referral_code: Optional[str] = None
    referral_balance: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

@router.get("", response_model=List[TenantResponse])
async def list_tenants(db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    from app.models.saved_search import SavedSearch
    from app.models.plan import Plan
    from sqlalchemy import func

    # Fetch plans
    stmt_p = select(Plan)
    res_p = await db.execute(stmt_p)
    plans = {p.code: getattr(p, 'max_saved_searches', 10) for p in res_p.scalars().all()}

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
        resp.append(t_resp)

    return resp

@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(body: CreateTenantRequest, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    from app.models.plan import Plan
    
    plan_code = body.plan.lower().strip()
    is_free = plan_code == "free"

    # Fetch Plan details from database if available
    stmt_p = select(Plan).where(Plan.code == plan_code)
    res_p = await db.execute(stmt_p)
    db_plan = res_p.scalars().first()

    # Paid plans start as 'pending' until cash/subscription payment is recorded
    initial_status = "active" if is_free else "pending"
    trial_days_count = body.trial_days if body.trial_days and body.trial_days > 0 else 7
    expires_at = (datetime.now(timezone.utc) + timedelta(days=trial_days_count)) if is_free else None
    
    tenant = Tenant(
        name=body.name,
        type=body.type,
        phone=body.phone,
        telegram_handle=body.telegram_handle,
        preferred_channel=body.preferred_channel,
        whatsapp_number=body.whatsapp_number,
        telegram_chat_id=body.telegram_chat_id,
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
        plan_started_at=datetime.now(timezone.utc),
        plan_expires_at=expires_at,
        status=initial_status
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
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

    for field, val in update_data.items():
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
