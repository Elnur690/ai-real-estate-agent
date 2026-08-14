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
    feature_aged_listings: bool = False
    addon_aged_listings_price: float = 0.0
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
    feature_aged_listings: bool = False
    addon_aged_listings_price: float = 0.0
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
    feature_aged_listings: Optional[bool] = None
    addon_aged_listings_price: Optional[float] = None
    backup_enabled: Optional[bool] = None


@router.get("", response_model=List[PlanResponse])
async def list_plans(db: AsyncSession = Depends(get_db)):
    """List all available subscription plans with subscriber counts."""
    stmt = select(Plan).order_by(Plan.price.asc())
    res = await db.execute(stmt)
    plans = res.scalars().all()

    # Get subscriber counts per plan code
    stmt_counts = select(Tenant.plan, func.count(Tenant.id)).group_by(Tenant.plan)
    res_counts = await db.execute(stmt_counts)
    counts_map = {row[0].lower(): row[1] for row in res_counts.all() if row[0]}

    response_list = []
    for plan in plans:
        sub_count = counts_map.get(plan.code.lower(), 0)
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
            feature_aged_listings=getattr(plan, 'feature_aged_listings', False),
            addon_aged_listings_price=getattr(plan, 'addon_aged_listings_price', 0.0),
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
        feature_aged_listings=body.feature_aged_listings,
        addon_aged_listings_price=body.addon_aged_listings_price,
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
        feature_aged_listings=plan.feature_aged_listings,
        addon_aged_listings_price=plan.addon_aged_listings_price,
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
        feature_aged_listings=getattr(plan, 'feature_aged_listings', False),
        addon_aged_listings_price=getattr(plan, 'addon_aged_listings_price', 0.0),
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
    if body.feature_aged_listings is not None:
        plan.feature_aged_listings = body.feature_aged_listings
    if body.addon_aged_listings_price is not None:
        plan.addon_aged_listings_price = body.addon_aged_listings_price
    if body.backup_enabled is not None:
        plan.backup_enabled = body.backup_enabled

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
    if body.feature_aged_listings is not None:
        tenant_updates["feature_aged_listings"] = body.feature_aged_listings
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
        feature_aged_listings=getattr(plan, 'feature_aged_listings', False),
        addon_aged_listings_price=getattr(plan, 'addon_aged_listings_price', 0.0),
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
