from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, get_current_admin, get_current_seller_user
from app.models.user import User
from app.models.tenant import Tenant
from app.models.seller import Seller, SellerPackage, SellerTransaction
from app.models.saved_search import SavedSearch
from app.models.match import Match
from app.models.setting import AppSettings
from app.models.plan import Plan
from app.models.payment import Payment
from app.api.v1.auth import get_password_hash
from app.core.config import settings
from app.core.security import validate_strong_password

router = APIRouter(prefix="/sellers", tags=["Sellers"])

# ----------------- PYDANTIC SCHEMAS -----------------

class CreateSellerRequest(BaseModel):
    name: str
    email: str
    phone: str
    password: str
    company_name: Optional[str] = None
    commission_rate: float = 70.0
    rank: str = "Bronze"
    custom_domain: Optional[str] = None
    custom_domain_enabled: bool = False
    custom_brand_title: Optional[str] = None
    custom_brand_logo: Optional[str] = None

class UpdateSellerRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    commission_rate: Optional[float] = None
    rank: Optional[str] = None
    status: Optional[str] = None
    password: Optional[str] = None
    custom_domain: Optional[str] = None
    custom_domain_enabled: Optional[bool] = None
    domain_status: Optional[str] = None
    custom_brand_title: Optional[str] = None
    custom_brand_logo: Optional[str] = None

class CreatePackageRequest(BaseModel):
    name: str
    price: float
    description: Optional[str] = None
    period: str = "monthly"
    duration_days: int = 30
    max_searches: int = 10
    max_locations: int = 5
    feature_makler_detector: bool = True
    feature_avm_bargain_finder: bool = True
    feature_social_brochure: bool = True
    feature_multi_location: bool = True
    feature_client_intake_bot: bool = False
    feature_backup_service: bool = False
    feature_aged_listings: bool = False
    addon_aged_listings_price: float = 15.0
    addon_aged_max_months: int = 12
    addon_aged_tiers: Optional[List[Dict[str, Any]]] = None
    addon_saved_searches: int = 0
    addon_saved_searches_price: float = 10.0
    addon_search_tiers: Optional[List[Dict[str, Any]]] = None
    feature_watermark_free_images: bool = False
    included_image_requests: int = 0
    addon_image_requests_price: float = 10.0
    addon_image_tiers: Optional[List[Dict[str, Any]]] = None
    feature_crm: bool = False
    addon_crm_price: float = 15.0
    addon_crm_tiers: Optional[List[Dict[str, Any]]] = None
    feature_portfolio: bool = False
    addon_portfolio_price: float = 15.0
    addon_portfolio_limit: int = 25
    addon_portfolio_tiers: Optional[List[Dict[str, Any]]] = None
    sale_enabled: bool = False
    sale_price: Optional[float] = None
    sale_discount_percent: Optional[float] = None
    sale_type: str = "permanent"
    sale_expires_at: Optional[datetime] = None
    sale_badge_label: Optional[str] = None

class UpdatePackageRequest(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    period: Optional[str] = None
    duration_days: Optional[int] = None
    max_searches: Optional[int] = None
    max_locations: Optional[int] = None
    feature_makler_detector: Optional[bool] = None
    feature_avm_bargain_finder: Optional[bool] = None
    feature_social_brochure: Optional[bool] = None
    feature_multi_location: Optional[bool] = None
    feature_client_intake_bot: Optional[bool] = None
    feature_backup_service: Optional[bool] = None
    feature_aged_listings: Optional[bool] = None
    addon_aged_listings_price: Optional[float] = None
    addon_aged_max_months: Optional[int] = None
    addon_aged_tiers: Optional[List[Dict[str, Any]]] = None
    addon_saved_searches: Optional[int] = None
    addon_saved_searches_price: Optional[float] = None
    addon_search_tiers: Optional[List[Dict[str, Any]]] = None
    feature_watermark_free_images: Optional[bool] = None
    included_image_requests: Optional[int] = None
    addon_image_requests_price: Optional[float] = None
    addon_image_tiers: Optional[List[Dict[str, Any]]] = None
    feature_crm: Optional[bool] = None
    addon_crm_price: Optional[float] = None
    addon_crm_tiers: Optional[List[Dict[str, Any]]] = None
    feature_portfolio: Optional[bool] = None
    addon_portfolio_price: Optional[float] = None
    addon_portfolio_limit: Optional[int] = None
    addon_portfolio_tiers: Optional[List[Dict[str, Any]]] = None
    sale_enabled: Optional[bool] = None
    sale_price: Optional[float] = None
    sale_discount_percent: Optional[float] = None
    sale_type: Optional[str] = None
    sale_expires_at: Optional[datetime] = None
    sale_badge_label: Optional[str] = None
    is_active: Optional[bool] = None

class RegisterSellerAgentRequest(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    telegram_handle: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    whatsapp_number: Optional[str] = None
    preferred_channel: str = "telegram"
    package_id: Optional[int] = None
    is_trial: bool = False
    preferred_billing_day: Optional[int] = 1
    selected_aged_months: Optional[int] = None
    selected_aged_price: Optional[float] = None
    selected_extra_searches: Optional[int] = None
    selected_extra_searches_price: Optional[float] = None
    selected_image_requests: Optional[int] = None
    selected_image_price: Optional[float] = None
    selected_crm_enabled: Optional[bool] = None
    selected_crm_months: Optional[int] = None
    selected_crm_price: Optional[float] = None
    selected_portfolio_enabled: Optional[bool] = None
    selected_portfolio_limit: Optional[int] = None
    selected_portfolio_price: Optional[float] = None

class UpdateSellerAgentRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    telegram_handle: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    whatsapp_number: Optional[str] = None
    preferred_channel: Optional[str] = None
    preferred_billing_day: Optional[int] = None
    status: Optional[str] = None
    feature_makler_detector: Optional[bool] = None
    feature_avm_bargain_finder: Optional[bool] = None
    feature_social_brochure: Optional[bool] = None
    feature_multi_location: Optional[bool] = None
    max_locations_per_search: Optional[int] = None
    feature_client_intake_bot: Optional[bool] = None
    backup_enabled: Optional[bool] = None
    feature_aged_listings: Optional[bool] = None
    addon_aged_max_months: Optional[int] = None
    addon_saved_searches: Optional[int] = None
    feature_watermark_free_images: Optional[bool] = None
    addon_image_requests_limit: Optional[int] = None
    addon_image_requests_used: Optional[int] = None
    feature_crm: Optional[bool] = None
    addon_crm_price: Optional[float] = None
    feature_portfolio: Optional[bool] = None
    portfolio_limit: Optional[int] = None
    addon_portfolio_price: Optional[float] = None

class RenewSellerAgentRequest(BaseModel):
    package_id: Optional[int] = None
    custom_price: Optional[float] = None
    preferred_billing_day: Optional[int] = None
    selected_aged_months: Optional[int] = None
    selected_aged_price: Optional[float] = None
    selected_extra_searches: Optional[int] = None
    selected_extra_searches_price: Optional[float] = None
    selected_image_requests: Optional[int] = None
    selected_image_price: Optional[float] = None
    selected_crm_enabled: Optional[bool] = None
    selected_crm_months: Optional[int] = None
    selected_crm_price: Optional[float] = None
    selected_portfolio_enabled: Optional[bool] = None
    selected_portfolio_limit: Optional[int] = None
    selected_portfolio_price: Optional[float] = None

class UpdateFreeTrialSettingsRequest(BaseModel):
    free_trial_enabled: Optional[bool] = None
    free_trial_duration_days: Optional[int] = None
    free_trial_max_searches: Optional[int] = None
    free_trial_max_locations: Optional[int] = None
    free_trial_feature_makler: Optional[bool] = None
    free_trial_feature_avm: Optional[bool] = None
    free_trial_feature_social_brochure: Optional[bool] = None
    free_trial_feature_multi_location: Optional[bool] = None
    free_trial_feature_watermark_images: Optional[bool] = None
    free_trial_image_requests: Optional[int] = None
    free_trial_feature_crm: Optional[bool] = None
    free_trial_feature_portfolio: Optional[bool] = None
    free_trial_portfolio_limit: Optional[int] = None

class PayoutRequest(BaseModel):
    amount: float
    description: Optional[str] = None

class SettleCashRequest(BaseModel):
    amount: float
    notes: Optional[str] = None

class RankBonusesConfig(BaseModel):
    enabled: bool = True
    bronze_bonus: float = 0.0
    silver_bonus: float = 3.0
    gold_bonus: float = 5.0
    platinum_bonus: float = 8.0
    diamond_bonus: float = 10.0


async def get_seller_rank_config_map(db: AsyncSession) -> dict:
    """Returns the dynamic rank configuration map with admin configured bonuses and settings."""
    from app.models.setting import AppSettings
    from app.models.seller import SELLER_RANK_CONFIG
    import copy

    keys = [
        "seller_rank_bonus_enabled",
        "seller_rank_bonus_bronze",
        "seller_rank_bonus_silver",
        "seller_rank_bonus_gold",
        "seller_rank_bonus_platinum",
        "seller_rank_bonus_diamond"
    ]
    stmt = select(AppSettings).where(AppSettings.key.in_(keys))
    res = await db.execute(stmt)
    settings_map = {s.key: s.value for s in res.scalars().all()}

    is_enabled = settings_map.get("seller_rank_bonus_enabled", "true").lower() in ["true", "1", "yes"]

    rank_config = copy.deepcopy(SELLER_RANK_CONFIG)

    for rank, conf in rank_config.items():
        if not is_enabled:
            conf["bonus_commission"] = 0.0
        else:
            key_name = f"seller_rank_bonus_{rank.lower()}"
            if key_name in settings_map:
                try:
                    conf["bonus_commission"] = float(settings_map[key_name])
                except (ValueError, TypeError):
                    pass
        conf["bonus_enabled"] = is_enabled

    return rank_config


# ----------------- ADMIN ENDPOINTS -----------------

@router.get("/admin/rank-bonuses")
async def get_rank_bonuses_admin(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin-only: Get rank bonuses configuration."""
    from app.models.setting import AppSettings
    stmt = select(AppSettings).where(AppSettings.key.like("seller_rank_bonus%"))
    res = await db.execute(stmt)
    settings_map = {s.key: s.value for s in res.scalars().all()}

    is_enabled = settings_map.get("seller_rank_bonus_enabled", "true").lower() in ["true", "1", "yes"]

    def _get_float(key, default):
        try:
            return float(settings_map.get(key, default))
        except (ValueError, TypeError):
            return default

    return {
        "enabled": is_enabled,
        "bronze_bonus": _get_float("seller_rank_bonus_bronze", 0.0),
        "silver_bonus": _get_float("seller_rank_bonus_silver", 3.0),
        "gold_bonus": _get_float("seller_rank_bonus_gold", 5.0),
        "platinum_bonus": _get_float("seller_rank_bonus_platinum", 8.0),
        "diamond_bonus": _get_float("seller_rank_bonus_diamond", 10.0),
    }


@router.post("/admin/rank-bonuses")
async def update_rank_bonuses_admin(
    body: RankBonusesConfig,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin-only: Update rank bonuses configuration or disable bonuses completely."""
    from app.models.setting import AppSettings
    updates = {
        "seller_rank_bonus_enabled": "true" if body.enabled else "false",
        "seller_rank_bonus_bronze": str(max(0.0, min(100.0, body.bronze_bonus))),
        "seller_rank_bonus_silver": str(max(0.0, min(100.0, body.silver_bonus))),
        "seller_rank_bonus_gold": str(max(0.0, min(100.0, body.gold_bonus))),
        "seller_rank_bonus_platinum": str(max(0.0, min(100.0, body.platinum_bonus))),
        "seller_rank_bonus_diamond": str(max(0.0, min(100.0, body.diamond_bonus))),
    }

    for key, val in updates.items():
        stmt = select(AppSettings).where(AppSettings.key == key)
        res = await db.execute(stmt)
        setting = res.scalars().first()
        if setting:
            setting.value = val
            setting.updated_by = admin.id
        else:
            db.add(AppSettings(key=key, value=val, updated_by=admin.id))

    await db.commit()
    return {"message": "Dərəcə bonusları uğurla yeniləndi", "config": body}


@router.get("", response_model=List[dict])
async def list_all_sellers_admin(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin-only: List all registered sellers with their agent counts, earnings, and domain configs."""
    rank_map = await get_seller_rank_config_map(db)
    stmt = select(Seller).order_by(Seller.created_at.desc())
    res = await db.execute(stmt)
    sellers = res.scalars().all()

    # Pre-fetch all agent counts grouped by seller_id in a single efficient query
    from sqlalchemy import case
    agent_cnt_stmt = select(
        Tenant.seller_id,
        func.count(Tenant.id).label("total_agents"),
        func.count(case((Tenant.status == "active", Tenant.id), else_=None)).label("active_agents")
    ).where(Tenant.seller_id.is_not(None)).group_by(Tenant.seller_id)
    agent_cnt_res = await db.execute(agent_cnt_stmt)
    agent_cnt_map = {row.seller_id: (row.total_agents, row.active_agents) for row in agent_cnt_res.all()}

    results = []
    for s in sellers:
        total_agents, active_agents = agent_cnt_map.get(s.id, (0, 0))
        rank_info = rank_map.get(s.rank, rank_map.get("Bronze", {}))

        total_platform_fee = max(0.0, round((s.total_sales_volume or 0.0) - (s.total_earnings or 0.0), 2))
        platform_fee_settled = getattr(s, 'platform_fee_settled', 0.0) or 0.0
        pending_platform_debt = max(0.0, round(total_platform_fee - platform_fee_settled, 2))

        results.append({
            "id": s.id,
            "user_id": s.user_id,
            "name": s.name,
            "email": s.email,
            "phone": s.phone,
            "company_name": s.company_name,
            "commission_rate": s.commission_rate,
            "bonus_commission": rank_info.get("bonus_commission", 0.0),
            "effective_commission_rate": min(100.0, s.commission_rate + rank_info.get("bonus_commission", 0.0)),
            "rank": s.rank,
            "rank_label": rank_info.get("label", s.rank),
            "rank_emoji": rank_info.get("badge_emoji", "🥉"),
            "status": s.status,
            "balance": s.balance,
            "total_earnings": s.total_earnings,
            "total_sales_volume": s.total_sales_volume,
            "total_platform_fee": total_platform_fee,
            "platform_fee_settled": platform_fee_settled,
            "pending_platform_debt": pending_platform_debt,
            "total_agents": total_agents,
            "active_agents": active_agents,
            "custom_domain": s.custom_domain,
            "custom_domain_enabled": s.custom_domain_enabled,
            "rank_allows_domain": rank_info.get("custom_domain_allowed", False) or s.custom_domain_enabled,
            "domain_status": s.domain_status,
            "custom_brand_title": s.custom_brand_title,
            "custom_brand_logo": s.custom_brand_logo,
            "created_at": s.created_at.isoformat() if s.created_at else None
        })

    return results


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_seller_admin(
    body: CreateSellerRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin-only: Create a new Seller and generate their login account."""
    # Check if email is already taken
    stmt = select(User).where(User.email == body.email)
    res = await db.execute(stmt)
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="Bu email ilə artıq istifadəçi mövcuddur.")

    validate_strong_password(body.password)

    # 1. Create User
    user = User(
        name=body.name,
        email=body.email,
        phone=body.phone,
        role="seller",
        password_hash=get_password_hash(body.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    clean_domain = body.custom_domain.strip().lower().replace("https://", "").replace("http://", "").rstrip("/") if body.custom_domain else None

    # 2. Create Seller Profile
    seller = Seller(
        user_id=user.id,
        name=body.name,
        phone=body.phone,
        email=body.email,
        company_name=body.company_name,
        commission_rate=max(0.0, min(100.0, body.commission_rate)),
        rank=body.rank,
        custom_domain=clean_domain,
        custom_domain_enabled=body.custom_domain_enabled or (clean_domain is not None),
        domain_status="pending_dns" if clean_domain else "disabled",
        custom_brand_title=body.custom_brand_title,
        custom_brand_logo=body.custom_brand_logo,
        status="active"
    )
    db.add(seller)
    await db.commit()
    await db.refresh(seller)

    # 3. Create default packages for this seller
    default_packages = [
        SellerPackage(
            seller_id=seller.id,
            name="Standart Paket",
            description="Fərdi agentlər üçün aylıq tam paket",
            price=49.0,
            period="monthly",
            duration_days=30,
            max_searches=10,
            max_locations=5,
            feature_makler_detector=True,
            feature_avm_bargain_finder=True,
            feature_social_brochure=True,
            feature_multi_location=True,
            feature_client_intake_bot=False,
            feature_backup_service=False,
            feature_aged_listings=False,
            addon_aged_tiers=[
                {"months": 3, "price": 15.0},
                {"months": 6, "price": 25.0},
                {"months": 12, "price": 40.0}
            ],
            addon_search_tiers=[
                {"searches": 5, "price": 10.0},
                {"searches": 10, "price": 18.0},
                {"searches": 20, "price": 30.0}
            ]
        ),
        SellerPackage(
            seller_id=seller.id,
            name="Pro Agent Paketi",
            description="Geniş axtarışlar, müştəri botu və backup ilə",
            price=89.0,
            period="monthly",
            duration_days=30,
            max_searches=20,
            max_locations=10,
            feature_makler_detector=True,
            feature_avm_bargain_finder=True,
            feature_social_brochure=True,
            feature_multi_location=True,
            feature_client_intake_bot=True,
            feature_backup_service=True,
            feature_aged_listings=True,
            addon_aged_tiers=[
                {"months": 6, "price": 20.0},
                {"months": 12, "price": 35.0},
                {"months": 24, "price": 55.0}
            ],
            addon_search_tiers=[
                {"searches": 10, "price": 15.0},
                {"searches": 20, "price": 25.0},
                {"searches": 50, "price": 50.0}
            ]
        )
    ]
    db.add_all(default_packages)
    await db.commit()

    return {
        "message": "Satıcı uğurla yaradıldı",
        "seller_id": seller.id,
        "user_id": user.id,
        "name": seller.name,
        "commission_rate": seller.commission_rate,
        "rank": seller.rank
    }


# ----------------- SELLER PORTAL ENDPOINTS (ISOLATED) -----------------

@router.get("/me/dashboard")
async def get_seller_dashboard(
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: Get my dashboard metrics, earnings, rank, and active agent count."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    # Count total agents
    agent_cnt_stmt = select(func.count(Tenant.id)).where(Tenant.seller_id == seller.id)
    agent_cnt_res = await db.execute(agent_cnt_stmt)
    total_agents = agent_cnt_res.scalar() or 0

    # Count active agents
    active_cnt_stmt = select(func.count(Tenant.id)).where(Tenant.seller_id == seller.id, Tenant.status == "active")
    active_cnt_res = await db.execute(active_cnt_stmt)
    active_agents = active_cnt_res.scalar() or 0

    # Total packages count
    pkg_cnt_stmt = select(func.count(SellerPackage.id)).where(SellerPackage.seller_id == seller.id, SellerPackage.is_active == True)
    pkg_cnt_res = await db.execute(pkg_cnt_stmt)
    total_packages = pkg_cnt_res.scalar() or 0

    # Auto rank calculation based on lifetime sales volume
    rank_thresholds = [
        ("Diamond", 10000.0),
        ("Platinum", 5000.0),
        ("Gold", 2000.0),
        ("Silver", 500.0),
        ("Bronze", 0.0)
    ]
    auto_rank = seller.rank
    for rank_name, min_vol in rank_thresholds:
        if seller.total_sales_volume >= min_vol:
            auto_rank = rank_name
            break

    if auto_rank != seller.rank and seller.rank == "Bronze":
        seller.rank = auto_rank
        await db.commit()

    rank_map = await get_seller_rank_config_map(db)
    rank_info = rank_map.get(seller.rank, rank_map.get("Bronze", {}))
    bonus_commission = rank_info.get("bonus_commission", 0.0)
    effective_commission_rate = min(100.0, seller.commission_rate + bonus_commission)

    min_price, max_trial_days = await _get_seller_package_constraints(db)

    total_platform_fee = max(0.0, round((seller.total_sales_volume or 0.0) - (seller.total_earnings or 0.0), 2))
    platform_fee_settled = getattr(seller, 'platform_fee_settled', 0.0) or 0.0
    pending_platform_debt = max(0.0, round(total_platform_fee - platform_fee_settled, 2))

    return {
        "seller_id": seller.id,
        "name": seller.name,
        "email": seller.email,
        "phone": seller.phone,
        "company_name": seller.company_name,
        "commission_rate": seller.commission_rate,
        "bonus_commission": bonus_commission,
        "effective_commission_rate": effective_commission_rate,
        "rank": seller.rank,
        "rank_label": rank_info.get("label", seller.rank),
        "rank_emoji": rank_info.get("badge_emoji", "🥉"),
        "rank_description": rank_info.get("description", ""),
        "rank_max_packages": rank_info.get("max_packages", 5),
        "rank_custom_domain_allowed": rank_info.get("custom_domain_allowed", False) or seller.custom_domain_enabled,
        "next_rank": rank_info.get("next_rank"),
        "next_sales_target": rank_info.get("next_sales_target"),
        "status": seller.status,
        "balance": seller.balance,
        "total_earnings": seller.total_earnings,
        "total_sales_volume": seller.total_sales_volume,
        "total_platform_fee": total_platform_fee,
        "platform_fee_settled": platform_fee_settled,
        "pending_platform_debt": pending_platform_debt,
        "total_agents": total_agents,
        "active_agents": active_agents,
        "total_packages": total_packages,
        "min_package_price": min_price,
        "max_trial_days": max_trial_days,
        "free_trial_enabled": seller.free_trial_enabled,
        "free_trial_duration_days": seller.free_trial_duration_days,
        "free_trial_max_searches": seller.free_trial_max_searches,
        "free_trial_max_locations": seller.free_trial_max_locations,
        "free_trial_feature_makler": seller.free_trial_feature_makler,
        "free_trial_feature_avm": seller.free_trial_feature_avm,
        "free_trial_feature_social_brochure": seller.free_trial_feature_social_brochure,
        "free_trial_feature_multi_location": seller.free_trial_feature_multi_location,
        "custom_domain": seller.custom_domain,
        "custom_domain_enabled": seller.custom_domain_enabled,
        "domain_status": seller.domain_status,
        "custom_brand_title": seller.custom_brand_title,
        "custom_brand_logo": seller.custom_brand_logo
    }


def _is_expired(expires_at: Optional[datetime]) -> bool:
    if not expires_at:
        return False
    if expires_at.tzinfo is None:
        return expires_at < datetime.now(timezone.utc).replace(tzinfo=None)
    return expires_at < datetime.now(timezone.utc)


def _normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.get("/me/agents")
async def get_my_agents(
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: List only my registered agents."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    stmt = select(Tenant).where(Tenant.seller_id == seller.id).order_by(Tenant.created_at.desc())
    res = await db.execute(stmt)
    agents = res.scalars().all()

    # Load App Settings for Bot Links
    settings_stmt = select(AppSettings).where(AppSettings.key.in_(["telegram_bot_username", "whatsapp_bot_phone"]))
    settings_res = await db.execute(settings_stmt)
    settings_map = {s.key: s.value for s in settings_res.scalars().all()}
    tg_bot_user = settings_map.get("telegram_bot_username", "baku_realestate_ai_bot").lstrip("@")
    wa_bot_phone = settings_map.get("whatsapp_bot_phone", "+994501234567").replace("+", "").replace(" ", "")

    # Pre-fetch Seller Packages, Plans and Last Payments to eliminate N+1 queries
    pkg_stmt = select(SellerPackage).where(SellerPackage.seller_id == seller.id)
    pkg_res = await db.execute(pkg_stmt)
    pkgs_map = {p.id: p for p in pkg_res.scalars().all()}

    plan_stmt = select(Plan)
    plan_res = await db.execute(plan_stmt)
    plans_price_map = {}
    for p in plan_res.scalars().all():
        plans_price_map[p.code] = p.price
        plans_price_map[p.name] = p.price

    agent_ids = [a.id for a in agents]
    last_payments_map = {}
    if agent_ids:
        pay_stmt = select(Payment.tenant_id, Payment.amount).where(Payment.tenant_id.in_(agent_ids)).order_by(Payment.received_at.asc())
        pay_res = await db.execute(pay_stmt)
        for row in pay_res.all():
            last_payments_map[row.tenant_id] = row.amount

    results = []
    for a in agents:
        pkg_name = None
        pkg_price = 0.0
        if a.seller_package_id and a.seller_package_id in pkgs_map:
            pkg = pkgs_map[a.seller_package_id]
            pkg_name = pkg.name
            pkg_price = pkg.price
        else:
            last_amount = last_payments_map.get(a.id)
            if last_amount is not None and last_amount > 0:
                pkg_price = last_amount
            else:
                p_price = plans_price_map.get(a.plan)
                if p_price is not None:
                    pkg_price = p_price
                elif a.plan in ["pro", "agency"]:
                    pkg_price = 99.0
                elif a.plan in ["starter"]:
                    pkg_price = 49.0

        is_expired = _is_expired(a.plan_expires_at)
        tg_url = f"https://t.me/{tg_bot_user}?start=agent_{a.id}"
        wa_url = f"https://wa.me/{wa_bot_phone}?text=START_{a.id}"
        invite_url = tg_url if a.preferred_channel == "telegram" else wa_url

        results.append({
            "id": a.id,
            "name": a.name,
            "phone": a.phone,
            "telegram_handle": a.telegram_handle,
            "whatsapp_number": a.whatsapp_number,
            "preferred_channel": a.preferred_channel,
            "plan": pkg_name or a.plan,
            "plan_price": pkg_price,
            "is_transferred": a.seller_package_id is None,
            "status": a.status,
            "is_expired": is_expired,
            "plan_started_at": a.plan_started_at.isoformat() if a.plan_started_at else None,
            "plan_expires_at": a.plan_expires_at.isoformat() if a.plan_expires_at else None,
            "preferred_billing_day": getattr(a, 'preferred_billing_day', 1) or 1,
            "feature_makler_detector": a.feature_makler_detector,
            "feature_avm_bargain_finder": a.feature_avm_bargain_finder,
            "feature_social_brochure": a.feature_social_brochure,
            "feature_multi_location": a.feature_multi_location,
            "max_locations_per_search": a.max_locations_per_search,
            "feature_client_intake_bot": a.feature_client_intake_bot,
            "backup_enabled": a.backup_enabled,
            "feature_aged_listings": a.feature_aged_listings,
            "addon_aged_max_months": a.addon_aged_max_months,
            "aged_expires_at": a.aged_expires_at.isoformat() if getattr(a, 'aged_expires_at', None) else None,
            "addon_saved_searches": a.addon_saved_searches,
            "addon_saved_searches_price": a.addon_saved_searches_price,
            "feature_watermark_free_images": getattr(a, 'feature_watermark_free_images', False),
            "addon_image_requests_limit": getattr(a, 'addon_image_requests_limit', 0),
            "addon_image_requests_used": getattr(a, 'addon_image_requests_used', 0),
            "addon_image_requests_price": getattr(a, 'addon_image_requests_price', 0.0),
            "feature_crm": getattr(a, 'feature_crm', False),
            "crm_expires_at": a.crm_expires_at.isoformat() if getattr(a, 'crm_expires_at', None) else None,
            "feature_portfolio": getattr(a, 'feature_portfolio', False),
            "portfolio_limit": getattr(a, 'portfolio_limit', 25),
            "portfolio_expires_at": a.portfolio_expires_at.isoformat() if getattr(a, 'portfolio_expires_at', None) else None,
            "addon_portfolio_price": getattr(a, 'addon_portfolio_price', 0.0),
            "seller_package_id": a.seller_package_id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "telegram_bot_url": tg_url,
            "whatsapp_bot_url": wa_url,
            "invite_url": invite_url,
            "telegram_bot_username": tg_bot_user
        })
    return results


@router.get("/me/agents/{agent_id}")
async def get_my_agent_detail(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: Get full details and QR bot connection URLs for a specific agent."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    stmt = select(Tenant).where(Tenant.id == agent_id, Tenant.seller_id == seller.id)
    res = await db.execute(stmt)
    agent = res.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent tapılmadı")

    search_cnt_stmt = select(func.count(SavedSearch.id)).where(SavedSearch.tenant_id == agent.id)
    search_cnt_res = await db.execute(search_cnt_stmt)
    saved_searches_count = search_cnt_res.scalar() or 0

    match_cnt_stmt = select(func.count(Match.id)).where(Match.tenant_id == agent.id)
    match_cnt_res = await db.execute(match_cnt_stmt)
    matches_count = match_cnt_res.scalar() or 0

    pkg_data = None
    plan_price = 0.0
    if agent.seller_package_id:
        p_stmt = select(SellerPackage).where(SellerPackage.id == agent.seller_package_id)
        p_res = await db.execute(p_stmt)
        pkg = p_res.scalars().first()
        if pkg:
            plan_price = pkg.price
            pkg_data = {
                "id": pkg.id,
                "name": pkg.name,
                "price": pkg.price,
                "period": pkg.period,
                "duration_days": pkg.duration_days,
                "max_searches": pkg.max_searches,
                "max_locations": pkg.max_locations,
                "addon_aged_tiers": pkg.addon_aged_tiers or [],
                "addon_search_tiers": pkg.addon_search_tiers or [],
                "feature_watermark_free_images": getattr(pkg, 'feature_watermark_free_images', False),
                "included_image_requests": getattr(pkg, 'included_image_requests', 0),
                "addon_image_requests_price": getattr(pkg, 'addon_image_requests_price', 10.0),
                "addon_image_tiers": getattr(pkg, 'addon_image_tiers', []) or []
            }
    else:
        # Check latest payment or global Plan price
        last_pay_stmt = select(Payment.amount).where(Payment.tenant_id == agent.id).order_by(Payment.received_at.desc())
        last_pay_res = await db.execute(last_pay_stmt)
        last_amount = last_pay_res.scalars().first()
        if last_amount is not None and last_amount > 0:
            plan_price = last_amount
        else:
            plan_stmt = select(Plan.price).where(or_(Plan.code == agent.plan, Plan.name == agent.plan))
            plan_res = await db.execute(plan_stmt)
            p_price = plan_res.scalars().first()
            if p_price is not None:
                plan_price = p_price
            elif agent.plan in ["pro", "agency"]:
                plan_price = 99.0
            elif agent.plan in ["starter"]:
                plan_price = 49.0

    settings_stmt = select(AppSettings).where(AppSettings.key.in_(["telegram_bot_username", "whatsapp_bot_phone", "app_name"]))
    settings_res = await db.execute(settings_stmt)
    settings_map = {s.key: s.value for s in settings_res.scalars().all()}
    tg_bot_user = settings_map.get("telegram_bot_username", "baku_realestate_ai_bot").lstrip("@")
    wa_bot_phone = settings_map.get("whatsapp_bot_phone", "+994501234567").replace("+", "").replace(" ", "")

    tg_url = f"https://t.me/{tg_bot_user}?start=agent_{agent.id}"
    wa_url = f"https://wa.me/{wa_bot_phone}?text=START_{agent.id}"
    invite_url = tg_url if agent.preferred_channel == "telegram" else wa_url

    is_expired = _is_expired(agent.plan_expires_at)

    return {
        "id": agent.id,
        "name": agent.name,
        "phone": agent.phone,
        "telegram_handle": agent.telegram_handle,
        "whatsapp_number": agent.whatsapp_number,
        "preferred_channel": agent.preferred_channel,
        "plan": pkg_data["name"] if pkg_data else agent.plan,
        "plan_price": plan_price,
        "is_transferred": agent.seller_package_id is None,
        "status": agent.status,
        "is_expired": is_expired,
        "plan_started_at": agent.plan_started_at.isoformat() if agent.plan_started_at else None,
        "plan_expires_at": agent.plan_expires_at.isoformat() if agent.plan_expires_at else None,
        "preferred_billing_day": getattr(agent, 'preferred_billing_day', 1) or 1,
        "feature_makler_detector": agent.feature_makler_detector,
        "feature_avm_bargain_finder": agent.feature_avm_bargain_finder,
        "feature_social_brochure": agent.feature_social_brochure,
        "feature_multi_location": agent.feature_multi_location,
        "max_locations_per_search": agent.max_locations_per_search,
        "feature_client_intake_bot": agent.feature_client_intake_bot,
        "backup_enabled": agent.backup_enabled,
        "feature_aged_listings": agent.feature_aged_listings,
        "addon_aged_max_months": agent.addon_aged_max_months,
        "aged_expires_at": agent.aged_expires_at.isoformat() if getattr(agent, 'aged_expires_at', None) else None,
        "addon_saved_searches": agent.addon_saved_searches,
        "addon_saved_searches_price": agent.addon_saved_searches_price,
        "feature_watermark_free_images": getattr(agent, 'feature_watermark_free_images', False),
        "addon_image_requests_limit": getattr(agent, 'addon_image_requests_limit', 0),
        "addon_image_requests_used": getattr(agent, 'addon_image_requests_used', 0),
        "addon_image_requests_price": getattr(agent, 'addon_image_requests_price', 0.0),
        "feature_crm": getattr(agent, 'feature_crm', False),
        "crm_expires_at": agent.crm_expires_at.isoformat() if getattr(agent, 'crm_expires_at', None) else None,
        "feature_portfolio": getattr(agent, 'feature_portfolio', False),
        "portfolio_limit": getattr(agent, 'portfolio_limit', 25),
        "portfolio_expires_at": agent.portfolio_expires_at.isoformat() if getattr(agent, 'portfolio_expires_at', None) else None,
        "addon_portfolio_price": getattr(agent, 'addon_portfolio_price', 0.0),
        "seller_package_id": agent.seller_package_id,
        "package_data": pkg_data,
        "saved_searches_count": saved_searches_count,
        "matches_count": matches_count,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "telegram_bot_url": tg_url,
        "whatsapp_bot_url": wa_url,
        "invite_url": invite_url,
        "telegram_bot_username": tg_bot_user
    }


@router.put("/me/agents/{agent_id}")
async def update_my_agent(
    agent_id: int,
    body: UpdateSellerAgentRequest,
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: Update agent contact information, preferred channel, status, and feature flags."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    stmt = select(Tenant).where(Tenant.id == agent_id, Tenant.seller_id == seller.id)
    res = await db.execute(stmt)
    agent = res.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent tapılmadı")

    from app.core.baku_locations import extract_az_phone

    if body.phone is not None and body.phone.strip():
        clean_phone = body.phone.strip()
        p_res = extract_az_phone(clean_phone)
        formatted_phone = p_res[0] if p_res else clean_phone
        raw_phone = p_res[1] if p_res else clean_phone

        if formatted_phone != agent.phone:
            stmt_check = select(Tenant).where(
                Tenant.id != agent.id,
                or_(
                    Tenant.phone == formatted_phone,
                    Tenant.phone == raw_phone,
                    Tenant.whatsapp_number == formatted_phone,
                    Tenant.whatsapp_number == raw_phone
                )
            )
            res_check = await db.execute(stmt_check)
            if res_check.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bu telefon nömrəsi artıq başqa bir agent üçün qeydiyyatdan keçib."
                )
            agent.phone = formatted_phone

    if body.name is not None and body.name.strip():
        agent.name = body.name.strip()
    if body.telegram_handle is not None:
        h = body.telegram_handle.strip().lstrip('@')
        agent.telegram_handle = h or None
        if h and h.isdigit() and not body.telegram_chat_id:
            agent.telegram_chat_id = h
    if body.telegram_chat_id is not None:
        cid = body.telegram_chat_id.strip()
        agent.telegram_chat_id = cid or None
        if cid and cid.isdigit() and not agent.telegram_handle:
            agent.telegram_handle = cid
    if body.whatsapp_number is not None:
        agent.whatsapp_number = body.whatsapp_number.strip() or None
    if body.preferred_channel is not None:
        agent.preferred_channel = body.preferred_channel
    if body.preferred_billing_day is not None:
        agent.preferred_billing_day = max(1, min(28, int(body.preferred_billing_day)))
    if body.status is not None:
        agent.status = body.status
    if body.feature_makler_detector is not None:
        agent.feature_makler_detector = body.feature_makler_detector
    if body.feature_avm_bargain_finder is not None:
        agent.feature_avm_bargain_finder = body.feature_avm_bargain_finder
    if body.feature_social_brochure is not None:
        agent.feature_social_brochure = body.feature_social_brochure
    if body.feature_multi_location is not None:
        agent.feature_multi_location = body.feature_multi_location
    if body.max_locations_per_search is not None:
        agent.max_locations_per_search = max(1, min(20, body.max_locations_per_search))
    if body.feature_client_intake_bot is not None:
        agent.feature_client_intake_bot = body.feature_client_intake_bot
    if body.backup_enabled is not None:
        agent.backup_enabled = body.backup_enabled
    if body.feature_aged_listings is not None:
        agent.feature_aged_listings = body.feature_aged_listings
    if body.addon_aged_max_months is not None:
        agent.addon_aged_max_months = body.addon_aged_max_months
    if body.addon_saved_searches is not None:
        agent.addon_saved_searches = body.addon_saved_searches
    if body.feature_watermark_free_images is not None:
        agent.feature_watermark_free_images = body.feature_watermark_free_images
    if body.addon_image_requests_limit is not None:
        agent.addon_image_requests_limit = body.addon_image_requests_limit
    if body.addon_image_requests_used is not None:
        agent.addon_image_requests_used = body.addon_image_requests_used
    if body.feature_crm is not None:
        agent.feature_crm = body.feature_crm
        if body.feature_crm:
            now_utc = datetime.now(timezone.utc)
            if not agent.crm_expires_at or agent.crm_expires_at < now_utc:
                agent.crm_expires_at = agent.plan_expires_at or (now_utc + timedelta(days=30))
    if body.feature_portfolio is not None:
        agent.feature_portfolio = body.feature_portfolio
        if body.feature_portfolio:
            now_utc = datetime.now(timezone.utc)
            if not agent.portfolio_expires_at or agent.portfolio_expires_at < now_utc:
                agent.portfolio_expires_at = agent.plan_expires_at or (now_utc + timedelta(days=30))
    if body.portfolio_limit is not None:
        agent.portfolio_limit = body.portfolio_limit
    if body.addon_portfolio_price is not None:
        agent.addon_portfolio_price = body.addon_portfolio_price

    await db.commit()
    await db.refresh(agent)

    return {"message": "Agent məlumatları uğurla yeniləndi", "agent_id": agent.id}


@router.post("/me/agents/{agent_id}/renew")
async def renew_my_agent(
    agent_id: int,
    body: RenewSellerAgentRequest,
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: Renew or extend an agent's subscription with package and selected addon tiers."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    stmt = select(Tenant).where(Tenant.id == agent_id, Tenant.seller_id == seller.id)
    res = await db.execute(stmt)
    agent = res.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent tapılmadı")

    from datetime import timedelta
    if agent.plan_expires_at and not _is_expired(agent.plan_expires_at):
        base_expiry = agent.plan_expires_at
    else:
        base_expiry = datetime.now(timezone.utc)

    # 1. If a specific SellerPackage is selected (> 0)
    if body.package_id and body.package_id > 0:
        p_stmt = select(SellerPackage).where(
            SellerPackage.id == body.package_id,
            SellerPackage.seller_id == seller.id,
            SellerPackage.is_active == True
        )
        p_res = await db.execute(p_stmt)
        package = p_res.scalars().first()
        if not package:
            raise HTTPException(status_code=404, detail="Seçilmiş paket tapılmadı və ya aktiv deyil.")

        duration_days = package.duration_days or 30
        new_expires_at = base_expiry + timedelta(days=duration_days)

        if body.selected_aged_months is not None and body.selected_aged_months > 0:
            f_aged = True
            aged_months = int(body.selected_aged_months)
        else:
            f_aged = package.feature_aged_listings
            aged_months = package.addon_aged_max_months

        if body.selected_extra_searches is not None and body.selected_extra_searches > 0:
            addon_searches = int(body.selected_extra_searches)
            addon_searches_price = float(body.selected_extra_searches_price or 0.0)
        else:
            addon_searches = package.addon_saved_searches
            addon_searches_price = package.addon_saved_searches_price

        # Image Add-on Handling
        if body.selected_image_requests is not None and body.selected_image_requests > 0:
            f_images = True
            addon_images = int(body.selected_image_requests)
            addon_images_price = float(body.selected_image_price or 0.0)
        else:
            f_images = getattr(package, 'feature_watermark_free_images', False)
            addon_images = getattr(package, 'included_image_requests', 0)
            addon_images_price = getattr(package, 'addon_image_requests_price', 0.0)

        agent.plan = package.name
        agent.seller_package_id = package.id
        agent.status = "active"
        agent.plan_expires_at = new_expires_at
        agent.feature_makler_detector = package.feature_makler_detector
        agent.feature_avm_bargain_finder = package.feature_avm_bargain_finder
        agent.feature_social_brochure = package.feature_social_brochure
        agent.feature_multi_location = package.feature_multi_location
        agent.max_locations_per_search = package.max_locations
        agent.feature_client_intake_bot = package.feature_client_intake_bot
        agent.backup_enabled = package.feature_backup_service
        agent.feature_aged_listings = f_aged
        agent.addon_aged_max_months = aged_months
        agent.addon_saved_searches = addon_searches
        agent.addon_saved_searches_price = addon_searches_price
        agent.feature_watermark_free_images = f_images
        agent.addon_image_requests_limit = addon_images
        agent.addon_image_requests_price = addon_images_price
        agent.addon_image_requests_used = 0

        # Preferred Billing Day
        if body.preferred_billing_day is not None:
            agent.preferred_billing_day = max(1, min(28, int(body.preferred_billing_day)))

        # CRM Mini App Add-on Handling with Independent Expiry
        selected_crm_price = max(0.0, float(body.selected_crm_price or 0.0))
        now_utc = datetime.now(timezone.utc)
        crm_months = int(body.selected_crm_months or 1)
        norm_crm_exp = _normalize_dt(agent.crm_expires_at)
        if body.selected_crm_enabled is not None:
            agent.feature_crm = bool(body.selected_crm_enabled)
            agent.addon_crm_price = selected_crm_price if body.selected_crm_enabled else 0.0
            if body.selected_crm_enabled:
                base_crm_exp = norm_crm_exp if (norm_crm_exp and norm_crm_exp > now_utc) else now_utc
                agent.crm_expires_at = base_crm_exp + timedelta(days=crm_months * 30)
        elif selected_crm_price > 0:
            agent.feature_crm = True
            agent.addon_crm_price = selected_crm_price
            base_crm_exp = norm_crm_exp if (norm_crm_exp and norm_crm_exp > now_utc) else now_utc
            agent.crm_expires_at = base_crm_exp + timedelta(days=crm_months * 30)
        else:
            agent.feature_crm = package.feature_crm
            agent.addon_crm_price = package.addon_crm_price if package.feature_crm else 0.0
            if package.feature_crm:
                base_crm_exp = norm_crm_exp if (norm_crm_exp and norm_crm_exp > now_utc) else now_utc
                agent.crm_expires_at = base_crm_exp + timedelta(days=30)

        # Agent Portfolio Add-on Handling with Independent Expiry
        selected_portfolio_price = max(0.0, float(body.selected_portfolio_price or 0.0))
        portfolio_limit_val = int(body.selected_portfolio_limit or 25)
        norm_port_exp = _normalize_dt(agent.portfolio_expires_at)
        if body.selected_portfolio_enabled is not None:
            agent.feature_portfolio = bool(body.selected_portfolio_enabled)
            agent.portfolio_limit = portfolio_limit_val
            agent.addon_portfolio_price = selected_portfolio_price if body.selected_portfolio_enabled else 0.0
            if body.selected_portfolio_enabled:
                base_port_exp = norm_port_exp if (norm_port_exp and norm_port_exp > now_utc) else now_utc
                agent.portfolio_expires_at = base_port_exp + timedelta(days=30)
        elif selected_portfolio_price > 0:
            agent.feature_portfolio = True
            agent.portfolio_limit = portfolio_limit_val
            agent.addon_portfolio_price = selected_portfolio_price
            base_port_exp = norm_port_exp if (norm_port_exp and norm_port_exp > now_utc) else now_utc
            agent.portfolio_expires_at = base_port_exp + timedelta(days=30)
        else:
            agent.feature_portfolio = getattr(package, 'feature_portfolio', False)
            agent.portfolio_limit = getattr(package, 'addon_portfolio_limit', 25) or 25
            agent.addon_portfolio_price = getattr(package, 'addon_portfolio_price', 0.0) if getattr(package, 'feature_portfolio', False) else 0.0
            if getattr(package, 'feature_portfolio', False):
                base_port_exp = norm_port_exp if (norm_port_exp and norm_port_exp > now_utc) else now_utc
                agent.portfolio_expires_at = base_port_exp + timedelta(days=30)

        # Aged Archive Add-on Handling with Independent Expiry
        if body.selected_aged_months is not None and body.selected_aged_months > 0:
            norm_aged_exp = _normalize_dt(agent.aged_expires_at)
            base_aged_exp = norm_aged_exp if (norm_aged_exp and norm_aged_exp > now_utc) else now_utc
            agent.aged_expires_at = base_aged_exp + timedelta(days=int(body.selected_aged_months) * 30)

        base_price = package.price
        if getattr(package, 'sale_enabled', False) and getattr(package, 'sale_price', None) is not None and package.sale_price > 0:
            base_price = package.sale_price
        pkg_tx_id = package.id
        desc_plan = f"Paket Yenilənməsi: {agent.name} ({package.name})"
    else:
        # 2. Keep transferred / existing plan and preserve ALL features intact
        duration_days = 30
        new_expires_at = base_expiry + timedelta(days=duration_days)
        agent.status = "active"
        agent.plan_expires_at = new_expires_at

        # Preferred Billing Day
        if body.preferred_billing_day is not None:
            agent.preferred_billing_day = max(1, min(28, int(body.preferred_billing_day)))

        # CRM Mini App Add-on Handling for custom/transferred
        selected_crm_price = max(0.0, float(body.selected_crm_price or 0.0))
        now_utc = datetime.now(timezone.utc)
        crm_months = int(body.selected_crm_months or 1)
        norm_crm_exp = _normalize_dt(agent.crm_expires_at)
        if body.selected_crm_enabled is not None:
            agent.feature_crm = bool(body.selected_crm_enabled)
            agent.addon_crm_price = selected_crm_price if body.selected_crm_enabled else 0.0
            if body.selected_crm_enabled:
                base_crm_exp = norm_crm_exp if (norm_crm_exp and norm_crm_exp > now_utc) else now_utc
                agent.crm_expires_at = base_crm_exp + timedelta(days=crm_months * 30)
        elif selected_crm_price > 0:
            agent.feature_crm = True
            agent.addon_crm_price = selected_crm_price
            base_crm_exp = norm_crm_exp if (norm_crm_exp and norm_crm_exp > now_utc) else now_utc
            agent.crm_expires_at = base_crm_exp + timedelta(days=crm_months * 30)

        # Agent Portfolio Add-on Handling for custom/transferred
        selected_portfolio_price = max(0.0, float(body.selected_portfolio_price or 0.0))
        portfolio_limit_val = int(body.selected_portfolio_limit or 25)
        norm_port_exp = _normalize_dt(agent.portfolio_expires_at)
        if body.selected_portfolio_enabled is not None:
            agent.feature_portfolio = bool(body.selected_portfolio_enabled)
            agent.portfolio_limit = portfolio_limit_val
            agent.addon_portfolio_price = selected_portfolio_price if body.selected_portfolio_enabled else 0.0
            if body.selected_portfolio_enabled:
                base_port_exp = norm_port_exp if (norm_port_exp and norm_port_exp > now_utc) else now_utc
                agent.portfolio_expires_at = base_port_exp + timedelta(days=30)
        elif selected_portfolio_price > 0:
            agent.feature_portfolio = True
            agent.portfolio_limit = portfolio_limit_val
            agent.addon_portfolio_price = selected_portfolio_price
            base_port_exp = norm_port_exp if (norm_port_exp and norm_port_exp > now_utc) else now_utc
            agent.portfolio_expires_at = base_port_exp + timedelta(days=30)

        # Aged Archive Add-on Handling with Independent Expiry
        if body.selected_aged_months is not None and body.selected_aged_months > 0:
            agent.feature_aged_listings = True
            agent.addon_aged_max_months = int(body.selected_aged_months)
            norm_aged_exp = _normalize_dt(agent.aged_expires_at)
            base_aged_exp = norm_aged_exp if (norm_aged_exp and norm_aged_exp > now_utc) else now_utc
            agent.aged_expires_at = base_aged_exp + timedelta(days=int(body.selected_aged_months) * 30)

        # Determine price from custom_price, latest payment, plan table, or fallback
        if body.custom_price is not None and body.custom_price > 0:
            base_price = float(body.custom_price)
        else:
            last_pay_stmt = select(Payment.amount).where(Payment.tenant_id == agent.id).order_by(Payment.received_at.desc())
            last_pay_res = await db.execute(last_pay_stmt)
            last_amount = last_pay_res.scalars().first()
            if last_amount is not None and last_amount > 0:
                base_price = last_amount
            else:
                plan_stmt = select(Plan.price).where(or_(Plan.code == agent.plan, Plan.name == agent.plan))
                plan_res = await db.execute(plan_stmt)
                p_price = plan_res.scalars().first()
                if p_price is not None:
                    base_price = p_price
                elif agent.plan in ["pro", "agency"]:
                    base_price = 99.0
                elif agent.plan in ["starter"]:
                    base_price = 49.0
                else:
                    base_price = 50.0

        pkg_tx_id = agent.seller_package_id
        desc_plan = f"Köçürülmüş Plan Yenilənməsi: {agent.name} ({agent.plan})"

    if base_price > 0 or selected_crm_price > 0 or selected_portfolio_price > 0:
        rank_map = await get_seller_rank_config_map(db)
        rank_info = rank_map.get(seller.rank, rank_map.get("Bronze", {}))
        bonus_pct = rank_info.get("bonus_commission", 0.0)
        effective_commission_pct = min(100.0, seller.commission_rate + bonus_pct)

        selected_aged_price = max(0.0, float(body.selected_aged_price or 0.0))
        selected_extra_searches_price = max(0.0, float(body.selected_extra_searches_price or 0.0))
        selected_image_price = max(0.0, float(body.selected_image_price or 0.0))
        gross_amount = round(base_price + selected_aged_price + selected_extra_searches_price + selected_image_price + selected_crm_price + selected_portfolio_price, 2)

        seller_profit = round(gross_amount * (effective_commission_pct / 100.0), 2)
        platform_fee = round(gross_amount - seller_profit, 2)

        seller.balance += seller_profit
        seller.total_earnings += seller_profit
        seller.total_sales_volume += gross_amount

        for rank_name, min_vol in [("Diamond", 10000.0), ("Platinum", 5000.0), ("Gold", 2000.0), ("Silver", 500.0), ("Bronze", 0.0)]:
            if seller.total_sales_volume >= min_vol:
                seller.rank = rank_name
                break

        tx = SellerTransaction(
            seller_id=seller.id,
            tenant_id=agent.id,
            package_id=pkg_tx_id,
            amount=gross_amount,
            commission_rate=effective_commission_pct,
            seller_profit=seller_profit,
            platform_fee=platform_fee,
            type="subscription_sale",
            description=f"{desc_plan} [Bonus: +{bonus_pct}%]"
        )
        db.add(tx)

        # Create confirmed Payment record for this agent
        pay_record = Payment(
            tenant_id=agent.id,
            amount=gross_amount,
            currency="AZN",
            period_covered_start=base_expiry,
            period_covered_end=new_expires_at,
            received_at=datetime.now(timezone.utc),
            notes=f"Seller Renewal: {desc_plan} (Aged: {selected_aged_price} AZN, Searches: {selected_extra_searches_price} AZN, Images: {selected_image_price} AZN, CRM: {selected_crm_price} AZN, Portfel: {selected_portfolio_price} AZN)"
        )
        db.add(pay_record)

    await db.commit()
    await db.refresh(agent)
    await db.refresh(seller)

    return {
        "message": f"Agentin abunəsi uğurla {duration_days} gün müddətinə yeniləndi!",
        "agent_id": agent.id,
        "plan": agent.plan,
        "plan_expires_at": agent.plan_expires_at.isoformat() if agent.plan_expires_at else None,
        "status": agent.status
    }


@router.post("/me/agents", status_code=status.HTTP_201_CREATED)
async def register_my_agent(
    body: RegisterSellerAgentRequest,
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """
    Seller-only: Register a new Agent under my seller account.
    Enforces strict system-wide agent uniqueness. If the agent is already in the system under ANY seller,
    it rejects with: 'Bu agent artıq sistemdə qeydiyyatdan keçib və tətbiqdən istifadə edir.'
    """
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    from app.core.baku_locations import extract_az_phone

    clean_phone = body.phone.strip()
    p_res = extract_az_phone(clean_phone)
    formatted_phone = p_res[0] if p_res else clean_phone
    raw_phone = p_res[1] if p_res else clean_phone

    # 1. Strict System-Wide Agent Uniqueness Check
    # Check Phone Number
    stmt_check_phone = select(Tenant).where(
        or_(
            Tenant.phone == formatted_phone,
            Tenant.phone == raw_phone,
            Tenant.whatsapp_number == formatted_phone,
            Tenant.whatsapp_number == raw_phone
        )
    )
    res_phone = await db.execute(stmt_check_phone)
    if res_phone.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu agent artıq sistemdə qeydiyyatdan keçib və tətbiqdən istifadə edir."
        )

    # Check Telegram Handle if provided
    if body.telegram_handle and body.telegram_handle.strip():
        clean_handle = body.telegram_handle.strip().lstrip('@').lower()
        stmt_check_tg = select(Tenant).where(func.lower(Tenant.telegram_handle) == clean_handle)
        res_tg = await db.execute(stmt_check_tg)
        if res_tg.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu agent artıq sistemdə qeydiyyatdan keçib və tətbiqdən istifadə edir."
            )

    # 2. Check Package if assigned OR Free Trial
    package = None
    is_trial = body.is_trial or (body.package_id is None)
    if not is_trial and body.package_id:
        p_stmt = select(SellerPackage).where(
            SellerPackage.id == body.package_id,
            SellerPackage.seller_id == seller.id,
            SellerPackage.is_active == True
        )
        p_res = await db.execute(p_stmt)
        package = p_res.scalars().first()
        if not package:
            raise HTTPException(status_code=404, detail="Seçilmiş paket tapılmadı və ya aktiv deyil.")

    # 3. Create Tenant Agent
    from datetime import timedelta
    now_utc = datetime.now(timezone.utc)

    if is_trial:
        if not seller.free_trial_enabled:
            raise HTTPException(status_code=400, detail="Satıcı pulsuz sınaq təklifini deaktiv edib. Zəhmət olmasa ödənişli paket seçin.")
        trial_days = seller.free_trial_duration_days or 7
        expires_at = now_utc + timedelta(days=trial_days)
        agent_plan = f"Pulsuz Sınaq ({trial_days} Gün)"
        f_makler = seller.free_trial_feature_makler
        f_avm = seller.free_trial_feature_avm
        f_brochure = seller.free_trial_feature_social_brochure
        f_multiloc = seller.free_trial_feature_multi_location
        max_locs = seller.free_trial_max_locations or 3
        f_bot = False
        f_backup = False
        f_aged = False
        aged_months = 12
        addon_searches = 0
        addon_searches_price = 0.0
        f_images = getattr(seller, 'free_trial_feature_watermark_images', False)
        addon_images = getattr(seller, 'free_trial_image_requests', 5) if f_images else 0
        addon_images_price = 0.0
        f_portfolio = getattr(seller, 'free_trial_feature_portfolio', False)
        portfolio_limit = getattr(seller, 'free_trial_portfolio_limit', 25) or 25
        portfolio_price = 0.0
    else:
        expires_at = now_utc + timedelta(days=package.duration_days if package else 30)
        agent_plan = package.name if package else "starter"
        f_makler = package.feature_makler_detector if package else True
        f_avm = package.feature_avm_bargain_finder if package else True
        f_brochure = package.feature_social_brochure if package else True
        f_multiloc = package.feature_multi_location if package else True
        max_locs = package.max_locations if package else 5
        f_bot = package.feature_client_intake_bot if package else False
        f_backup = package.feature_backup_service if package else False
        
        # Determine aged listings addon
        if body.selected_aged_months is not None and body.selected_aged_months > 0:
            f_aged = True
            aged_months = int(body.selected_aged_months)
        else:
            f_aged = package.feature_aged_listings if package else False
            aged_months = package.addon_aged_max_months if package else 12

        # Determine extra searches addon
        if body.selected_extra_searches is not None and body.selected_extra_searches > 0:
            addon_searches = int(body.selected_extra_searches)
            addon_searches_price = float(body.selected_extra_searches_price or 0.0)
        else:
            addon_searches = package.addon_saved_searches if package else 0
            addon_searches_price = package.addon_saved_searches_price if package else 0.0

        # Determine image requests addon
        if body.selected_image_requests is not None and body.selected_image_requests > 0:
            f_images = True
            addon_images = int(body.selected_image_requests)
            addon_images_price = float(body.selected_image_price or 0.0)
        else:
            f_images = getattr(package, 'feature_watermark_free_images', False) if package else False
            addon_images = getattr(package, 'included_image_requests', 0) if package else 0
            addon_images_price = getattr(package, 'addon_image_requests_price', 0.0) if package else 0.0

        # Determine portfolio addon
        if body.selected_portfolio_enabled is not None:
            f_portfolio = bool(body.selected_portfolio_enabled)
            portfolio_limit = int(body.selected_portfolio_limit or 25)
            portfolio_price = float(body.selected_portfolio_price or 0.0)
        elif body.selected_portfolio_price and float(body.selected_portfolio_price) > 0:
            f_portfolio = True
            portfolio_limit = int(body.selected_portfolio_limit or 25)
            portfolio_price = float(body.selected_portfolio_price)
        else:
            f_portfolio = getattr(package, 'feature_portfolio', False) if package else False
            portfolio_limit = getattr(package, 'addon_portfolio_limit', 25) if package else 25
            portfolio_price = getattr(package, 'addon_portfolio_price', 0.0) if package else 0.0

    crm_enabled = bool(body.selected_crm_enabled or (body.selected_crm_price and body.selected_crm_price > 0))
    crm_months = int(body.selected_crm_months or 1)
    crm_exp = (now_utc + timedelta(days=crm_months * 30)) if crm_enabled else None
    aged_exp = (now_utc + timedelta(days=int(body.selected_aged_months) * 30)) if (body.selected_aged_months and body.selected_aged_months > 0) else None
    portfolio_exp = (now_utc + timedelta(days=30)) if f_portfolio else None

    raw_handle = body.telegram_handle.strip().lstrip('@') if body.telegram_handle else None
    raw_chat_id = body.telegram_chat_id.strip() if body.telegram_chat_id else None
    if raw_handle and raw_handle.isdigit() and not raw_chat_id:
        raw_chat_id = raw_handle
    elif raw_chat_id and raw_chat_id.isdigit() and not raw_handle:
        raw_handle = raw_chat_id

    agent = Tenant(
        name=body.name,
        phone=formatted_phone,
        telegram_handle=raw_handle,
        telegram_chat_id=raw_chat_id,
        whatsapp_number=body.whatsapp_number or formatted_phone,
        preferred_channel=body.preferred_channel,
        preferred_billing_day=max(1, min(28, int(body.preferred_billing_day or 1))),
        seller_id=seller.id,
        seller_package_id=package.id if (package and not is_trial) else None,
        plan=agent_plan,
        status="active",
        plan_started_at=now_utc,
        plan_expires_at=expires_at,
        feature_makler_detector=f_makler,
        feature_avm_bargain_finder=f_avm,
        feature_social_brochure=f_brochure,
        feature_multi_location=f_multiloc,
        max_locations_per_search=max_locs,
        feature_client_intake_bot=f_bot,
        backup_enabled=f_backup,
        feature_aged_listings=f_aged,
        addon_aged_max_months=aged_months,
        aged_expires_at=aged_exp,
        addon_saved_searches=addon_searches,
        addon_saved_searches_price=addon_searches_price,
        feature_watermark_free_images=f_images,
        addon_image_requests_limit=addon_images,
        addon_image_requests_used=0,
        addon_image_requests_price=addon_images_price,
        feature_crm=crm_enabled,
        addon_crm_price=float(body.selected_crm_price or 0.0) if crm_enabled else 0.0,
        crm_expires_at=crm_exp,
        feature_portfolio=f_portfolio,
        portfolio_limit=portfolio_limit,
        portfolio_expires_at=portfolio_exp,
        addon_portfolio_price=portfolio_price
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    # 4. Calculate Commission & Financials
    rank_map = await get_seller_rank_config_map(db)
    rank_info = rank_map.get(seller.rank, rank_map.get("Bronze", {}))
    bonus_pct = rank_info.get("bonus_commission", 0.0)
    effective_commission_pct = min(100.0, seller.commission_rate + bonus_pct)

    effective_pkg_price = 0.0
    pkg_name = package.name if package else "Custom/Trial"
    pkg_id = package.id if package else None
    if package and package.price > 0 and not is_trial:
        effective_pkg_price = package.price
        if getattr(package, 'sale_enabled', False) and getattr(package, 'sale_price', None) is not None and package.sale_price > 0:
            effective_pkg_price = package.sale_price

    # Dynamic Addon Pricing Calculation
    selected_aged_price = max(0.0, float(body.selected_aged_price or 0.0))
    selected_extra_searches_price = max(0.0, float(body.selected_extra_searches_price or 0.0))
    selected_image_price = max(0.0, float(body.selected_image_price or 0.0))
    selected_crm_price = max(0.0, float(body.selected_crm_price or 0.0))
    selected_portfolio_price = max(0.0, float(body.selected_portfolio_price or 0.0))
    gross_amount = round(effective_pkg_price + selected_aged_price + selected_extra_searches_price + selected_image_price + selected_crm_price + selected_portfolio_price, 2)

    if gross_amount > 0:
        seller_profit = round(gross_amount * (effective_commission_pct / 100.0), 2)
        platform_fee = round(gross_amount - seller_profit, 2)

        # Update seller balances
        seller.balance += seller_profit
        seller.total_earnings += seller_profit
        seller.total_sales_volume += gross_amount

        # Check for auto rank upgrade
        for rank_name, min_vol in [("Diamond", 10000.0), ("Platinum", 5000.0), ("Gold", 2000.0), ("Silver", 500.0), ("Bronze", 0.0)]:
            if seller.total_sales_volume >= min_vol:
                seller.rank = rank_name
                break

        # Create transaction record
        tx = SellerTransaction(
            seller_id=seller.id,
            tenant_id=agent.id,
            package_id=pkg_id,
            amount=gross_amount,
            commission_rate=effective_commission_pct,
            seller_profit=seller_profit,
            platform_fee=platform_fee,
            type="subscription_sale",
            description=f"Agent abunəsi: {agent.name} ({pkg_name}) [Bonus: +{bonus_pct}%]"
        )
        db.add(tx)

    # Always create confirmed Payment record for this agent
    pay_record = Payment(
        tenant_id=agent.id,
        amount=gross_amount,
        currency="AZN",
        period_covered_start=now_utc,
        period_covered_end=expires_at,
        received_at=now_utc,
        notes=f"Seller Registration: {agent.name} ({pkg_name}) (Aged: {selected_aged_price} AZN, CRM: {selected_crm_price} AZN)"
    )
    db.add(pay_record)

    await db.commit()
    await db.refresh(seller)

    return {
        "message": "Agent uğurla qeydiyyatdan keçirildi",
        "agent_id": agent.id,
        "name": agent.name,
        "phone": agent.phone,
        "plan": agent.plan,
        "status": agent.status
    }


@router.get("/me/trial-settings")
async def get_my_trial_settings(
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: Get my current free trial offer configuration."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")
    _, max_trial_days = await _get_seller_package_constraints(db)
    return {
        "free_trial_enabled": seller.free_trial_enabled,
        "free_trial_duration_days": seller.free_trial_duration_days,
        "free_trial_max_searches": seller.free_trial_max_searches,
        "free_trial_max_locations": seller.free_trial_max_locations,
        "free_trial_feature_makler": seller.free_trial_feature_makler,
        "free_trial_feature_avm": seller.free_trial_feature_avm,
        "free_trial_feature_social_brochure": seller.free_trial_feature_social_brochure,
        "free_trial_feature_multi_location": seller.free_trial_feature_multi_location,
        "free_trial_feature_watermark_images": getattr(seller, 'free_trial_feature_watermark_images', False),
        "free_trial_image_requests": getattr(seller, 'free_trial_image_requests', 5),
        "free_trial_feature_crm": getattr(seller, 'free_trial_feature_crm', False),
        "free_trial_feature_portfolio": getattr(seller, 'free_trial_feature_portfolio', False),
        "free_trial_portfolio_limit": getattr(seller, 'free_trial_portfolio_limit', 25),
        "admin_max_trial_days": max_trial_days
    }


@router.post("/me/trial-settings")
async def update_my_trial_settings(
    body: UpdateFreeTrialSettingsRequest,
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: Configure what capabilities and duration agents get during free trial."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    _, max_trial_days = await _get_seller_package_constraints(db)

    if body.free_trial_duration_days is not None:
        if body.free_trial_duration_days <= 0 or body.free_trial_duration_days > max_trial_days:
            raise HTTPException(
                status_code=400,
                detail=f"Sınaq müddəti 1 ilə {max_trial_days} gün arasında olmalıdır."
            )
        seller.free_trial_duration_days = body.free_trial_duration_days

    if body.free_trial_enabled is not None:
        seller.free_trial_enabled = body.free_trial_enabled
    if body.free_trial_max_searches is not None:
        seller.free_trial_max_searches = max(1, min(20, body.free_trial_max_searches))
    if body.free_trial_max_locations is not None:
        seller.free_trial_max_locations = max(1, min(10, body.free_trial_max_locations))
    if body.free_trial_feature_makler is not None:
        seller.free_trial_feature_makler = body.free_trial_feature_makler
    if body.free_trial_feature_avm is not None:
        seller.free_trial_feature_avm = body.free_trial_feature_avm
    if body.free_trial_feature_social_brochure is not None:
        seller.free_trial_feature_social_brochure = body.free_trial_feature_social_brochure
    if body.free_trial_feature_multi_location is not None:
        seller.free_trial_feature_multi_location = body.free_trial_feature_multi_location
    if body.free_trial_feature_watermark_images is not None:
        seller.free_trial_feature_watermark_images = body.free_trial_feature_watermark_images
    if body.free_trial_image_requests is not None:
        seller.free_trial_image_requests = max(0, min(50, body.free_trial_image_requests))
    if body.free_trial_feature_crm is not None:
        seller.free_trial_feature_crm = body.free_trial_feature_crm
    if body.free_trial_feature_portfolio is not None:
        seller.free_trial_feature_portfolio = body.free_trial_feature_portfolio
    if body.free_trial_portfolio_limit is not None:
        seller.free_trial_portfolio_limit = max(1, min(100, body.free_trial_portfolio_limit))

    await db.commit()
    await db.refresh(seller)
    return {"message": "Pulsuz sınaq parametrləri yadda saxlanıldı"}


@router.get("/me/packages", response_model=List[dict])
async def get_my_packages(
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: List my custom packages."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    stmt = select(SellerPackage).where(SellerPackage.seller_id == seller.id).order_by(SellerPackage.price.asc())
    res = await db.execute(stmt)
    packages = res.scalars().all()

    return [{
        "id": p.id,
        "seller_id": p.seller_id,
        "name": p.name,
        "description": p.description,
        "price": p.price,
        "period": p.period,
        "duration_days": p.duration_days,
        "max_searches": p.max_searches,
        "max_locations": p.max_locations,
        "feature_makler_detector": p.feature_makler_detector,
        "feature_avm_bargain_finder": p.feature_avm_bargain_finder,
        "feature_social_brochure": p.feature_social_brochure,
        "feature_multi_location": p.feature_multi_location,
        "feature_client_intake_bot": p.feature_client_intake_bot,
        "feature_backup_service": p.feature_backup_service,
        "feature_aged_listings": p.feature_aged_listings,
        "addon_aged_listings_price": p.addon_aged_listings_price,
        "addon_aged_max_months": p.addon_aged_max_months,
        "addon_aged_tiers": p.addon_aged_tiers or [],
        "addon_saved_searches": p.addon_saved_searches,
        "addon_saved_searches_price": p.addon_saved_searches_price,
        "addon_search_tiers": p.addon_search_tiers or [],
        "feature_watermark_free_images": getattr(p, 'feature_watermark_free_images', False),
        "included_image_requests": getattr(p, 'included_image_requests', 0),
        "addon_image_requests_price": getattr(p, 'addon_image_requests_price', 10.0),
        "addon_image_tiers": getattr(p, 'addon_image_tiers', []) or [],
        "feature_crm": getattr(p, 'feature_crm', False),
        "addon_crm_price": getattr(p, 'addon_crm_price', 15.0),
        "addon_crm_tiers": getattr(p, 'addon_crm_tiers', []) or [],
        "feature_portfolio": getattr(p, 'feature_portfolio', False),
        "addon_portfolio_price": getattr(p, 'addon_portfolio_price', 15.0),
        "addon_portfolio_limit": getattr(p, 'addon_portfolio_limit', 25),
        "addon_portfolio_tiers": getattr(p, 'addon_portfolio_tiers', []) or [],
        "sale_enabled": getattr(p, 'sale_enabled', False),
        "sale_price": getattr(p, 'sale_price', None),
        "sale_discount_percent": getattr(p, 'sale_discount_percent', None),
        "sale_type": getattr(p, 'sale_type', 'permanent'),
        "sale_expires_at": p.sale_expires_at.isoformat() if getattr(p, 'sale_expires_at', None) else None,
        "sale_badge_label": getattr(p, 'sale_badge_label', None),
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else None
    } for p in packages]


async def _get_seller_package_constraints(db: AsyncSession) -> tuple[float, int]:
    from app.models.setting import AppSettings
    stmt = select(AppSettings).where(AppSettings.key.in_(["seller_min_package_price", "seller_max_trial_days"]))
    res = await db.execute(stmt)
    settings_map = {s.key: s.value for s in res.scalars().all()}

    try:
        min_price = float(settings_map.get("seller_min_package_price", "29.0"))
    except (ValueError, TypeError):
        min_price = 29.0

    try:
        max_trial_days = int(settings_map.get("seller_max_trial_days", "14"))
    except (ValueError, TypeError):
        max_trial_days = 14

    return min_price, max_trial_days


@router.post("/me/packages", status_code=status.HTTP_201_CREATED)
async def create_my_package(
    body: CreatePackageRequest,
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: Create a new custom package with admin minimum price constraints. Free trials are disabled for sellers."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    min_price, _ = await _get_seller_package_constraints(db)

    from app.models.seller import SELLER_RANK_CONFIG
    rank_info = SELLER_RANK_CONFIG.get(seller.rank, SELLER_RANK_CONFIG["Bronze"])
    max_pkgs = rank_info.get("max_packages", 5)

    pkg_cnt_stmt = select(func.count(SellerPackage.id)).where(SellerPackage.seller_id == seller.id, SellerPackage.is_active == True)
    pkg_cnt_res = await db.execute(pkg_cnt_stmt)
    current_active_pkgs = pkg_cnt_res.scalar() or 0

    if current_active_pkgs >= max_pkgs:
        raise HTTPException(
            status_code=400,
            detail=f"Sizin '{seller.rank}' səviyyəniz üçün maksimum {max_pkgs} paket limiti dolub. Satış həcminizi artıraraq növbəti səviyyəyə yüksələ bilərsiniz."
        )

    # 1. Sellers cannot add free trial (0 AZN) packages
    if body.price < min_price:
        raise HTTPException(
            status_code=400,
            detail=f"Paket qiyməti minimum {min_price:.2f} AZN olmalıdır. Satıcılar pulsuz sınaq paketi yarada bilməz."
        )

    # Calculate sale price & discount percent
    final_sale_price = body.sale_price
    final_discount_pct = body.sale_discount_percent
    if body.sale_enabled:
        if final_sale_price is None and final_discount_pct is not None and final_discount_pct > 0:
            final_sale_price = round(body.price * (1 - final_discount_pct / 100.0), 2)
        elif final_sale_price is not None and final_discount_pct is None and body.price > 0:
            final_discount_pct = round(((body.price - final_sale_price) / body.price) * 100.0, 1)

    pkg = SellerPackage(
        seller_id=seller.id,
        name=body.name,
        description=body.description,
        price=body.price,
        period=body.period,
        duration_days=body.duration_days,
        max_searches=body.max_searches,
        max_locations=body.max_locations,
        feature_makler_detector=body.feature_makler_detector,
        feature_avm_bargain_finder=body.feature_avm_bargain_finder,
        feature_social_brochure=body.feature_social_brochure,
        feature_multi_location=body.feature_multi_location,
        feature_client_intake_bot=body.feature_client_intake_bot,
        feature_backup_service=body.feature_backup_service,
        feature_aged_listings=body.feature_aged_listings,
        addon_aged_listings_price=body.addon_aged_listings_price,
        addon_aged_max_months=body.addon_aged_max_months,
        addon_aged_tiers=body.addon_aged_tiers or [],
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
        sale_enabled=body.sale_enabled,
        sale_price=final_sale_price,
        sale_discount_percent=final_discount_pct,
        sale_type=body.sale_type or "permanent",
        sale_expires_at=body.sale_expires_at,
        sale_badge_label=body.sale_badge_label,
        is_active=True
    )
    db.add(pkg)
    await db.commit()
    await db.refresh(pkg)

    return {"message": "Paket uğurla yaradıldı", "package_id": pkg.id}


@router.put("/me/packages/{package_id}")
async def update_my_package(
    package_id: int,
    body: UpdatePackageRequest,
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: Update a custom package with admin constraints."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    stmt = select(SellerPackage).where(SellerPackage.id == package_id, SellerPackage.seller_id == seller.id)
    res = await db.execute(stmt)
    pkg = res.scalars().first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Paket tapılmadı")

    min_price, _ = await _get_seller_package_constraints(db)

    target_price = body.price if body.price is not None else pkg.price

    if target_price < min_price:
        raise HTTPException(
            status_code=400,
            detail=f"Paket qiyməti minimum {min_price:.2f} AZN olmalıdır. Satıcılar pulsuz sınaq paketi yarada bilməz."
        )

    if body.name is not None:
        pkg.name = body.name
    if body.price is not None:
        pkg.price = body.price
    if body.description is not None:
        pkg.description = body.description
    if body.period is not None:
        pkg.period = body.period
    if body.duration_days is not None:
        pkg.duration_days = body.duration_days
    if body.max_searches is not None:
        pkg.max_searches = body.max_searches
    if body.max_locations is not None:
        pkg.max_locations = body.max_locations
    if body.feature_makler_detector is not None:
        pkg.feature_makler_detector = body.feature_makler_detector
    if body.feature_avm_bargain_finder is not None:
        pkg.feature_avm_bargain_finder = body.feature_avm_bargain_finder
    if body.feature_social_brochure is not None:
        pkg.feature_social_brochure = body.feature_social_brochure
    if body.feature_multi_location is not None:
        pkg.feature_multi_location = body.feature_multi_location
    if body.feature_client_intake_bot is not None:
        pkg.feature_client_intake_bot = body.feature_client_intake_bot
    if body.feature_backup_service is not None:
        pkg.feature_backup_service = body.feature_backup_service
    if body.feature_aged_listings is not None:
        pkg.feature_aged_listings = body.feature_aged_listings
    if body.addon_aged_listings_price is not None:
        pkg.addon_aged_listings_price = body.addon_aged_listings_price
    if body.addon_aged_max_months is not None:
        pkg.addon_aged_max_months = body.addon_aged_max_months
    if body.addon_aged_tiers is not None:
        pkg.addon_aged_tiers = body.addon_aged_tiers
    if body.addon_saved_searches is not None:
        pkg.addon_saved_searches = body.addon_saved_searches
    if body.addon_saved_searches_price is not None:
        pkg.addon_saved_searches_price = body.addon_saved_searches_price
    if body.addon_search_tiers is not None:
        pkg.addon_search_tiers = body.addon_search_tiers
    if body.feature_watermark_free_images is not None:
        pkg.feature_watermark_free_images = body.feature_watermark_free_images
    if body.included_image_requests is not None:
        pkg.included_image_requests = body.included_image_requests
    if body.addon_image_requests_price is not None:
        pkg.addon_image_requests_price = body.addon_image_requests_price
    if body.addon_image_tiers is not None:
        pkg.addon_image_tiers = body.addon_image_tiers
    if body.feature_crm is not None:
        pkg.feature_crm = body.feature_crm
    if body.addon_crm_price is not None:
        pkg.addon_crm_price = body.addon_crm_price
    if body.addon_crm_tiers is not None:
        pkg.addon_crm_tiers = body.addon_crm_tiers
    if body.feature_portfolio is not None:
        pkg.feature_portfolio = body.feature_portfolio
    if body.addon_portfolio_price is not None:
        pkg.addon_portfolio_price = body.addon_portfolio_price
    if body.addon_portfolio_limit is not None:
        pkg.addon_portfolio_limit = body.addon_portfolio_limit
    if body.addon_portfolio_tiers is not None:
        pkg.addon_portfolio_tiers = body.addon_portfolio_tiers
    if body.sale_enabled is not None:
        pkg.sale_enabled = body.sale_enabled
    if body.sale_price is not None:
        pkg.sale_price = body.sale_price
    if body.sale_discount_percent is not None:
        pkg.sale_discount_percent = body.sale_discount_percent
    if body.sale_type is not None:
        pkg.sale_type = body.sale_type
    if body.sale_expires_at is not None:
        pkg.sale_expires_at = body.sale_expires_at
    if body.sale_badge_label is not None:
        pkg.sale_badge_label = body.sale_badge_label
    if body.is_active is not None:
        pkg.is_active = body.is_active

    # Reconcile discount calculations
    if pkg.sale_enabled:
        if body.sale_price is not None and body.sale_discount_percent is None and pkg.price > 0:
            pkg.sale_discount_percent = round(((pkg.price - pkg.sale_price) / pkg.price) * 100.0, 1)
        elif body.sale_discount_percent is not None and body.sale_price is None:
            pkg.sale_price = round(pkg.price * (1 - pkg.sale_discount_percent / 100.0), 2)

    await db.commit()
    await db.refresh(pkg)
    return {"message": "Paket yeniləndi", "package_id": pkg.id}


@router.delete("/me/packages/{package_id}")
async def delete_my_package(
    package_id: int,
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: Delete or deactivate a package."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    stmt = select(SellerPackage).where(SellerPackage.id == package_id, SellerPackage.seller_id == seller.id)
    res = await db.execute(stmt)
    if not pkg:
        raise HTTPException(status_code=404, detail="Paket tapılmadı")

    # Soft-deactivate the package to safely preserve agent subscription records and transaction histories
    pkg.is_active = False
    await db.commit()
    return {"message": "Paket uğurla deaktiv edildi"}


@router.get("/me/earnings")
async def get_my_earnings(
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: View my transactions and earnings history."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    stmt = select(SellerTransaction).where(SellerTransaction.seller_id == seller.id).order_by(SellerTransaction.created_at.desc())
    res = await db.execute(stmt)
    txs = res.scalars().all()

    return {
        "balance": seller.balance,
        "total_earnings": seller.total_earnings,
        "commission_rate": seller.commission_rate,
        "rank": seller.rank,
        "transactions": [{
            "id": t.id,
            "amount": t.amount,
            "commission_rate": t.commission_rate,
            "seller_profit": t.seller_profit,
            "platform_fee": t.platform_fee,
            "type": t.type,
            "description": t.description,
            "created_at": t.created_at.isoformat() if t.created_at else None
        } for t in txs]
    }


# ----------------- CUSTOM DOMAIN & WHITE-LABEL ENDPOINTS -----------------

class UpdateMyDomainRequest(BaseModel):
    custom_domain: Optional[str] = None
    custom_brand_title: Optional[str] = None
    custom_brand_logo: Optional[str] = None


@router.get("/me/domain")
async def get_my_domain_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: Get custom domain details and DNS setup instructions dynamically."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    from app.models.seller import SELLER_RANK_CONFIG
    rank_info = SELLER_RANK_CONFIG.get(seller.rank, SELLER_RANK_CONFIG["Bronze"])

    # 1. Check if Admin configured a custom system domain override in AppSettings
    from app.models.setting import AppSettings
    stmt_setting = select(AppSettings).where(AppSettings.key == "cname_target_domain")
    res_setting = await db.execute(stmt_setting)
    db_setting = res_setting.scalars().first()

    if db_setting and db_setting.value.strip():
        target_cname = db_setting.value.strip()
    else:
        # 2. Extract dynamically from incoming Request Host / X-Forwarded-Host
        raw_host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
        clean_req_host = raw_host.split(":")[0].strip().lower()
        
        # If API host is requested (e.g. realtor-api.erma.shop -> realtor.erma.shop)
        if clean_req_host.startswith("realtor-api."):
            clean_req_host = clean_req_host.replace("realtor-api.", "realtor.", 1)
        elif "-api." in clean_req_host:
            clean_req_host = clean_req_host.replace("-api.", ".", 1)
        elif clean_req_host.startswith("api."):
            clean_req_host = clean_req_host.replace("api.", "", 1)

        if clean_req_host and clean_req_host not in ["localhost", "127.0.0.1", "test", "testserver"]:
            target_cname = clean_req_host
        else:
            target_cname = getattr(settings, "CNAME_TARGET_DOMAIN", "realtor.erma.shop")

    # 3. Resolve actual Server IP dynamically
    import socket
    try:
        resolved_server_ip = socket.gethostbyname(target_cname)
    except Exception:
        resolved_server_ip = getattr(settings, "SERVER_IP", "185.196.21.159")

    return {
        "custom_domain": seller.custom_domain,
        "custom_domain_enabled": seller.custom_domain_enabled,
        "domain_status": seller.domain_status,
        "custom_brand_title": seller.custom_brand_title,
        "custom_brand_logo": seller.custom_brand_logo,
        "rank_allows_domain": rank_info.get("custom_domain_allowed", False) or seller.custom_domain_enabled,
        "dns_instructions": {
            "type": "CNAME",
            "host": seller.custom_domain or "emlak.brendiniz.az",
            "target": target_cname,
            "server_ip": resolved_server_ip,
            "ttl": 300
        }
    }


@router.post("/me/domain")
async def update_my_domain_settings(
    body: UpdateMyDomainRequest,
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: Save custom domain & brand details if allowed by Admin or Rank."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    from app.models.seller import SELLER_RANK_CONFIG
    rank_info = SELLER_RANK_CONFIG.get(seller.rank, SELLER_RANK_CONFIG["Bronze"])
    if not (rank_info.get("custom_domain_allowed", False) or seller.custom_domain_enabled):
        raise HTTPException(
            status_code=403,
            detail="Fərdi domen funksiyası üçün admin icazəsi və ya Gold+ səviyyəsi tələb olunur."
        )

    if body.custom_domain is not None:
        clean_domain = body.custom_domain.strip().lower().replace("https://", "").replace("http://", "").rstrip("/")
        seller.custom_domain = clean_domain if clean_domain else None
        seller.domain_status = "pending_dns" if clean_domain else "disabled"
    if body.custom_brand_title is not None:
        seller.custom_brand_title = body.custom_brand_title.strip()
    if body.custom_brand_logo is not None:
        seller.custom_brand_logo = body.custom_brand_logo.strip()

    await db.commit()
    await db.refresh(seller)
    return {"message": "Domen məlumatları yeniləndi", "domain_status": seller.domain_status}


@router.post("/me/domain/verify")
async def verify_my_domain_dns(
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: Verify DNS resolution for custom domain."""
    user, seller = current_auth
    if not seller or not seller.custom_domain:
        raise HTTPException(status_code=400, detail="Fərdi domen təyin edilməyib.")

    import socket
    domain = seller.custom_domain.strip()
    try:
        ip = socket.gethostbyname(domain)
        seller.domain_status = "active"
        seller.custom_domain_enabled = True
        await db.commit()
        return {
            "success": True,
            "domain": domain,
            "resolved_ip": ip,
            "domain_status": "active",
            "message": f"DNS uğurla təsdiqləndi ({ip}). Fərdi domen aktivdir!"
        }
    except Exception as e:
        seller.domain_status = "pending_dns"
        await db.commit()
        return {
            "success": False,
            "domain": domain,
            "domain_status": "pending_dns",
            "message": f"DNS hələ aktiv deyil və ya ünvanlanmayıb: {str(e)}"
        }


@router.get("/public-branding")
async def get_public_branding_by_domain(
    host: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Public endpoint: Resolve seller branding by hostname for white-label display."""
    if not host:
        return {"is_custom": False, "app_name": "RealEstate AI Agent", "logo_url": None}

    clean_host = host.split(":")[0].strip().lower()
    stmt = select(Seller).where(Seller.custom_domain == clean_host, Seller.domain_status == "active")
    res = await db.execute(stmt)
    seller = res.scalars().first()
    if seller:
        return {
            "is_custom": True,
            "seller_id": seller.id,
            "seller_name": seller.name,
            "app_name": seller.custom_brand_title or seller.company_name or f"{seller.name} Emlak Portalı",
            "logo_url": seller.custom_brand_logo
        }

    return {"is_custom": False, "app_name": "RealEstate AI Agent", "logo_url": None}


# ----------------- SELLER PAYOUT / WITHDRAWAL WORKFLOW -----------------

class CreateSellerPayoutRequest(BaseModel):
    amount: float
    card_number: str
    card_holder_name: str
    iban: Optional[str] = None
    notes: Optional[str] = None

class ActionPayoutRequest(BaseModel):
    action: str # "approve" | "pay" | "reject"
    admin_notes: Optional[str] = None


@router.post("/me/payouts")
async def request_seller_payout(
    body: CreateSellerPayoutRequest,
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller requests withdrawal of available balance to bank card."""
    user, current_seller = current_auth
    if not current_seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Çıxarış məbləği müsbət olmalıdır.")
    if body.amount > current_seller.balance:
        raise HTTPException(
            status_code=400,
            detail=f"Balansınızda kifayət qədər vəsait yoxdur (Mövcud balans: {current_seller.balance:.2f} AZN)."
        )

    from app.models.seller_payout import SellerPayoutRequest
    payout = SellerPayoutRequest(
        seller_id=current_seller.id,
        amount=body.amount,
        card_number=body.card_number.strip(),
        card_holder_name=body.card_holder_name.strip(),
        iban=body.iban.strip() if body.iban else None,
        notes=body.notes,
        status="pending"
    )
    db.add(payout)
    await db.commit()
    await db.refresh(payout)

    # Notify admin via Telegram
    from app.services.health_monitor import HealthMonitorService
    await HealthMonitorService.send_admin_alert(
        db,
        title="Yeni Satıcı Çıxarış Tələbi",
        message=(
            f"👤 *Satıcı:* {current_seller.name} ({current_seller.company_name or 'Fərdi'})\n"
            f"💰 *Məbləğ:* {payout.amount:.2f} AZN\n"
            f"💳 *Kart:* `{payout.card_number}` ({payout.card_holder_name})\n"
            f"📋 *Qeyd:* {payout.notes or 'Yoxdur'}"
        )
    )

    return {
        "status": "success",
        "payout_id": payout.id,
        "amount": payout.amount,
        "message": "Çıxarış tələbiniz qeydə alındı və admin tərəfindən nəzərdən keçirilir."
    }


@router.get("/me/payouts")
async def list_my_payouts(
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller views all their past and pending payout requests."""
    user, current_seller = current_auth
    if not current_seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")
    from app.models.seller_payout import SellerPayoutRequest
    stmt = select(SellerPayoutRequest).where(SellerPayoutRequest.seller_id == current_seller.id).order_by(SellerPayoutRequest.created_at.desc())
    res = await db.execute(stmt)
    payouts = res.scalars().all()

    return [
        {
            "id": p.id,
            "amount": p.amount,
            "card_number": p.card_number,
            "card_holder_name": p.card_holder_name,
            "iban": p.iban,
            "status": p.status,
            "notes": p.notes,
            "admin_notes": p.admin_notes,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "processed_at": p.processed_at.isoformat() if p.processed_at else None
        }
        for p in payouts
    ]


@router.get("/admin/payouts")
async def list_all_payouts_admin(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Admin views all seller payout requests across the platform."""
    from app.models.seller_payout import SellerPayoutRequest
    stmt = select(SellerPayoutRequest).order_by(SellerPayoutRequest.created_at.desc())
    res = await db.execute(stmt)
    payouts = res.scalars().all()

    out = []
    for p in payouts:
        s_stmt = select(Seller).where(Seller.id == p.seller_id)
        s_res = await db.execute(s_stmt)
        seller = s_res.scalars().first()

        out.append({
            "id": p.id,
            "seller_id": p.seller_id,
            "seller_name": seller.name if seller else "Naməlum",
            "seller_company": seller.company_name if seller else None,
            "seller_phone": seller.phone if seller else None,
            "seller_balance": seller.balance if seller else 0.0,
            "amount": p.amount,
            "card_number": p.card_number,
            "card_holder_name": p.card_holder_name,
            "iban": p.iban,
            "status": p.status,
            "notes": p.notes,
            "admin_notes": p.admin_notes,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "processed_at": p.processed_at.isoformat() if p.processed_at else None
        })
    return out


@router.post("/admin/payouts/{payout_id}/action")
async def action_seller_payout_admin(
    payout_id: int,
    body: ActionPayoutRequest,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Admin approves/pays or rejects a seller payout request."""
    from app.models.seller_payout import SellerPayoutRequest
    stmt = select(SellerPayoutRequest).where(SellerPayoutRequest.id == payout_id)
    res = await db.execute(stmt)
    payout = res.scalars().first()
    if not payout:
        raise HTTPException(status_code=404, detail="Çıxarış tələbi tapılmadı.")

    s_stmt = select(Seller).where(Seller.id == payout.seller_id)
    s_res = await db.execute(s_stmt)
    seller = s_res.scalars().first()
    if not seller:
        raise HTTPException(status_code=404, detail="Satıcı tapılmadı.")

    if body.action.lower() in ["approve", "pay"]:
        if payout.status == "paid":
            raise HTTPException(status_code=400, detail="Bu çıxarış artıq ödənilib.")
        if seller.balance < payout.amount:
            raise HTTPException(
                status_code=400,
                detail=f"Satıcının balansı kifayət etmir (Mövcud: {seller.balance:.2f} AZN, Tələb olunan: {payout.amount:.2f} AZN)."
            )

        seller.balance -= payout.amount
        payout.status = "paid"
        payout.admin_notes = body.admin_notes
        payout.processed_at = datetime.now(timezone.utc)

        # Record seller transaction
        tx = SellerTransaction(
            seller_id=seller.id,
            amount=-payout.amount,
            type="payout",
            description=f"Kart çıxarışı #{payout.id}: {payout.card_number} ({payout.card_holder_name})"
        )
        db.add(tx)
        await db.commit()

        return {
            "status": "success",
            "message": f"{payout.amount:.2f} AZN məbləğində çıxarış təsdiqləndi və satıcı balansından çıxıldı.",
            "new_balance": seller.balance
        }

    elif body.action.lower() == "reject":
        payout.status = "rejected"
        payout.admin_notes = body.admin_notes or "İmtina edildi"
        payout.processed_at = datetime.now(timezone.utc)
        await db.commit()

        return {
            "status": "success",
            "message": "Çıxarış tələbi imtina edildi.",
            "payout_status": "rejected"
        }
    else:
        raise HTTPException(status_code=400, detail="Yanlış əməliyyat. approve və ya reject seçin.")


# ----------------- ADMIN PARAMETERIZED SELLER ENDPOINTS -----------------

@router.put("/{seller_id}")
async def update_seller_admin(
    seller_id: int,
    body: UpdateSellerRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin-only: Update seller details, commission %, rank, domain, or status."""
    stmt = select(Seller).where(Seller.id == seller_id)
    res = await db.execute(stmt)
    seller = res.scalars().first()
    if not seller:
        raise HTTPException(status_code=404, detail="Satıcı tapılmadı")

    if body.name is not None:
        seller.name = body.name
    if body.email is not None and body.email.strip():
        clean_email = body.email.strip().lower()
        if clean_email != seller.email:
            # Check for email collision
            chk_stmt = select(User).where(User.email == clean_email, User.id != seller.user_id)
            chk_res = await db.execute(chk_stmt)
            if chk_res.scalars().first():
                raise HTTPException(status_code=400, detail="Bu email ilə artıq başqa istifadəçi mövcuddur.")
            seller.email = clean_email
    if body.phone is not None:
        seller.phone = body.phone
    if body.company_name is not None:
        seller.company_name = body.company_name
    if body.commission_rate is not None:
        seller.commission_rate = max(0.0, min(100.0, body.commission_rate))
    if body.rank is not None:
        seller.rank = body.rank
        from app.models.seller import SELLER_RANK_CONFIG
        rank_info = SELLER_RANK_CONFIG.get(body.rank, {})
        if rank_info.get("custom_domain_allowed", False):
            seller.custom_domain_enabled = True

    if body.status is not None:
        seller.status = body.status
    if body.custom_domain is not None:
        clean_d = body.custom_domain.strip().lower().replace("https://", "").replace("http://", "").rstrip("/") if body.custom_domain else None
        seller.custom_domain = clean_d
        if clean_d:
            if body.domain_status:
                seller.domain_status = body.domain_status
            elif seller.domain_status == "disabled":
                seller.domain_status = "active" if seller.custom_domain_enabled else "pending_dns"
        else:
            seller.domain_status = "disabled"
    if body.custom_domain_enabled is not None:
        seller.custom_domain_enabled = body.custom_domain_enabled
    if body.domain_status is not None:
        seller.domain_status = body.domain_status
    if body.custom_brand_title is not None:
        seller.custom_brand_title = body.custom_brand_title
    if body.custom_brand_logo is not None:
        seller.custom_brand_logo = body.custom_brand_logo

    # Update associated user
    u_stmt = select(User).where(User.id == seller.user_id)
    u_res = await db.execute(u_stmt)
    user = u_res.scalars().first()
    if user:
        if body.name is not None:
            user.name = body.name
        if body.email is not None and body.email.strip():
            user.email = body.email.strip().lower()
        if body.phone is not None:
            user.phone = body.phone
        if body.password:
            validate_strong_password(body.password)
            user.password_hash = get_password_hash(body.password)

    await db.commit()
    await db.refresh(seller)
    return {"message": "Satıcı məlumatları yeniləndi", "seller": {
        "id": seller.id,
        "name": seller.name,
        "email": seller.email,
        "commission_rate": seller.commission_rate,
        "rank": seller.rank,
        "status": seller.status,
        "custom_domain": seller.custom_domain,
        "custom_domain_enabled": seller.custom_domain_enabled,
        "domain_status": seller.domain_status
    }}


@router.delete("/{seller_id}")
async def delete_seller_admin(
    seller_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin-only: Delete a seller."""
    stmt = select(Seller).where(Seller.id == seller_id)
    res = await db.execute(stmt)
    seller = res.scalars().first()
    if not seller:
        raise HTTPException(status_code=404, detail="Satıcı tapılmadı")

    user_id = seller.user_id
    await db.delete(seller)
    
    # Also delete user account
    if user_id:
        u_stmt = select(User).where(User.id == user_id)
        u_res = await db.execute(u_stmt)
        user = u_res.scalars().first()
        if user:
            await db.delete(user)

    await db.commit()
    return {"message": "Satıcı və hesabı silindi"}


@router.get("/{seller_id}/agents")
async def get_seller_agents_admin(
    seller_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin-only: View all agents belonging to a specific seller."""
    stmt = select(Tenant).where(Tenant.seller_id == seller_id).order_by(Tenant.created_at.desc())
    res = await db.execute(stmt)
    agents = res.scalars().all()
    return [{
        "id": a.id,
        "name": a.name,
        "phone": a.phone,
        "telegram_handle": a.telegram_handle,
        "plan": a.plan,
        "status": a.status,
        "plan_expires_at": a.plan_expires_at.isoformat() if a.plan_expires_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None
    } for a in agents]


@router.post("/{seller_id}/payout")
async def process_seller_payout_admin(
    seller_id: int,
    body: PayoutRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin-only: Process a payout to a seller."""
    stmt = select(Seller).where(Seller.id == seller_id)
    res = await db.execute(stmt)
    seller = res.scalars().first()
    if not seller:
        raise HTTPException(status_code=404, detail="Satıcı tapılmadı")

    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Ödəniş məbləği müsbət olmalıdır.")
    if seller.balance < body.amount:
        raise HTTPException(status_code=400, detail=f"Kifayət qədər balans yoxdur. Mövcud balans: {seller.balance} AZN")

    seller.balance -= body.amount

    # Record payout transaction
    tx = SellerTransaction(
        seller_id=seller.id,
        tenant_id=0,
        amount=body.amount,
        commission_rate=seller.commission_rate,
        seller_profit=-body.amount,
        platform_fee=0.0,
        type="payout",
        description=body.description or f"Satıcıya ödənildi: {body.amount} AZN"
    )
    db.add(tx)
    await db.commit()
    await db.refresh(seller)
    return {"message": "Ödəniş uğurla qeydə alındı", "new_balance": seller.balance}


@router.post("/{seller_id}/settle-cash")
async def settle_seller_cash_admin(
    seller_id: int,
    body: SettleCashRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Admin-only: Record cash platform fee collection from a seller.
    When a seller collects cash from agents, they owe the platform fee share to Admin.
    Admin uses this endpoint to confirm receiving cash from the seller.
    """
    stmt = select(Seller).where(Seller.id == seller_id)
    res = await db.execute(stmt)
    seller = res.scalars().first()
    if not seller:
        raise HTTPException(status_code=404, detail="Satıcı tapılmadı")

    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Məbləğ müsbət olmalıdır.")

    seller.platform_fee_settled = (getattr(seller, 'platform_fee_settled', 0.0) or 0.0) + body.amount
    
    # Record transaction
    tx = SellerTransaction(
        seller_id=seller.id,
        amount=-body.amount,
        type="cash_settlement",
        description=f"Admin nağd təhvil aldı: {body.amount:.2f} AZN ({body.notes or 'Nağd hesablaşma'})"
    )
    db.add(tx)
    await db.commit()
    await db.refresh(seller)

    total_platform_fee = max(0.0, round((seller.total_sales_volume or 0.0) - (seller.total_earnings or 0.0), 2))
    pending_debt = max(0.0, round(total_platform_fee - seller.platform_fee_settled, 2))

    return {
        "message": "Nağd hesablaşma uğurla qeydə alındı",
        "seller_id": seller.id,
        "amount_settled": body.amount,
        "total_settled": seller.platform_fee_settled,
        "pending_platform_debt": pending_debt
    }

