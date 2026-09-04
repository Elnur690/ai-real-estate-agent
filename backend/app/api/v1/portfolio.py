from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, func, desc, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.tenant import Tenant
from app.models.seller import Seller
from app.models.listing import Listing
from app.models.portfolio import PortfolioListing, generate_share_code
from app.services.domain_service import (
    resolve_tenant_domain_info,
    resolve_tenant_base_url,
    verify_domain_dns,
    verify_domain_dns_async,
    clean_domain_string
)

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


# --- Pydantic Schemas ---

class AgentDomainUpdateRequest(BaseModel):
    custom_domain: Optional[str] = None
    custom_domain_enabled: Optional[bool] = None
    enabled: Optional[bool] = None

    @property
    def is_enabled(self) -> Optional[bool]:
        if self.custom_domain_enabled is not None:
            return self.custom_domain_enabled
        return self.enabled


class PortfolioListingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    currency: str = "AZN"
    price_usd: Optional[float] = None
    district: Optional[str] = None
    metro_station: Optional[str] = None
    address: Optional[str] = None
    rooms: Optional[int] = None
    area_sqm: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    building_type: Optional[str] = None
    property_type: Optional[str] = "apartment"
    offer_type: Optional[str] = "sale"
    photos: Optional[List[Any]] = []
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None


class PortfolioListingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    price_usd: Optional[float] = None
    district: Optional[str] = None
    metro_station: Optional[str] = None
    address: Optional[str] = None
    rooms: Optional[int] = None
    area_sqm: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    building_type: Optional[str] = None
    property_type: Optional[str] = None
    offer_type: Optional[str] = None
    photos: Optional[List[Any]] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class PortfolioListingResponse(BaseModel):
    id: int
    tenant_id: int
    listing_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    price: float
    currency: str = "AZN"
    price_usd: Optional[float] = None
    district: Optional[str] = None
    metro_station: Optional[str] = None
    address: Optional[str] = None
    rooms: Optional[int] = None
    area_sqm: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    building_type: Optional[str] = None
    property_type: Optional[str] = "apartment"
    offer_type: Optional[str] = "sale"
    photos: Optional[List[Any]] = []
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None
    share_code: str
    share_url: Optional[str] = None
    is_active: bool = True
    status: str = "active"
    created_at: datetime
    updated_at: datetime


class PortfolioOverviewResponse(BaseModel):
    items: List[PortfolioListingResponse]
    active_count: int
    portfolio_limit: int
    is_limit_reached: bool
    feature_enabled: bool
    expires_at: Optional[datetime] = None
    portfolio_slug: Optional[str] = None
    portfolio_vitrin_url: Optional[str] = None
    custom_domain_info: Optional[Dict[str, Any]] = None


class PublicPortfolioListingResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    price: float
    currency: str = "AZN"
    price_usd: Optional[float] = None
    district: Optional[str] = None
    metro_station: Optional[str] = None
    address: Optional[str] = None
    rooms: Optional[int] = None
    area_sqm: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    building_type: Optional[str] = None
    property_type: str = "apartment"
    offer_type: str = "sale"
    photos: List[Any] = []
    share_code: str
    share_url: Optional[str] = None
    agent_name: str
    agent_phone: str
    agent_whatsapp: Optional[str] = None
    agent_slug: Optional[str] = None
    agent_vitrin_url: Optional[str] = None
    whatsapp_message_url: str
    created_at: datetime


# --- Helpers ---

async def get_tenant_for_portfolio(db: AsyncSession, user: User, tenant_id_override: Optional[int] = None) -> Tenant:
    if user.role == "admin" and tenant_id_override:
        stmt = select(Tenant).where(Tenant.id == tenant_id_override)
        res = await db.execute(stmt)
        t = res.scalars().first()
        if t:
            return t

    if user.role == "admin":
        stmt = select(Tenant).order_by(Tenant.id.asc())
        res = await db.execute(stmt)
        tenant = res.scalars().first()
        if not tenant:
            raise HTTPException(status_code=404, detail="No tenant accounts found.")
        return tenant

    if not user.tenant_id:
        raise HTTPException(status_code=403, detail="User is not linked to any tenant account.")

    stmt = select(Tenant).where(Tenant.id == user.tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant account not found.")
    return tenant


async def count_active_portfolio_listings(db: AsyncSession, tenant_id: int) -> int:
    stmt = select(func.count(PortfolioListing.id)).where(
        PortfolioListing.tenant_id == tenant_id,
        PortfolioListing.is_active == True
    )
    res = await db.execute(stmt)
    return res.scalar_one() or 0


def format_listing_response(item: PortfolioListing, base_url: str = "", slug: Optional[str] = None) -> PortfolioListingResponse:
    prefix = base_url.rstrip("/") if base_url else ""
    if slug:
        share_url = f"{prefix}/v/{slug}/{item.id}"
    else:
        share_url = f"{prefix}/p/{item.share_code}"

    data = {
        "id": item.id,
        "tenant_id": item.tenant_id,
        "listing_id": item.listing_id,
        "title": item.title,
        "description": item.description,
        "price": item.price,
        "currency": item.currency or "AZN",
        "price_usd": item.price_usd,
        "district": item.district,
        "metro_station": item.metro_station,
        "address": item.address,
        "rooms": item.rooms,
        "area_sqm": item.area_sqm,
        "floor": item.floor,
        "total_floors": item.total_floors,
        "building_type": item.building_type,
        "property_type": item.property_type or "apartment",
        "offer_type": item.offer_type or "sale",
        "photos": item.photos or [],
        "contact_name": item.contact_name,
        "contact_phone": item.contact_phone,
        "notes": item.notes,
        "share_code": item.share_code,
        "share_url": share_url,
        "is_active": item.is_active,
        "status": item.status,
        "created_at": item.created_at,
        "updated_at": item.updated_at
    }
    return PortfolioListingResponse(**data)


# --- Endpoints ---

@router.get("", response_model=PortfolioOverviewResponse)
async def list_portfolio_listings(
    status_filter: Optional[str] = None,
    tenant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List authenticated agent's portfolio listings with quota and limit metrics."""
    tenant = await get_tenant_for_portfolio(db, current_user, tenant_id)

    stmt = select(PortfolioListing).where(PortfolioListing.tenant_id == tenant.id)
    if status_filter:
        stmt = stmt.where(PortfolioListing.status == status_filter)
    stmt = stmt.order_by(desc(PortfolioListing.created_at))

    res = await db.execute(stmt)
    listings = res.scalars().all()

    active_count = await count_active_portfolio_listings(db, tenant.id)
    limit = getattr(tenant, 'portfolio_limit', 25) or 25
    feature_enabled = bool(getattr(tenant, 'feature_portfolio', False))

    domain_info = await resolve_tenant_domain_info(db, tenant)
    base_url = domain_info["base_url"]
    slug = getattr(tenant, 'portfolio_slug', None) or f"agent-{tenant.id}"
    vitrin_url = f"{base_url}/v/{slug}"

    return PortfolioOverviewResponse(
        items=[format_listing_response(item, base_url=base_url, slug=slug) for item in listings],
        active_count=active_count,
        portfolio_limit=limit,
        is_limit_reached=(active_count >= limit),
        feature_enabled=feature_enabled,
        expires_at=getattr(tenant, 'portfolio_expires_at', None),
        portfolio_slug=slug,
        portfolio_vitrin_url=vitrin_url,
        custom_domain_info=domain_info
    )


@router.get("/domain")
async def get_portfolio_domain_info(
    tenant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get active domain resolution details, agent custom domain configuration, and reseller inheritance."""
    tenant = await get_tenant_for_portfolio(db, current_user, tenant_id)
    return await resolve_tenant_domain_info(db, tenant)


@router.put("/domain")
async def update_portfolio_domain(
    payload: AgentDomainUpdateRequest,
    tenant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Configure or toggle the agent's custom domain add-on."""
    tenant = await get_tenant_for_portfolio(db, current_user, tenant_id)
    if not getattr(tenant, "feature_custom_domain", False):
        price = getattr(tenant, "addon_custom_domain_price", 5.0) or 5.0
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Fərdi Domen Adı add-on aktiv deyil. Aktivləşdirmək üçün: {price} AZN / ay (Telegram botda: /al domen)."
        )

    if payload.custom_domain is not None:
        clean_domain = clean_domain_string(payload.custom_domain)
        if clean_domain:
            stmt_t = select(Tenant).where(Tenant.custom_domain == clean_domain, Tenant.id != tenant.id)
            res_t = await db.execute(stmt_t)
            if res_t.scalars().first():
                raise HTTPException(status_code=400, detail="Bu domen adı başqa bir istifadəçi tərəfindən istifadə edilir.")

            stmt_s = select(Seller).where(Seller.custom_domain == clean_domain)
            res_s = await db.execute(stmt_s)
            if res_s.scalars().first():
                raise HTTPException(status_code=400, detail="Bu domen adı reseller platformasında artıq qeydiyyatdan keçib.")

        tenant.custom_domain = clean_domain
        if not clean_domain:
            tenant.custom_domain_enabled = False
            tenant.custom_domain_status = "disabled"
        else:
            dns_res = await verify_domain_dns_async(clean_domain)
            if dns_res.get("verified") or dns_res.get("success"):
                tenant.custom_domain_status = "active"
                tenant.custom_domain_enabled = True
            else:
                tenant.custom_domain_status = "pending_dns"

    effective_enabled = payload.is_enabled
    if effective_enabled is not None and tenant.custom_domain:
        tenant.custom_domain_enabled = effective_enabled
        if not effective_enabled:
            tenant.custom_domain_status = "disabled"
        elif tenant.custom_domain_status == "disabled":
            tenant.custom_domain_status = "active"

    await db.commit()
    await db.refresh(tenant)
    return await resolve_tenant_domain_info(db, tenant)


@router.post("/domain/verify")
async def verify_portfolio_domain_dns(
    tenant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test DNS resolution for the agent's custom domain."""
    tenant = await get_tenant_for_portfolio(db, current_user, tenant_id)
    if not tenant.custom_domain:
        raise HTTPException(status_code=400, detail="Fərdi domen təyin edilməyib.")

    dns_res = await verify_domain_dns_async(tenant.custom_domain)
    is_valid = bool(dns_res.get("verified") or dns_res.get("success"))
    if is_valid:
        tenant.custom_domain_status = "active"
        tenant.custom_domain_enabled = True
        await db.commit()
        return {
            "success": True,
            "verified": True,
            "domain": tenant.custom_domain,
            "resolved_ip": dns_res.get("resolved_ip"),
            "domain_status": "active",
            "message": dns_res.get("message", "DNS uğurla təsdiqləndi.")
        }
    else:
        tenant.custom_domain_status = "pending_dns"
        await db.commit()
        return {
            "success": False,
            "verified": False,
            "domain": tenant.custom_domain,
            "domain_status": "pending_dns",
            "message": dns_res.get("error", "DNS yoxlanışı uğursuz oldu.")
        }


@router.post("/from-listing/{listing_id}", response_model=PortfolioListingResponse)
async def add_to_portfolio_from_listing(
    listing_id: int,
    tenant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    1-Click Add: Clone a received listing into the agent's private portfolio.
    Checks portfolio add-on activation and enforces portfolio listing quota/limit.
    """
    tenant = await get_tenant_for_portfolio(db, current_user, tenant_id)

    # 1. Check feature toggle
    if not getattr(tenant, "feature_portfolio", False):
        price = getattr(tenant, "addon_portfolio_price", 15.0) or 15.0
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Agent Portfeli add-on aktiv deyil. Hesabınızda portfel modulunu aktivləşdirin ({price} AZN / ay)."
        )

    # 2. Check active quota vs limit
    active_count = await count_active_portfolio_listings(db, tenant.id)
    limit = getattr(tenant, "portfolio_limit", 25) or 25
    if active_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Portfel limitiniz dolub ({active_count}/{limit} elan istifadə edilib). Zəhmət olmasa vaxtı bitmiş elanları silin və ya paketinizi artırın."
        )

    # 3. Fetch source listing
    stmt = select(Listing).where(Listing.id == listing_id)
    res = await db.execute(stmt)
    listing = res.scalars().first()
    if not listing:
        raise HTTPException(status_code=404, detail="Göstərilən elan tapılmadı.")

    # 4. Clone fields into PortfolioListing
    portfolio_item = PortfolioListing(
        tenant_id=tenant.id,
        listing_id=listing.id,
        title=listing.title,
        description=listing.description,
        price=listing.price,
        currency=listing.currency or "AZN",
        price_usd=listing.price_usd,
        district=listing.district,
        metro_station=listing.metro_station,
        address=listing.address_raw,
        rooms=listing.rooms,
        area_sqm=listing.area_sqm,
        floor=listing.floor,
        total_floors=listing.total_floors,
        building_type=listing.building_type,
        property_type=listing.property_type or "apartment",
        offer_type=listing.offer_type or "sale",
        photos=listing.photos or [],
        contact_name=tenant.name,
        contact_phone=tenant.phone,
        notes=f"Elan portaldan əlavə edildi (Mənbə ID: #{listing.id})",
        share_code=generate_share_code(),
        is_active=True,
        status="active"
    )

    db.add(portfolio_item)
    await db.commit()
    await db.refresh(portfolio_item)

    return format_listing_response(portfolio_item)


@router.post("", response_model=PortfolioListingResponse)
async def create_portfolio_listing(
    payload: PortfolioListingCreate,
    tenant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually create a new property listing inside agent's portfolio."""
    tenant = await get_tenant_for_portfolio(db, current_user, tenant_id)

    if not getattr(tenant, "feature_portfolio", False):
        price = getattr(tenant, "addon_portfolio_price", 15.0) or 15.0
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Agent Portfeli add-on aktiv deyil. Aktivləşdirmək üçün: {price} AZN / ay."
        )

    active_count = await count_active_portfolio_listings(db, tenant.id)
    limit = getattr(tenant, "portfolio_limit", 25) or 25
    if active_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Portfel limitiniz dolub ({active_count}/{limit}). Zəhmət olmasa vaxtı bitmiş elanları silin və ya paketinizi artırın."
        )

    item = PortfolioListing(
        tenant_id=tenant.id,
        title=payload.title,
        description=payload.description,
        price=payload.price,
        currency=payload.currency or "AZN",
        price_usd=payload.price_usd,
        district=payload.district,
        metro_station=payload.metro_station,
        address=payload.address,
        rooms=payload.rooms,
        area_sqm=payload.area_sqm,
        floor=payload.floor,
        total_floors=payload.total_floors,
        building_type=payload.building_type,
        property_type=payload.property_type or "apartment",
        offer_type=payload.offer_type or "sale",
        photos=payload.photos or [],
        contact_name=payload.contact_name or tenant.name,
        contact_phone=payload.contact_phone or tenant.phone,
        notes=payload.notes,
        share_code=generate_share_code(),
        is_active=True,
        status="active"
    )

    db.add(item)
    await db.commit()
    await db.refresh(item)

    return format_listing_response(item)


@router.get("/{id}", response_model=PortfolioListingResponse)
async def get_portfolio_listing(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve details of a single portfolio listing."""
    tenant = await get_tenant_for_portfolio(db, current_user)

    stmt = select(PortfolioListing).where(
        PortfolioListing.id == id,
        PortfolioListing.tenant_id == tenant.id
    )
    res = await db.execute(stmt)
    item = res.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Portfel elanı tapılmadı.")

    return format_listing_response(item)


@router.put("/{id}", response_model=PortfolioListingResponse)
async def update_portfolio_listing(
    id: int,
    payload: PortfolioListingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update details of a portfolio listing field-by-field.
    Allows agent to customize description, price, contact, photos, status, etc.
    """
    tenant = await get_tenant_for_portfolio(db, current_user)

    stmt = select(PortfolioListing).where(
        PortfolioListing.id == id,
        PortfolioListing.tenant_id == tenant.id
    )
    res = await db.execute(stmt)
    item = res.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Portfel elanı tapılmadı.")

    # If reactivating an inactive listing, check limit
    if payload.is_active is True and item.is_active is False:
        active_count = await count_active_portfolio_listings(db, tenant.id)
        limit = getattr(tenant, "portfolio_limit", 25) or 25
        if active_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Portfel limiti ({limit}) dolub. Yeni elan aktivləşdirmək üçün köhnələri silin."
            )

    update_dict = payload.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(item, field, val)

    item.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(item)

    return format_listing_response(item)


@router.delete("/{id}")
async def delete_portfolio_listing(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an expired or sold listing from portfolio.
    Instantly frees up limit slot for the agent.
    """
    tenant = await get_tenant_for_portfolio(db, current_user)

    stmt = select(PortfolioListing).where(
        PortfolioListing.id == id,
        PortfolioListing.tenant_id == tenant.id
    )
    res = await db.execute(stmt)
    item = res.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Portfel elanı tapılmadı.")

    await db.delete(item)
    await db.commit()

    new_active_count = await count_active_portfolio_listings(db, tenant.id)
    limit = getattr(tenant, "portfolio_limit", 25) or 25

    return {
        "message": "Elan portfeldən uğurla silindi və limit yuvası azad edildi.",
        "active_count": new_active_count,
        "portfolio_limit": limit,
        "remaining_slots": max(0, limit - new_active_count)
    }


# --- Public Client Sharing Endpoints (No Auth Required) ---

@router.get("/public/by-domain", response_model=List[PublicPortfolioListingResponse])
async def get_portfolio_by_domain(
    request: Request,
    domain: Optional[str] = Query(None, description="Custom domain hostname to lookup"),
    db: AsyncSession = Depends(get_db)
):
    """
    Lookup agent or reseller portfolio showcase directly by domain name.
    Used when a customer navigates to https://customdomain.az/ root URL.
    Must be defined before /public/{share_code} to prevent route capture.
    """
    target_domain = clean_domain_string(domain)
    if not target_domain:
        host_header = request.headers.get("host", "").split(":")[0]
        target_domain = clean_domain_string(host_header)

    if not target_domain:
        raise HTTPException(status_code=400, detail="Domen adı təqdim edilməyib.")

    # 1. Look for matching Agent (Tenant)
    stmt_t = select(Tenant).where(
        Tenant.custom_domain == target_domain,
        Tenant.custom_domain_enabled == True,
        Tenant.feature_custom_domain == True,
        Tenant.status != "suspended"
    )
    res_t = await db.execute(stmt_t)
    tenant = res_t.scalars().first()
    if tenant:
        return await get_agent_public_catalog(identifier=str(tenant.id), db=db)

    # 2. Look for matching Reseller (Seller)
    stmt_s = select(Seller).where(
        Seller.custom_domain == target_domain,
        Seller.custom_domain_enabled == True,
        Seller.status != "suspended"
    )
    res_s = await db.execute(stmt_s)
    seller = res_s.scalars().first()
    if seller:
        # Find all non-suspended tenants under this reseller
        stmt_tenants = select(Tenant.id).where(Tenant.seller_id == seller.id, Tenant.status != "suspended")
        res_tenants = await db.execute(stmt_tenants)
        tenant_ids = res_tenants.scalars().all()
        if not tenant_ids:
            return []

        stmt_listings = select(PortfolioListing).where(
            PortfolioListing.tenant_id.in_(tenant_ids),
            PortfolioListing.is_active == True,
            PortfolioListing.status == "active"
        ).order_by(desc(PortfolioListing.created_at))
        res_listings = await db.execute(stmt_listings)
        listings = res_listings.scalars().all()

        output = []
        base_url = f"https://{target_domain}"
        for it in listings:
            res_item_tenant = await db.execute(select(Tenant).where(Tenant.id == it.tenant_id))
            item_tenant = res_item_tenant.scalars().first()

            agent_name = it.contact_name or (item_tenant.name if item_tenant else seller.name)
            agent_phone = it.contact_phone or (item_tenant.phone if item_tenant else (seller.contact_phone or ""))
            agent_whatsapp = (item_tenant.whatsapp_number or agent_phone) if item_tenant else agent_phone
            clean_wa = "".join(filter(str.isdigit, agent_whatsapp or ""))
            wa_msg = f"Salam, {agent_name}. Sizin platformadakı bu elanla bağlı maraqlanıram: {it.title} (Kod: {it.share_code})"
            wa_url = f"https://wa.me/{clean_wa}?text={urllib.parse.quote(wa_msg)}" if clean_wa else ""
            agent_slug = (item_tenant.portfolio_slug or str(item_tenant.id)) if item_tenant else ""
            share_url = f"{base_url}/v/{agent_slug}/{it.id}" if agent_slug else f"{base_url}/p/{it.share_code}"

            output.append(PublicPortfolioListingResponse(
                id=it.id,
                title=it.title,
                description=it.description,
                price=it.price,
                currency=it.currency or "AZN",
                price_usd=it.price_usd,
                district=it.district,
                metro_station=it.metro_station,
                address=it.address,
                rooms=it.rooms,
                area_sqm=it.area_sqm,
                floor=it.floor,
                total_floors=it.total_floors,
                building_type=it.building_type,
                property_type=it.property_type or "apartment",
                offer_type=it.offer_type or "sale",
                photos=it.photos or [],
                share_code=it.share_code,
                share_url=share_url,
                agent_name=agent_name,
                agent_phone=agent_phone,
                agent_whatsapp=agent_whatsapp,
                agent_slug=agent_slug,
                agent_vitrin_url=f"{base_url}/v/{agent_slug}" if agent_slug else None,
                whatsapp_message_url=wa_url,
                created_at=it.created_at
            ))
        return output

    raise HTTPException(status_code=404, detail="Bu domenə bağlı aktiv agent və ya reseller vitrini tapılmadı.")


@router.get("/public/{share_code}", response_model=PublicPortfolioListingResponse)
async def get_public_portfolio_listing(
    share_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Public Client Presentation:
    Fetches property details via public share_code (or numeric listing ID) with agent branding and WhatsApp contact button.
    Does not expose competitors, broker portals, or internal private notes.
    """
    clean_code = share_code.strip()
    stmt = select(PortfolioListing).where(PortfolioListing.is_active == True)
    if clean_code.isdigit():
        stmt = stmt.where((PortfolioListing.id == int(clean_code)) | (PortfolioListing.share_code == clean_code))
    else:
        stmt = stmt.where(PortfolioListing.share_code == clean_code)

    res = await db.execute(stmt)
    item = res.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Elan tapılmadı və ya aktivliyi dayandırılıb.")

    # Resolve tenant contact info
    stmt_t = select(Tenant).where(Tenant.id == item.tenant_id)
    res_t = await db.execute(stmt_t)
    tenant = res_t.scalars().first()

    base_url = (await resolve_tenant_base_url(db, tenant)) if tenant else ""
    agent_name = item.contact_name or (tenant.name if tenant else "Əmlak Agentliyi")
    agent_phone = item.contact_phone or (tenant.phone if tenant else "")
    agent_whatsapp = (tenant.whatsapp_number or agent_phone) if tenant else agent_phone
    agent_slug = tenant.portfolio_slug or str(tenant.id) if tenant else None
    agent_vitrin_url = f"{base_url}/v/{agent_slug}" if agent_slug else None
    share_url = f"{base_url}/v/{agent_slug}/{item.id}" if agent_slug else f"{base_url}/p/{item.share_code}"

    clean_wa = "".join(filter(str.isdigit, agent_whatsapp or ""))
    wa_msg = f"Salam, {agent_name}. Sizin portfelinizdəki bu elanla bağlı əlaqə saxlayıram: {item.title} (Kod: {item.share_code})"
    encoded_msg = urllib.parse.quote(wa_msg)
    wa_url = f"https://wa.me/{clean_wa}?text={encoded_msg}" if clean_wa else ""

    return PublicPortfolioListingResponse(
        id=item.id,
        title=item.title,
        description=item.description,
        price=item.price,
        currency=item.currency or "AZN",
        price_usd=item.price_usd,
        district=item.district,
        metro_station=item.metro_station,
        address=item.address,
        rooms=item.rooms,
        area_sqm=item.area_sqm,
        floor=item.floor,
        total_floors=item.total_floors,
        building_type=item.building_type,
        property_type=item.property_type or "apartment",
        offer_type=item.offer_type or "sale",
        photos=item.photos or [],
        share_code=item.share_code,
        share_url=share_url,
        agent_name=agent_name,
        agent_phone=agent_phone,
        agent_whatsapp=agent_whatsapp,
        agent_slug=agent_slug,
        agent_vitrin_url=agent_vitrin_url,
        whatsapp_message_url=wa_url,
        created_at=item.created_at
    )



@router.get("/public/agent/{identifier}", response_model=List[PublicPortfolioListingResponse])
@router.get("/agent/{identifier}/public", response_model=List[PublicPortfolioListingResponse])
async def get_agent_public_catalog(
    identifier: str,
    db: AsyncSession = Depends(get_db)
):
    """Public showcase of all active properties for an agent via numeric ID or friendly slug."""
    clean_id = identifier.strip().lower()
    stmt_t = select(Tenant)
    if clean_id.isdigit():
        stmt_t = stmt_t.where(Tenant.id == int(clean_id))
    else:
        stmt_t = stmt_t.where(
            (Tenant.portfolio_slug == clean_id) |
            (Tenant.referral_code == clean_id) |
            (Tenant.name.ilike(clean_id))
        )
    res_t = await db.execute(stmt_t)
    tenant = res_t.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Agent vitrini tapılmadı və ya aktiv deyil.")

    stmt = select(PortfolioListing).where(
        PortfolioListing.tenant_id == tenant.id,
        PortfolioListing.is_active == True,
        PortfolioListing.status == "active"
    ).order_by(desc(PortfolioListing.created_at))
    res = await db.execute(stmt)
    items = res.scalars().all()

    output = []
    base_url = await resolve_tenant_base_url(db, tenant)
    clean_wa = "".join(filter(str.isdigit, tenant.whatsapp_number or tenant.phone or ""))
    agent_slug = tenant.portfolio_slug or str(tenant.id)
    vitrin_url = f"{base_url}/v/{agent_slug}"

    for it in items:
        wa_msg = f"Salam, {tenant.name}. Sizin portfelinizdəki bu elanla bağlı maraqlanıram: {it.title} (Kod: {it.share_code})"
        wa_url = f"https://wa.me/{clean_wa}?text={urllib.parse.quote(wa_msg)}" if clean_wa else ""
        share_url = f"{base_url}/v/{agent_slug}/{it.id}"

        output.append(PublicPortfolioListingResponse(
            id=it.id,
            title=it.title,
            description=it.description,
            price=it.price,
            currency=it.currency or "AZN",
            price_usd=it.price_usd,
            district=it.district,
            metro_station=it.metro_station,
            address=it.address,
            rooms=it.rooms,
            area_sqm=it.area_sqm,
            floor=it.floor,
            total_floors=it.total_floors,
            building_type=it.building_type,
            property_type=it.property_type or "apartment",
            offer_type=it.offer_type or "sale",
            photos=it.photos or [],
            share_code=it.share_code,
            share_url=share_url,
            agent_name=it.contact_name or tenant.name,
            agent_phone=it.contact_phone or tenant.phone,
            agent_whatsapp=tenant.whatsapp_number or tenant.phone,
            agent_slug=agent_slug,
            agent_vitrin_url=vitrin_url,
            whatsapp_message_url=wa_url,
            created_at=it.created_at
        ))

    return output


@router.get("/public/agent/{agent_identifier}/{listing_identifier}", response_model=PublicPortfolioListingResponse)
@router.get("/agent/{agent_identifier}/{listing_identifier}/public", response_model=PublicPortfolioListingResponse)
async def get_public_listing_by_agent_and_id(
    agent_identifier: str,
    listing_identifier: str,
    db: AsyncSession = Depends(get_db)
):
    """Lookup a single portfolio listing under an agent using friendly URL path (e.g. /v/elnur/1042)."""
    clean_agent = agent_identifier.strip().lower()
    clean_listing = listing_identifier.strip()

    stmt_t = select(Tenant)
    if clean_agent.isdigit():
        stmt_t = stmt_t.where(Tenant.id == int(clean_agent))
    else:
        stmt_t = stmt_t.where(
            (Tenant.portfolio_slug == clean_agent) |
            (Tenant.referral_code == clean_agent) |
            (Tenant.name.ilike(clean_agent))
        )
    res_t = await db.execute(stmt_t)
    tenant = res_t.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Agent vitrini tapılmadı.")

    stmt_l = select(PortfolioListing).where(
        PortfolioListing.tenant_id == tenant.id,
        PortfolioListing.is_active == True
    )
    if clean_listing.isdigit():
        stmt_l = stmt_l.where((PortfolioListing.id == int(clean_listing)) | (PortfolioListing.share_code == clean_listing))
    else:
        stmt_l = stmt_l.where(PortfolioListing.share_code == clean_listing)

    res_l = await db.execute(stmt_l)
    item = res_l.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Elan tapılmadı və ya aktivliyi dayandırılıb.")

    agent_name = item.contact_name or tenant.name
    agent_phone = item.contact_phone or tenant.phone
    agent_whatsapp = tenant.whatsapp_number or agent_phone
    clean_wa = "".join(filter(str.isdigit, agent_whatsapp or ""))
    wa_msg = f"Salam, {agent_name}. Sizin portfelinizdəki bu elanla bağlı əlaqə saxlayıram: {item.title} (Kod: {item.share_code})"
    encoded_msg = urllib.parse.quote(wa_msg)
    wa_url = f"https://wa.me/{clean_wa}?text={encoded_msg}" if clean_wa else ""

    base_url = await resolve_tenant_base_url(db, tenant)
    agent_slug = tenant.portfolio_slug or str(tenant.id)

    return PublicPortfolioListingResponse(
        id=item.id,
        title=item.title,
        description=item.description,
        price=item.price,
        currency=item.currency or "AZN",
        price_usd=item.price_usd,
        district=item.district,
        metro_station=item.metro_station,
        address=item.address,
        rooms=item.rooms,
        area_sqm=item.area_sqm,
        floor=item.floor,
        total_floors=item.total_floors,
        building_type=item.building_type,
        property_type=item.property_type or "apartment",
        offer_type=item.offer_type or "sale",
        photos=item.photos or [],
        share_code=item.share_code,
        share_url=f"{base_url}/v/{agent_slug}/{item.id}",
        agent_name=agent_name,
        agent_phone=agent_phone,
        agent_whatsapp=agent_whatsapp,
        agent_slug=agent_slug,
        agent_vitrin_url=f"{base_url}/v/{agent_slug}",
        whatsapp_message_url=wa_url,
        created_at=item.created_at
    )
