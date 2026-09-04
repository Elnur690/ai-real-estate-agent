import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin
from app.models.plan import Plan
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/plans", tags=["Plans"])


class PlanResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    price: float
    currency: str
    billing_period: str
    trial_days: Optional[int] = 7
    is_active: bool
    max_agents: int
    feature_makler_detector: bool
    feature_avm_bargain_finder: bool
    feature_social_brochure: bool
    feature_client_intake_bot: bool
    feature_multi_location: bool = True
    max_locations_per_search: int = 5
    feature_aged_listings: bool = False
    addon_aged_listings_price: float = 0.0
    addon_aged_max_months: int = 12
    addon_aged_tiers: Optional[List[dict]] = []
    max_saved_searches: int = 10
    addon_saved_searches: int = 0
    addon_saved_searches_price: float = 10.0
    addon_search_tiers: Optional[List[dict]] = []
    feature_watermark_free_images: bool = False
    included_image_requests: int = 0
    addon_image_requests_price: float = 10.0
    addon_image_tiers: Optional[List[dict]] = []
    feature_crm: bool = False
    addon_crm_price: float = 15.0
    addon_crm_tiers: Optional[List[dict]] = []
    feature_portfolio: bool = False
    addon_portfolio_price: float = 15.0
    addon_portfolio_limit: int = 25
    addon_portfolio_tiers: Optional[List[dict]] = []
    feature_custom_domain: bool = False
    addon_custom_domain_price: float = 5.0
    sale_enabled: bool = False
    sale_price: Optional[float] = None
    sale_discount_percent: Optional[float] = None
    sale_type: str = "permanent"
    sale_expires_at: Optional[str] = None
    sale_badge_label: Optional[str] = None
    backup_enabled: bool
    subscriber_count: int = 0


class CreatePlanRequest(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    price: float = 0.0
    currency: str = "AZN"
    billing_period: str = "monthly"  # daily | monthly | quarterly | annual | lifetime
    trial_days: Optional[int] = 7
    is_active: bool = True
    max_agents: int = 1
    feature_makler_detector: bool = True
    feature_avm_bargain_finder: bool = True
    feature_social_brochure: bool = True
    feature_client_intake_bot: bool = True
    feature_multi_location: bool = True
    max_locations_per_search: int = 5
    feature_aged_listings: bool = False
    addon_aged_listings_price: float = 0.0
    addon_aged_max_months: int = 12
    addon_aged_tiers: Optional[List[dict]] = []
    max_saved_searches: int = 10
    addon_saved_searches: int = 0
    addon_saved_searches_price: float = 10.0
    addon_search_tiers: Optional[List[dict]] = []
    feature_watermark_free_images: bool = False
    included_image_requests: int = 0
    addon_image_requests_price: float = 10.0
    addon_image_tiers: Optional[List[dict]] = []
    feature_crm: bool = False
    addon_crm_price: float = 15.0
    addon_crm_tiers: Optional[List[dict]] = []
    feature_portfolio: bool = False
    addon_portfolio_price: float = 15.0
    addon_portfolio_limit: int = 25
    addon_portfolio_tiers: Optional[List[dict]] = []
    feature_custom_domain: bool = False
    addon_custom_domain_price: float = 5.0
    sale_enabled: bool = False
    sale_price: Optional[float] = None
    sale_discount_percent: Optional[float] = None
    sale_type: str = "permanent"
    sale_expires_at: Optional[str] = None
    sale_badge_label: Optional[str] = None
    backup_enabled: bool = True


class UpdatePlanRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    billing_period: Optional[str] = None
    trial_days: Optional[int] = None
    is_active: Optional[bool] = None
    max_agents: Optional[int] = None
    feature_makler_detector: Optional[bool] = None
    feature_avm_bargain_finder: Optional[bool] = None
    feature_social_brochure: Optional[bool] = None
    feature_client_intake_bot: Optional[bool] = None
    feature_multi_location: Optional[bool] = None
    max_locations_per_search: Optional[int] = None
    feature_aged_listings: Optional[bool] = None
    addon_aged_listings_price: Optional[float] = None
    addon_aged_max_months: Optional[int] = None
    addon_aged_tiers: Optional[List[dict]] = None
    max_saved_searches: Optional[int] = None
    addon_saved_searches: Optional[int] = None
    addon_saved_searches_price: Optional[float] = None
    addon_search_tiers: Optional[List[dict]] = None
    feature_watermark_free_images: Optional[bool] = None
    included_image_requests: Optional[int] = None
    addon_image_requests_price: Optional[float] = None
    addon_image_tiers: Optional[List[dict]] = None
    feature_crm: Optional[bool] = None
    addon_crm_price: Optional[float] = None
    addon_crm_tiers: Optional[List[dict]] = None
    feature_portfolio: Optional[bool] = None
    addon_portfolio_price: Optional[float] = None
    addon_portfolio_limit: Optional[int] = None
    addon_portfolio_tiers: Optional[List[dict]] = None
    feature_custom_domain: Optional[bool] = None
    addon_custom_domain_price: Optional[float] = None
    sale_enabled: Optional[bool] = None
    sale_price: Optional[float] = None
    sale_discount_percent: Optional[float] = None
    sale_type: Optional[str] = None
    sale_expires_at: Optional[str] = None
    sale_badge_label: Optional[str] = None
    backup_enabled: Optional[bool] = None


@router.get("", response_model=List[PlanResponse])
async def list_plans(db: AsyncSession = Depends(get_db)):
    """List all available subscription plans with subscriber counts."""
    stmt = select(Plan).order_by(Plan.price.asc())
    res = await db.execute(stmt)
    plans = res.scalars().all()

    # Pre-fetch all subscriber counts grouped by plan in a single query
    sub_counts_stmt = select(Tenant.plan, func.count(Tenant.id)).group_by(Tenant.plan)
    sub_counts_res = await db.execute(sub_counts_stmt)
    sub_counts_map = dict(sub_counts_res.all())

    response_list = []
    for plan in plans:
        sub_count = sub_counts_map.get(plan.code, 0)

        response_list.append(PlanResponse(
            id=plan.id,
            code=plan.code,
            name=plan.name,
            description=plan.description,
            price=plan.price,
            currency=plan.currency,
            billing_period=plan.billing_period,
            trial_days=plan.trial_days or 7,
            is_active=plan.is_active,
            max_agents=plan.max_agents,
            feature_makler_detector=plan.feature_makler_detector,
            feature_avm_bargain_finder=plan.feature_avm_bargain_finder,
            feature_social_brochure=plan.feature_social_brochure,
            feature_client_intake_bot=plan.feature_client_intake_bot,
            feature_multi_location=getattr(plan, 'feature_multi_location', True),
            max_locations_per_search=getattr(plan, 'max_locations_per_search', 5),
            feature_aged_listings=getattr(plan, 'feature_aged_listings', False),
            addon_aged_listings_price=getattr(plan, 'addon_aged_listings_price', 0.0),
            addon_aged_max_months=getattr(plan, 'addon_aged_max_months', 12),
            addon_aged_tiers=getattr(plan, 'addon_aged_tiers', []) or [],
            max_saved_searches=getattr(plan, 'max_saved_searches', 10),
            addon_saved_searches=getattr(plan, 'addon_saved_searches', 0),
            addon_saved_searches_price=getattr(plan, 'addon_saved_searches_price', 10.0),
            addon_search_tiers=getattr(plan, 'addon_search_tiers', []) or [],
            feature_watermark_free_images=getattr(plan, 'feature_watermark_free_images', False),
            included_image_requests=getattr(plan, 'included_image_requests', 0),
            addon_image_requests_price=getattr(plan, 'addon_image_requests_price', 10.0),
            addon_image_tiers=getattr(plan, 'addon_image_tiers', []) or [],
            feature_crm=getattr(plan, 'feature_crm', False),
            addon_crm_price=getattr(plan, 'addon_crm_price', 15.0),
            addon_crm_tiers=getattr(plan, 'addon_crm_tiers', []) or [],
            feature_portfolio=getattr(plan, 'feature_portfolio', False),
            addon_portfolio_price=getattr(plan, 'addon_portfolio_price', 15.0),
            addon_portfolio_limit=getattr(plan, 'addon_portfolio_limit', 25),
            addon_portfolio_tiers=getattr(plan, 'addon_portfolio_tiers', []) or [],
            feature_custom_domain=getattr(plan, 'feature_custom_domain', False),
            addon_custom_domain_price=getattr(plan, 'addon_custom_domain_price', 5.0) or 5.0,
            sale_enabled=getattr(plan, 'sale_enabled', False),
            sale_price=getattr(plan, 'sale_price', None),
            sale_discount_percent=getattr(plan, 'sale_discount_percent', None),
            sale_type=getattr(plan, 'sale_type', 'permanent'),
            sale_expires_at=plan.sale_expires_at.isoformat() if getattr(plan, 'sale_expires_at', None) else None,
            sale_badge_label=getattr(plan, 'sale_badge_label', None),
            backup_enabled=plan.backup_enabled,
            subscriber_count=sub_count
        ))

    return response_list


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    body: CreatePlanRequest,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Create a new subscription plan (Admin only)."""
    stmt = select(Plan).where(Plan.code == body.code.lower().strip())
    res = await db.execute(stmt)
    if res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan code '{body.code}' already exists."
        )

    # Calculate sale price & discount percent
    final_sale_price = body.sale_price
    final_discount_pct = body.sale_discount_percent
    if body.sale_enabled:
        if final_sale_price is None and final_discount_pct is not None and final_discount_pct > 0:
            final_sale_price = round(body.price * (1 - final_discount_pct / 100.0), 2)
        elif final_sale_price is not None and final_discount_pct is None and body.price > 0:
            final_discount_pct = round(((body.price - final_sale_price) / body.price) * 100.0, 1)

    plan = Plan(
        code=body.code.lower().strip(),
        name=body.name.strip(),
        description=body.description,
        price=body.price,
        currency=body.currency.upper(),
        billing_period=body.billing_period,
        trial_days=body.trial_days or 7,
        is_active=body.is_active,
        max_agents=body.max_agents,
        feature_makler_detector=body.feature_makler_detector,
        feature_avm_bargain_finder=body.feature_avm_bargain_finder,
        feature_social_brochure=body.feature_social_brochure,
        feature_client_intake_bot=body.feature_client_intake_bot,
        feature_multi_location=body.feature_multi_location,
        max_locations_per_search=body.max_locations_per_search,
        feature_aged_listings=body.feature_aged_listings,
        addon_aged_listings_price=body.addon_aged_listings_price,
        addon_aged_max_months=body.addon_aged_max_months,
        addon_aged_tiers=body.addon_aged_tiers or [],
        max_saved_searches=body.max_saved_searches,
        addon_saved_searches=body.addon_saved_searches,
        addon_saved_searches_price=body.addon_saved_searches_price,
        addon_search_tiers=body.addon_search_tiers or [],
        feature_watermark_free_images=body.feature_watermark_free_images,
        included_image_requests=body.included_image_requests,
        addon_image_requests_price=body.addon_image_requests_price,
        addon_image_tiers=body.addon_image_tiers or [],
        feature_crm=body.feature_crm,
        addon_crm_price=body.addon_crm_price,
        addon_crm_tiers=body.addon_crm_tiers or [],
        feature_portfolio=body.feature_portfolio,
        addon_portfolio_price=body.addon_portfolio_price,
        addon_portfolio_limit=body.addon_portfolio_limit,
        addon_portfolio_tiers=body.addon_portfolio_tiers or [],
        feature_custom_domain=body.feature_custom_domain,
        addon_custom_domain_price=body.addon_custom_domain_price,
        sale_enabled=body.sale_enabled,
        sale_price=final_sale_price,
        sale_discount_percent=final_discount_pct,
        sale_type=body.sale_type or "permanent",
        sale_expires_at=(datetime.fromisoformat(body.sale_expires_at) if body.sale_expires_at else None),
        sale_badge_label=body.sale_badge_label,
        backup_enabled=body.backup_enabled
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return PlanResponse(
        id=plan.id,
        code=plan.code,
        name=plan.name,
        description=plan.description,
        price=plan.price,
        currency=plan.currency,
        billing_period=plan.billing_period,
        trial_days=plan.trial_days or 7,
        is_active=plan.is_active,
        max_agents=plan.max_agents,
        feature_makler_detector=plan.feature_makler_detector,
        feature_avm_bargain_finder=plan.feature_avm_bargain_finder,
        feature_social_brochure=plan.feature_social_brochure,
        feature_client_intake_bot=plan.feature_client_intake_bot,
        feature_multi_location=plan.feature_multi_location,
        max_locations_per_search=plan.max_locations_per_search,
        feature_aged_listings=plan.feature_aged_listings,
        addon_aged_listings_price=plan.addon_aged_listings_price,
        addon_aged_max_months=getattr(plan, 'addon_aged_max_months', 12),
        addon_aged_tiers=getattr(plan, 'addon_aged_tiers', []) or [],
        max_saved_searches=plan.max_saved_searches,
        addon_saved_searches=getattr(plan, 'addon_saved_searches', 0),
        addon_saved_searches_price=plan.addon_saved_searches_price,
        addon_search_tiers=getattr(plan, 'addon_search_tiers', []) or [],
        feature_watermark_free_images=getattr(plan, 'feature_watermark_free_images', False),
        included_image_requests=getattr(plan, 'included_image_requests', 0),
        addon_image_requests_price=getattr(plan, 'addon_image_requests_price', 10.0),
        addon_image_tiers=getattr(plan, 'addon_image_tiers', []) or [],
        feature_crm=getattr(plan, 'feature_crm', False),
        addon_crm_price=getattr(plan, 'addon_crm_price', 15.0),
        addon_crm_tiers=getattr(plan, 'addon_crm_tiers', []) or [],
        feature_portfolio=getattr(plan, 'feature_portfolio', False),
        addon_portfolio_price=getattr(plan, 'addon_portfolio_price', 15.0),
        addon_portfolio_limit=getattr(plan, 'addon_portfolio_limit', 25),
        addon_portfolio_tiers=getattr(plan, 'addon_portfolio_tiers', []) or [],
        feature_custom_domain=getattr(plan, 'feature_custom_domain', False),
        addon_custom_domain_price=getattr(plan, 'addon_custom_domain_price', 5.0) or 5.0,
        sale_enabled=getattr(plan, 'sale_enabled', False),
        sale_price=getattr(plan, 'sale_price', None),
        sale_discount_percent=getattr(plan, 'sale_discount_percent', None),
        sale_type=getattr(plan, 'sale_type', 'permanent'),
        sale_expires_at=plan.sale_expires_at.isoformat() if getattr(plan, 'sale_expires_at', None) else None,
        sale_badge_label=getattr(plan, 'sale_badge_label', None),
        backup_enabled=plan.backup_enabled,
        subscriber_count=0
    )


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Get plan details by ID."""
    stmt = select(Plan).where(Plan.id == plan_id)
    res = await db.execute(stmt)
    plan = res.scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")

    stmt_count = select(func.count(Tenant.id)).where(Tenant.plan == plan.code)
    res_count = await db.execute(stmt_count)
    sub_count = res_count.scalar() or 0

    return PlanResponse(
        id=plan.id,
        code=plan.code,
        name=plan.name,
        description=plan.description,
        price=plan.price,
        currency=plan.currency,
        billing_period=plan.billing_period,
        trial_days=plan.trial_days or 7,
        is_active=plan.is_active,
        max_agents=plan.max_agents,
        feature_makler_detector=plan.feature_makler_detector,
        feature_avm_bargain_finder=plan.feature_avm_bargain_finder,
        feature_social_brochure=plan.feature_social_brochure,
        feature_client_intake_bot=plan.feature_client_intake_bot,
        feature_multi_location=getattr(plan, 'feature_multi_location', True),
        max_locations_per_search=getattr(plan, 'max_locations_per_search', 5),
        feature_aged_listings=getattr(plan, 'feature_aged_listings', False),
        addon_aged_listings_price=getattr(plan, 'addon_aged_listings_price', 0.0),
        addon_aged_max_months=getattr(plan, 'addon_aged_max_months', 12),
        addon_aged_tiers=getattr(plan, 'addon_aged_tiers', []) or [],
        max_saved_searches=getattr(plan, 'max_saved_searches', 10),
        addon_saved_searches=getattr(plan, 'addon_saved_searches', 0),
        addon_saved_searches_price=getattr(plan, 'addon_saved_searches_price', 10.0),
        addon_search_tiers=getattr(plan, 'addon_search_tiers', []) or [],
        feature_watermark_free_images=getattr(plan, 'feature_watermark_free_images', False),
        included_image_requests=getattr(plan, 'included_image_requests', 0),
        addon_image_requests_price=getattr(plan, 'addon_image_requests_price', 10.0),
        addon_image_tiers=getattr(plan, 'addon_image_tiers', []) or [],
        feature_crm=getattr(plan, 'feature_crm', False),
        addon_crm_price=getattr(plan, 'addon_crm_price', 15.0),
        addon_crm_tiers=getattr(plan, 'addon_crm_tiers', []) or [],
        feature_portfolio=getattr(plan, 'feature_portfolio', False),
        addon_portfolio_price=getattr(plan, 'addon_portfolio_price', 15.0),
        addon_portfolio_limit=getattr(plan, 'addon_portfolio_limit', 25),
        addon_portfolio_tiers=getattr(plan, 'addon_portfolio_tiers', []) or [],
        feature_custom_domain=getattr(plan, 'feature_custom_domain', False),
        addon_custom_domain_price=getattr(plan, 'addon_custom_domain_price', 5.0) or 5.0,
        sale_enabled=getattr(plan, 'sale_enabled', False),
        sale_price=getattr(plan, 'sale_price', None),
        sale_discount_percent=getattr(plan, 'sale_discount_percent', None),
        sale_type=getattr(plan, 'sale_type', 'permanent'),
        sale_expires_at=plan.sale_expires_at.isoformat() if getattr(plan, 'sale_expires_at', None) else None,
        sale_badge_label=getattr(plan, 'sale_badge_label', None),
        backup_enabled=plan.backup_enabled,
        subscriber_count=sub_count
    )


@router.put("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: int,
    body: UpdatePlanRequest,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Update subscription plan details or feature flags (Admin only)."""
    stmt = select(Plan).where(Plan.id == plan_id)
    res = await db.execute(stmt)
    plan = res.scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")

    if body.name is not None:
        plan.name = body.name.strip()
    if body.description is not None:
        plan.description = body.description
    if body.price is not None:
        plan.price = body.price
    if body.currency is not None:
        plan.currency = body.currency.upper()
    if body.billing_period is not None:
        plan.billing_period = body.billing_period
    if body.trial_days is not None:
        plan.trial_days = body.trial_days
    if body.is_active is not None:
        plan.is_active = body.is_active
    if body.max_agents is not None:
        plan.max_agents = body.max_agents
    if body.feature_makler_detector is not None:
        plan.feature_makler_detector = body.feature_makler_detector
    if body.feature_avm_bargain_finder is not None:
        plan.feature_avm_bargain_finder = body.feature_avm_bargain_finder
    if body.feature_social_brochure is not None:
        plan.feature_social_brochure = body.feature_social_brochure
    if body.feature_client_intake_bot is not None:
        plan.feature_client_intake_bot = body.feature_client_intake_bot
    if body.feature_multi_location is not None:
        plan.feature_multi_location = body.feature_multi_location
    if body.max_locations_per_search is not None:
        plan.max_locations_per_search = body.max_locations_per_search
    if body.feature_aged_listings is not None:
        plan.feature_aged_listings = body.feature_aged_listings
    if body.addon_aged_listings_price is not None:
        plan.addon_aged_listings_price = body.addon_aged_listings_price
    if body.addon_aged_max_months is not None:
        plan.addon_aged_max_months = body.addon_aged_max_months
    if body.addon_aged_tiers is not None:
        plan.addon_aged_tiers = body.addon_aged_tiers
    if body.max_saved_searches is not None:
        plan.max_saved_searches = body.max_saved_searches
    if body.addon_saved_searches is not None:
        plan.addon_saved_searches = body.addon_saved_searches
    if body.addon_saved_searches_price is not None:
        plan.addon_saved_searches_price = body.addon_saved_searches_price
    if body.addon_search_tiers is not None:
        plan.addon_search_tiers = body.addon_search_tiers
    if body.feature_watermark_free_images is not None:
        plan.feature_watermark_free_images = body.feature_watermark_free_images
    if body.included_image_requests is not None:
        plan.included_image_requests = body.included_image_requests
    if body.addon_image_requests_price is not None:
        plan.addon_image_requests_price = body.addon_image_requests_price
    if body.addon_image_tiers is not None:
        plan.addon_image_tiers = body.addon_image_tiers
    if body.feature_crm is not None:
        plan.feature_crm = body.feature_crm
    if body.addon_crm_price is not None:
        plan.addon_crm_price = body.addon_crm_price
    if body.addon_crm_tiers is not None:
        plan.addon_crm_tiers = body.addon_crm_tiers
    if body.feature_portfolio is not None:
        plan.feature_portfolio = body.feature_portfolio
    if body.addon_portfolio_price is not None:
        plan.addon_portfolio_price = body.addon_portfolio_price
    if body.addon_portfolio_limit is not None:
        plan.addon_portfolio_limit = body.addon_portfolio_limit
    if body.addon_portfolio_tiers is not None:
        plan.addon_portfolio_tiers = body.addon_portfolio_tiers
    if body.feature_custom_domain is not None:
        plan.feature_custom_domain = body.feature_custom_domain
    if body.addon_custom_domain_price is not None:
        plan.addon_custom_domain_price = body.addon_custom_domain_price
    if body.sale_enabled is not None:
        plan.sale_enabled = body.sale_enabled
    if body.sale_price is not None:
        plan.sale_price = body.sale_price
    if body.sale_discount_percent is not None:
        plan.sale_discount_percent = body.sale_discount_percent
    if body.sale_type is not None:
        plan.sale_type = body.sale_type
    if body.sale_expires_at is not None:
        from datetime import datetime as dt
        try:
            plan.sale_expires_at = dt.fromisoformat(body.sale_expires_at) if body.sale_expires_at else None
        except (ValueError, TypeError):
            plan.sale_expires_at = None
    if body.sale_badge_label is not None:
        plan.sale_badge_label = body.sale_badge_label
    if body.backup_enabled is not None:
        plan.backup_enabled = body.backup_enabled

    # Reconcile discount calculations
    if plan.sale_enabled:
        if body.sale_price is not None and body.sale_discount_percent is None and plan.price > 0:
            plan.sale_discount_percent = round(((plan.price - plan.sale_price) / plan.price) * 100.0, 1)
        elif body.sale_discount_percent is not None and body.sale_price is None:
            plan.sale_price = round(plan.price * (1 - plan.sale_discount_percent / 100.0), 2)

    # Cascade updated feature permissions to all tenants currently on this plan
    from sqlalchemy import update as sa_update
    tenant_updates = {}
    if body.feature_makler_detector is not None:
        tenant_updates["feature_makler_detector"] = body.feature_makler_detector
    if body.feature_avm_bargain_finder is not None:
        tenant_updates["feature_avm_bargain_finder"] = body.feature_avm_bargain_finder
    if body.feature_social_brochure is not None:
        tenant_updates["feature_social_brochure"] = body.feature_social_brochure
    if body.feature_client_intake_bot is not None:
        tenant_updates["feature_client_intake_bot"] = body.feature_client_intake_bot
    if body.feature_multi_location is not None:
        tenant_updates["feature_multi_location"] = body.feature_multi_location
    if body.max_locations_per_search is not None:
        tenant_updates["max_locations_per_search"] = body.max_locations_per_search
    if body.feature_aged_listings is not None:
        tenant_updates["feature_aged_listings"] = body.feature_aged_listings
    if body.feature_watermark_free_images is not None:
        tenant_updates["feature_watermark_free_images"] = body.feature_watermark_free_images
    if body.feature_crm is not None:
        tenant_updates["feature_crm"] = body.feature_crm
    if body.feature_portfolio is not None:
        tenant_updates["feature_portfolio"] = body.feature_portfolio
    if body.addon_portfolio_limit is not None:
        tenant_updates["portfolio_limit"] = body.addon_portfolio_limit
    if body.feature_custom_domain is not None:
        tenant_updates["feature_custom_domain"] = body.feature_custom_domain
    if body.backup_enabled is not None:
        tenant_updates["backup_enabled"] = body.backup_enabled

    if tenant_updates:
        await db.execute(
            sa_update(Tenant)
            .where(Tenant.plan == plan.code)
            .values(**tenant_updates)
        )

    await db.commit()
    await db.refresh(plan)

    stmt_count = select(func.count(Tenant.id)).where(Tenant.plan == plan.code)
    res_count = await db.execute(stmt_count)
    sub_count = res_count.scalar() or 0

    return PlanResponse(
        id=plan.id,
        code=plan.code,
        name=plan.name,
        description=plan.description,
        price=plan.price,
        currency=plan.currency,
        billing_period=plan.billing_period,
        trial_days=plan.trial_days or 7,
        is_active=plan.is_active,
        max_agents=plan.max_agents,
        feature_makler_detector=plan.feature_makler_detector,
        feature_avm_bargain_finder=plan.feature_avm_bargain_finder,
        feature_social_brochure=plan.feature_social_brochure,
        feature_client_intake_bot=plan.feature_client_intake_bot,
        feature_multi_location=getattr(plan, 'feature_multi_location', True),
        max_locations_per_search=getattr(plan, 'max_locations_per_search', 5),
        feature_aged_listings=getattr(plan, 'feature_aged_listings', False),
        addon_aged_listings_price=getattr(plan, 'addon_aged_listings_price', 0.0),
        addon_aged_max_months=getattr(plan, 'addon_aged_max_months', 12),
        addon_aged_tiers=getattr(plan, 'addon_aged_tiers', []) or [],
        max_saved_searches=plan.max_saved_searches,
        addon_saved_searches=getattr(plan, 'addon_saved_searches', 0),
        addon_saved_searches_price=plan.addon_saved_searches_price,
        addon_search_tiers=getattr(plan, 'addon_search_tiers', []) or [],
        feature_watermark_free_images=getattr(plan, 'feature_watermark_free_images', False),
        included_image_requests=getattr(plan, 'included_image_requests', 0),
        addon_image_requests_price=getattr(plan, 'addon_image_requests_price', 10.0),
        addon_image_tiers=getattr(plan, 'addon_image_tiers', []) or [],
        feature_crm=getattr(plan, 'feature_crm', False),
        addon_crm_price=getattr(plan, 'addon_crm_price', 15.0),
        addon_crm_tiers=getattr(plan, 'addon_crm_tiers', []) or [],
        feature_portfolio=getattr(plan, 'feature_portfolio', False),
        addon_portfolio_price=getattr(plan, 'addon_portfolio_price', 15.0),
        addon_portfolio_limit=getattr(plan, 'addon_portfolio_limit', 25),
        addon_portfolio_tiers=getattr(plan, 'addon_portfolio_tiers', []) or [],
        feature_custom_domain=getattr(plan, 'feature_custom_domain', False),
        addon_custom_domain_price=getattr(plan, 'addon_custom_domain_price', 5.0) or 5.0,
        sale_enabled=getattr(plan, 'sale_enabled', False),
        sale_price=getattr(plan, 'sale_price', None),
        sale_discount_percent=getattr(plan, 'sale_discount_percent', None),
        sale_type=getattr(plan, 'sale_type', 'permanent'),
        sale_expires_at=plan.sale_expires_at.isoformat() if getattr(plan, 'sale_expires_at', None) else None,
        sale_badge_label=getattr(plan, 'sale_badge_label', None),
        backup_enabled=plan.backup_enabled,
        subscriber_count=sub_count
    )


@router.delete("/{plan_id}")
async def delete_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Deactivate or delete a subscription plan."""
    stmt = select(Plan).where(Plan.id == plan_id)
    res = await db.execute(stmt)
    plan = res.scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")

    plan.is_active = False
    await db.commit()
    return {"message": f"Plan '{plan.name}' has been deactivated."}


class UpdateAddonRequest(BaseModel):
    is_active: Optional[bool] = None
    price: Optional[float] = None
    tiers: Optional[List[dict]] = None
    sale_enabled: Optional[bool] = None
    sale_price: Optional[float] = None
    sale_discount_percent: Optional[float] = None
    sale_badge_label: Optional[str] = None
    max_months: Optional[int] = None
    included_quota: Optional[int] = None


@router.get("/addons/overview")
async def get_addons_overview(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Retrieve consolidated catalogue of all SaaS Add-ons, their base prices, tiers, and sale parameters."""
    stmt = select(Plan).where(Plan.is_active == True)
    res = await db.execute(stmt)
    plans = res.scalars().all()

    # Find starter/default plan for reference
    starter_plan = next((p for p in plans if p.code == "starter"), (plans[0] if plans else None))

    addons = [
        {
            "key": "crm",
            "name": "💼 Telegram Mini App & Real Estate CRM",
            "description": "Agentlər üçün /crm əmri, müştəri boru kəməri (pipeline), lead idarəetməsi və Telegram Mini App CRM interfeysi.",
            "category": "crm",
            "is_active": True,
            "default_price": getattr(starter_plan, 'addon_crm_price', 15.0) or 15.0,
            "billing_period": "monthly",
            "tiers": getattr(starter_plan, 'addon_crm_tiers', []) or [
                {"months": 1, "price": 15.0},
                {"months": 3, "price": 35.0},
                {"months": 6, "price": 65.0},
                {"months": 12, "price": 110.0}
            ],
            "sale_enabled": False,
            "sale_price": None,
            "sale_discount_percent": 20.0,
            "sale_badge_label": "🔥 20% CRM Xüsusi Endirim",
            "features_included": [
                "/crm <id> Telegram əmri və sürətli idarəetmə",
                "Müştəri Boru Kəməri (TMA Kanban / Pipeline)",
                "Elan və müştəri uyğunluq qeydləri",
                "Fərdi zəng və əlaqə statuslarının izlənməsi"
            ]
        },
        {
            "key": "aged_listings",
            "name": "📦 Arxiv Elanlar Bazasından Axtarış",
            "description": "Tarixi və aktiv arxiv elanlar bazasından (1-24 ay) axtarış və dərhal uyğunluq tapılması.",
            "category": "inventory",
            "is_active": True,
            "default_price": getattr(starter_plan, 'addon_aged_listings_price', 15.0) or 15.0,
            "billing_period": "monthly",
            "max_months": getattr(starter_plan, 'addon_aged_max_months', 12) or 12,
            "tiers": getattr(starter_plan, 'addon_aged_tiers', []) or [
                {"months": 1, "price": 10.0},
                {"months": 3, "price": 25.0},
                {"months": 6, "price": 45.0},
                {"months": 12, "price": 80.0}
            ],
            "sale_enabled": False,
            "sale_price": None,
            "sale_discount_percent": 15.0,
            "sale_badge_label": "📦 Arxiv Paketi Xüsusi Təklif",
            "features_included": [
                "24 aya qədər tarixi elan arxivinə çıxış",
                "Dərhal tarixi axtarış (Backfill Matcher)",
                "Sahibindən arxiv elanlarının analizi"
            ]
        },
        {
            "key": "saved_searches",
            "name": "⚡ Əlavə Axtarış Yuvaları (Search Slots)",
            "description": "Agentin eyni anda aktiv saxlaya biləcəyi daimi axtarış filtrlərinin sayını artırır.",
            "category": "quota",
            "is_active": True,
            "default_price": getattr(starter_plan, 'addon_saved_searches_price', 10.0) or 10.0,
            "billing_period": "monthly",
            "pack_size": 5,
            "tiers": getattr(starter_plan, 'addon_search_tiers', []) or [
                {"searches": 5, "price": 10.0},
                {"searches": 10, "price": 18.0},
                {"searches": 20, "price": 30.0}
            ],
            "sale_enabled": False,
            "sale_price": None,
            "sale_discount_percent": None,
            "sale_badge_label": "⚡ Sürətli Axtarış Paketi",
            "features_included": [
                "Hər paket üçün +5 əlavə axtarış yuvası",
                "Eyni vaxtda çoxsaylı müştəri sorğusunu izləmə",
                "Prioritet elan bildirişləri"
            ]
        },
        {
            "key": "watermark_free_images",
            "name": "🖼️ Su Nişansız Şəkillər (Clean Photos)",
            "description": "Saytların su nişanları (bina.az, tap.az və s.) təmizlənmiş yüksək keyfiyyətli orijinal elan şəkilləri.",
            "category": "quota",
            "is_active": True,
            "default_price": getattr(starter_plan, 'addon_image_requests_price', 10.0) or 10.0,
            "billing_period": "monthly",
            "pack_size": 25,
            "tiers": getattr(starter_plan, 'addon_image_tiers', []) or [
                {"requests": 25, "price": 10.0},
                {"requests": 50, "price": 18.0},
                {"requests": 100, "price": 30.0}
            ],
            "sale_enabled": False,
            "sale_price": None,
            "sale_discount_percent": None,
            "sale_badge_label": "🖼️ Təmiz Şəkil Paketi",
            "features_included": [
                "AI ilə su nişanı təmizlənmiş fotolar",
                "Müştəriyə göndərilmək üçün hazır vizual broşür",
                "HD keyfiyyətli şəkil yükləmə"
            ]
        },
        {
            "key": "portfolio",
            "name": "🗂️ Agent Portfeli & Rəqəmsal Vitrin (Agent Portfolio)",
            "description": "Gələn elanları 1 toxunuşla fərdi portfelə köçürmə, sahələri redaktə etmə, müştərilərə xüsusi linklə təqdim etmə və limit daxilində idarə etmə.",
            "category": "portfolio",
            "is_active": True,
            "default_price": getattr(starter_plan, 'addon_portfolio_price', 15.0) or 15.0,
            "billing_period": "monthly",
            "pack_size": 25,
            "tiers": getattr(starter_plan, 'addon_portfolio_tiers', []) or [
                {"listings": 25, "price": 15.0},
                {"listings": 50, "price": 25.0},
                {"listings": 100, "price": 40.0}
            ],
            "sale_enabled": False,
            "sale_price": None,
            "sale_discount_percent": 20.0,
            "sale_badge_label": "🗂️ Portfel Add-on Xüsusi Endirim",
            "features_included": [
                "1 toxunuşla bildirişlərdən portfelə köçürmə (/portfolio <id>)",
                "Bütün elan sahələrinin fərdi redaktəsi",
                "25 aktiv elan yuvası (bitmiş elan silindikdə limit avtomatik boşalır)",
                "Brendləşdirilmiş müştəri paylaşım linkləri və WhatsApp düyməsi"
            ]
        }
    ]

    return addons


@router.put("/addons/{addon_key}")
async def update_addon_config(
    addon_key: str,
    body: UpdateAddonRequest,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Batch update pricing and tiers for a specific Add-on across subscription plans."""
    stmt = select(Plan)
    res = await db.execute(stmt)
    plans = res.scalars().all()

    for plan in plans:
        if addon_key == "crm":
            if body.price is not None:
                plan.addon_crm_price = float(body.price)
            if body.tiers is not None:
                plan.addon_crm_tiers = body.tiers
        elif addon_key == "portfolio":
            if body.price is not None:
                plan.addon_portfolio_price = float(body.price)
            if body.tiers is not None:
                plan.addon_portfolio_tiers = body.tiers
            if body.included_quota is not None:
                plan.addon_portfolio_limit = int(body.included_quota)
        elif addon_key == "aged_listings":
            if body.price is not None:
                plan.addon_aged_listings_price = float(body.price)
            if body.tiers is not None:
                plan.addon_aged_tiers = body.tiers
            if body.max_months is not None:
                plan.addon_aged_max_months = int(body.max_months)
        elif addon_key == "saved_searches":
            if body.price is not None:
                plan.addon_saved_searches_price = float(body.price)
            if body.tiers is not None:
                plan.addon_search_tiers = body.tiers
        elif addon_key == "watermark_free_images":
            if body.price is not None:
                plan.addon_image_requests_price = float(body.price)
            if body.tiers is not None:
                plan.addon_image_tiers = body.tiers

    await db.commit()
    return {"message": f"Add-on '{addon_key}' konfiqurasiyası bütün planlarda uğurla yeniləndi."}
