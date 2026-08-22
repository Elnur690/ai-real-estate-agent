from datetime import datetime, timezone
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, get_current_admin, get_current_seller_user
from app.models.user import User
from app.models.tenant import Tenant
from app.models.seller import Seller, SellerPackage, SellerTransaction
from app.api.v1.auth import get_password_hash

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
    max_searches: int = 5
    max_locations: int = 5
    feature_makler_detector: bool = True
    feature_avm_bargain_finder: bool = True
    feature_b2b_cobrokering: bool = False
    feature_backup_service: bool = False

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
    feature_b2b_cobrokering: Optional[bool] = None
    feature_backup_service: Optional[bool] = None
    is_active: Optional[bool] = None

class RegisterSellerAgentRequest(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    telegram_handle: Optional[str] = None
    whatsapp_number: Optional[str] = None
    preferred_channel: str = "telegram"
    package_id: Optional[int] = None

class PayoutRequest(BaseModel):
    amount: float
    description: Optional[str] = None


# ----------------- ADMIN ENDPOINTS -----------------

@router.get("", response_model=List[dict])
async def list_all_sellers_admin(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin-only: List all registered sellers with their agent counts, earnings, and domain configs."""
    from app.models.seller import SELLER_RANK_CONFIG
    stmt = select(Seller).order_by(Seller.created_at.desc())
    res = await db.execute(stmt)
    sellers = res.scalars().all()

    results = []
    for s in sellers:
        # Count agents
        agent_cnt_stmt = select(func.count(Tenant.id)).where(Tenant.seller_id == s.id)
        agent_cnt_res = await db.execute(agent_cnt_stmt)
        total_agents = agent_cnt_res.scalar() or 0

        # Count active agents
        active_cnt_stmt = select(func.count(Tenant.id)).where(Tenant.seller_id == s.id, Tenant.status == "active")
        active_cnt_res = await db.execute(active_cnt_stmt)
        active_agents = active_cnt_res.scalar() or 0

        rank_info = SELLER_RANK_CONFIG.get(s.rank, SELLER_RANK_CONFIG["Bronze"])

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
            "total_agents": total_agents,
            "active_agents": active_agents,
            "custom_domain": s.custom_domain,
            "custom_domain_enabled": s.custom_domain_enabled,
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
            max_searches=5,
            feature_makler_detector=True,
            feature_avm_bargain_finder=True
        ),
        SellerPackage(
            seller_id=seller.id,
            name="Pro Agent Paketi",
            description="Geniş axtarışlar və B2B şəbəkəsi ilə",
            price=89.0,
            period="monthly",
            duration_days=30,
            max_searches=15,
            feature_makler_detector=True,
            feature_avm_bargain_finder=True,
            feature_b2b_cobrokering=True,
            feature_backup_service=True
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
    if body.phone is not None:
        seller.phone = body.phone
    if body.company_name is not None:
        seller.company_name = body.company_name
    if body.commission_rate is not None:
        seller.commission_rate = max(0.0, min(100.0, body.commission_rate))
    if body.rank is not None:
        seller.rank = body.rank
    if body.status is not None:
        seller.status = body.status
    if body.custom_domain is not None:
        clean_d = body.custom_domain.strip().lower().replace("https://", "").replace("http://", "").rstrip("/") if body.custom_domain else None
        seller.custom_domain = clean_d
        if clean_d:
            seller.domain_status = "pending_dns" if seller.domain_status == "disabled" else seller.domain_status
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
        if body.phone is not None:
            user.phone = body.phone
        if body.password:
            user.password_hash = get_password_hash(body.password)

    await db.commit()
    await db.refresh(seller)
    return {"message": "Satıcı məlumatları yeniləndi", "seller": {
        "id": seller.id,
        "name": seller.name,
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

    from app.models.seller import SELLER_RANK_CONFIG
    rank_info = SELLER_RANK_CONFIG.get(seller.rank, SELLER_RANK_CONFIG["Bronze"])
    bonus_commission = rank_info.get("bonus_commission", 0.0)
    effective_commission_rate = min(100.0, seller.commission_rate + bonus_commission)

    min_price, max_trial_days = await _get_seller_package_constraints(db)

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
        "total_agents": total_agents,
        "active_agents": active_agents,
        "total_packages": total_packages,
        "min_package_price": min_price,
        "max_trial_days": max_trial_days,
        "custom_domain": seller.custom_domain,
        "custom_domain_enabled": seller.custom_domain_enabled,
        "domain_status": seller.domain_status,
        "custom_brand_title": seller.custom_brand_title,
        "custom_brand_logo": seller.custom_brand_logo
    }


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

    results = []
    for a in agents:
        # Load package info
        pkg_name = None
        if a.seller_package_id:
            p_stmt = select(SellerPackage).where(SellerPackage.id == a.seller_package_id)
            p_res = await db.execute(p_stmt)
            pkg = p_res.scalars().first()
            if pkg:
                pkg_name = pkg.name

        results.append({
            "id": a.id,
            "name": a.name,
            "phone": a.phone,
            "telegram_handle": a.telegram_handle,
            "whatsapp_number": a.whatsapp_number,
            "preferred_channel": a.preferred_channel,
            "plan": pkg_name or a.plan,
            "status": a.status,
            "plan_expires_at": a.plan_expires_at.isoformat() if a.plan_expires_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None
        })
    return results


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

    # 2. Check Package if assigned
    package = None
    if body.package_id:
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
    expires_at = now_utc + timedelta(days=package.duration_days if package else 30)

    agent = Tenant(
        name=body.name,
        phone=formatted_phone,
        telegram_handle=body.telegram_handle.strip().lstrip('@') if body.telegram_handle else None,
        whatsapp_number=body.whatsapp_number or formatted_phone,
        preferred_channel=body.preferred_channel,
        seller_id=seller.id,
        seller_package_id=package.id if package else None,
        plan=package.name if package else "starter",
        status="active",
        plan_started_at=now_utc,
        plan_expires_at=expires_at,
        feature_makler_detector=package.feature_makler_detector if package else True,
        feature_avm_bargain_finder=package.feature_avm_bargain_finder if package else True,
        feature_b2b_cobrokering=package.feature_b2b_cobrokering if package else False,
        backup_enabled=package.feature_backup_service if package else False
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    # 4. Calculate Commission & Financials if package has price
    if package and package.price > 0:
        from app.models.seller import SELLER_RANK_CONFIG
        rank_info = SELLER_RANK_CONFIG.get(seller.rank, SELLER_RANK_CONFIG["Bronze"])
        bonus_pct = rank_info.get("bonus_commission", 0.0)
        effective_commission_pct = min(100.0, seller.commission_rate + bonus_pct)

        gross_amount = package.price
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
            package_id=package.id,
            amount=gross_amount,
            commission_rate=effective_commission_pct,
            seller_profit=seller_profit,
            platform_fee=platform_fee,
            type="subscription_sale",
            description=f"Agent abunəsi: {agent.name} ({package.name}) [Bonus: +{bonus_pct}%]"
        )
        db.add(tx)
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
        "feature_b2b_cobrokering": p.feature_b2b_cobrokering,
        "feature_backup_service": p.feature_backup_service,
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
    """Seller-only: Create a new custom package with admin minimum price and trial duration constraints."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    min_price, max_trial_days = await _get_seller_package_constraints(db)

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

    if body.price < 0:
        raise HTTPException(status_code=400, detail="Qiymət mənfi ola bilməz.")

    if body.price == 0:
        # Free Trial Package: duration cannot exceed max_trial_days
        if body.duration_days > max_trial_days:
            raise HTTPException(
                status_code=400,
                detail=f"Pulsuz sınaq paketinin müddəti maksimum {max_trial_days} gün ola bilər."
            )
    else:
        # Paid Package: price cannot be less than min_price
        if body.price < min_price:
            raise HTTPException(
                status_code=400,
                detail=f"Ödənişli paket qiyməti minimum {min_price} AZN olmalıdır."
            )

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
        feature_b2b_cobrokering=body.feature_b2b_cobrokering,
        feature_backup_service=body.feature_backup_service,
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

    min_price, max_trial_days = await _get_seller_package_constraints(db)

    target_price = body.price if body.price is not None else pkg.price
    target_duration = body.duration_days if body.duration_days is not None else pkg.duration_days

    if target_price < 0:
        raise HTTPException(status_code=400, detail="Qiymət mənfi ola bilməz.")

    if target_price == 0:
        if target_duration > max_trial_days:
            raise HTTPException(
                status_code=400,
                detail=f"Pulsuz sınaq paketinin müddəti maksimum {max_trial_days} gün ola bilər."
            )
    else:
        if target_price < min_price:
            raise HTTPException(
                status_code=400,
                detail=f"Ödənişli paket qiyməti minimum {min_price} AZN olmalıdır."
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
    if body.feature_b2b_cobrokering is not None:
        pkg.feature_b2b_cobrokering = body.feature_b2b_cobrokering
    if body.feature_backup_service is not None:
        pkg.feature_backup_service = body.feature_backup_service
    if body.is_active is not None:
        pkg.is_active = body.is_active

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
    pkg = res.scalars().first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Paket tapılmadı")

    await db.delete(pkg)
    await db.commit()
    return {"message": "Paket silindi"}


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
    db: AsyncSession = Depends(get_db),
    current_auth: tuple[User, Optional[Seller]] = Depends(get_current_seller_user)
):
    """Seller-only: Get custom domain details and DNS setup instructions."""
    user, seller = current_auth
    if not seller:
        raise HTTPException(status_code=403, detail="Satıcı profili tələb olunur.")

    from app.models.seller import SELLER_RANK_CONFIG
    rank_info = SELLER_RANK_CONFIG.get(seller.rank, SELLER_RANK_CONFIG["Bronze"])

    return {
        "custom_domain": seller.custom_domain,
        "custom_domain_enabled": seller.custom_domain_enabled,
        "domain_status": seller.domain_status,
        "custom_brand_title": seller.custom_brand_title,
        "custom_brand_logo": seller.custom_brand_logo,
        "rank_allows_domain": rank_info.get("custom_domain_allowed", False) or seller.custom_domain_enabled,
        "dns_instructions": {
            "type": "CNAME",
            "host": seller.custom_domain or "subdomain.yourbrand.az",
            "target": "cname.realestateai.az",
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
