from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.tenant import Tenant
from app.models.listing import Listing
from app.models.crm import CrmClient, CrmDeal, CrmActivity, CrmReminder
from app.services.reminder_service import CrmReminderService

router = APIRouter(prefix="/crm", tags=["CRM"])


# --- Pydantic Schemas ---

class CrmClientCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    telegram_handle: Optional[str] = None
    client_type: str = "buyer" # buyer | renter | seller | landlord
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    rooms_min: Optional[int] = None
    rooms_max: Optional[int] = None
    districts: Optional[List[str]] = []
    notes: Optional[str] = None


class CrmClientUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    telegram_handle: Optional[str] = None
    client_type: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    rooms_min: Optional[int] = None
    rooms_max: Optional[int] = None
    districts: Optional[List[str]] = None
    notes: Optional[str] = None


class CrmClientResponse(BaseModel):
    id: int
    tenant_id: int
    name: str
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    telegram_handle: Optional[str] = None
    client_type: str
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    rooms_min: Optional[int] = None
    rooms_max: Optional[int] = None
    districts: Optional[List[str]] = []
    notes: Optional[str] = None
    deals_count: int = 0
    created_at: datetime
    updated_at: datetime


class CrmDealCreate(BaseModel):
    listing_id: Optional[int] = None
    listing_title: str
    listing_price: float = 0.0
    listing_currency: str = "AZN"
    listing_url: Optional[str] = None
    listing_image: Optional[str] = None
    listing_location: Optional[str] = None
    client_id: Optional[int] = None
    stage: str = "new" # new | offered | viewing | negotiation | closed | lost
    custom_offer_price: Optional[float] = None
    commission_amount: Optional[float] = None
    commission_percent: Optional[float] = None
    private_notes: Optional[str] = None
    scheduled_viewing_at: Optional[datetime] = None


class CrmDealUpdate(BaseModel):
    client_id: Optional[int] = None
    stage: Optional[str] = None
    custom_offer_price: Optional[float] = None
    commission_amount: Optional[float] = None
    commission_percent: Optional[float] = None
    private_notes: Optional[str] = None
    scheduled_viewing_at: Optional[datetime] = None
    is_archived: Optional[bool] = None


class CrmActivityResponse(BaseModel):
    id: int
    deal_id: Optional[int] = None
    action_type: str
    description: str
    created_at: datetime


class CrmDealResponse(BaseModel):
    id: int
    tenant_id: int
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    listing_id: Optional[int] = None
    listing_title: str
    listing_price: float
    listing_currency: str
    listing_url: Optional[str] = None
    listing_image: Optional[str] = None
    listing_location: Optional[str] = None
    stage: str
    custom_offer_price: Optional[float] = None
    commission_amount: Optional[float] = None
    commission_percent: Optional[float] = None
    private_notes: Optional[str] = None
    scheduled_viewing_at: Optional[datetime] = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    activities: List[CrmActivityResponse] = []


class CrmStatsResponse(BaseModel):
    total_deals: int
    stage_counts: Dict[str, int]
    total_clients: int
    total_won_commission: float


class CrmReminderCreate(BaseModel):
    title: str
    reminder_type: Optional[str] = "viewing" # viewing | call | follow_up | notary | other
    notes: Optional[str] = None
    due_at: datetime
    remind_before_minutes: Optional[int] = 60
    client_id: Optional[int] = None
    deal_id: Optional[int] = None


class CrmReminderUpdate(BaseModel):
    title: Optional[str] = None
    reminder_type: Optional[str] = None
    notes: Optional[str] = None
    due_at: Optional[datetime] = None
    remind_before_minutes: Optional[int] = None
    status: Optional[str] = None # pending | notified | completed | cancelled
    client_id: Optional[int] = None
    deal_id: Optional[int] = None


class CrmReminderResponse(BaseModel):
    id: int
    tenant_id: int
    client_id: Optional[int] = None
    deal_id: Optional[int] = None
    title: str
    reminder_type: str
    notes: Optional[str] = None
    due_at: datetime
    due_at_formatted: Optional[str] = None
    remind_before_minutes: int
    status: str
    notified_at: Optional[datetime] = None
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    deal_title: Optional[str] = None
    deal_price: Optional[float] = None
    created_at: datetime
    updated_at: datetime


# --- Helper to resolve tenant for request ---

async def get_tenant_for_user(db: AsyncSession, user: User) -> Tenant:
    if user.role == "admin":
        # Admin can view first tenant or manage system CRM
        stmt = select(Tenant).order_by(Tenant.id.asc())
        res = await db.execute(stmt)
        tenant = res.scalars().first()
        if not tenant:
            raise HTTPException(status_code=404, detail="No tenant available.")
        return tenant
    
    if not user.tenant_id:
        raise HTTPException(status_code=403, detail="User is not linked to any tenant account.")
    
    stmt = select(Tenant).where(Tenant.id == user.tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant account not found.")
    return tenant


# --- CRM Client Endpoints ---

@router.get("/clients", response_model=List[CrmClientResponse])
async def list_crm_clients(
    search: Optional[str] = None,
    client_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant = await get_tenant_for_user(db, current_user)
    stmt = select(CrmClient).where(CrmClient.tenant_id == tenant.id)
    
    if client_type:
        stmt = stmt.where(CrmClient.client_type == client_type)
    if search:
        s = f"%{search.strip()}%"
        stmt = stmt.where((CrmClient.name.ilike(s)) | (CrmClient.phone.ilike(s)))
    
    stmt = stmt.order_by(desc(CrmClient.updated_at))
    res = await db.execute(stmt)
    clients = res.scalars().all()

    # Bulk fetch deal counts per client
    client_ids = [c.id for c in clients]
    deal_counts = {}
    if client_ids:
        stmt_counts = (
            select(CrmDeal.client_id, func.count(CrmDeal.id))
            .where(CrmDeal.client_id.in_(client_ids), CrmDeal.is_archived == False)
            .group_by(CrmDeal.client_id)
        )
        res_counts = await db.execute(stmt_counts)
        deal_counts = dict(res_counts.all())

    result = [
        CrmClientResponse(
            id=c.id,
            tenant_id=c.tenant_id,
            name=c.name,
            phone=c.phone,
            whatsapp_number=c.whatsapp_number,
            telegram_handle=c.telegram_handle,
            client_type=c.client_type,
            budget_min=c.budget_min,
            budget_max=c.budget_max,
            rooms_min=c.rooms_min,
            rooms_max=c.rooms_max,
            districts=c.districts or [],
            notes=c.notes,
            deals_count=deal_counts.get(c.id, 0),
            created_at=c.created_at,
            updated_at=c.updated_at
        ) for c in clients
    ]
    return result


@router.post("/clients", response_model=CrmClientResponse)
async def create_crm_client(
    body: CrmClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant = await get_tenant_for_user(db, current_user)
    client = CrmClient(
        tenant_id=tenant.id,
        name=body.name.strip(),
        phone=body.phone.strip() if body.phone else None,
        whatsapp_number=body.whatsapp_number.strip() if body.whatsapp_number else None,
        telegram_handle=body.telegram_handle.strip().lstrip("@") if body.telegram_handle else None,
        client_type=body.client_type,
        budget_min=body.budget_min,
        budget_max=body.budget_max,
        rooms_min=body.rooms_min,
        rooms_max=body.rooms_max,
        districts=body.districts or [],
        notes=body.notes
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    
    return CrmClientResponse(
        id=client.id,
        tenant_id=client.tenant_id,
        name=client.name,
        phone=client.phone,
        whatsapp_number=client.whatsapp_number,
        telegram_handle=client.telegram_handle,
        client_type=client.client_type,
        budget_min=client.budget_min,
        budget_max=client.budget_max,
        rooms_min=client.rooms_min,
        rooms_max=client.rooms_max,
        districts=client.districts or [],
        notes=client.notes,
        deals_count=0,
        created_at=client.created_at,
        updated_at=client.updated_at
    )


@router.patch("/clients/{client_id}", response_model=CrmClientResponse)
async def update_crm_client(
    client_id: int,
    body: CrmClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant = await get_tenant_for_user(db, current_user)
    stmt = select(CrmClient).where(CrmClient.id == client_id, CrmClient.tenant_id == tenant.id)
    res = await db.execute(stmt)
    client = res.scalars().first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")

    if body.name is not None: client.name = body.name.strip()
    if body.phone is not None: client.phone = body.phone.strip() if body.phone else None
    if body.whatsapp_number is not None: client.whatsapp_number = body.whatsapp_number.strip() if body.whatsapp_number else None
    if body.telegram_handle is not None: client.telegram_handle = body.telegram_handle.strip().lstrip("@") if body.telegram_handle else None
    if body.client_type is not None: client.client_type = body.client_type
    if body.budget_min is not None: client.budget_min = body.budget_min
    if body.budget_max is not None: client.budget_max = body.budget_max
    if body.rooms_min is not None: client.rooms_min = body.rooms_min
    if body.rooms_max is not None: client.rooms_max = body.rooms_max
    if body.districts is not None: client.districts = body.districts
    if body.notes is not None: client.notes = body.notes

    await db.commit()
    await db.refresh(client)

    stmt_count = select(func.count(CrmDeal.id)).where(CrmDeal.client_id == client.id, CrmDeal.is_archived == False)
    res_count = await db.execute(stmt_count)
    d_count = res_count.scalar() or 0

    return CrmClientResponse(
        id=client.id,
        tenant_id=client.tenant_id,
        name=client.name,
        phone=client.phone,
        whatsapp_number=client.whatsapp_number,
        telegram_handle=client.telegram_handle,
        client_type=client.client_type,
        budget_min=client.budget_min,
        budget_max=client.budget_max,
        rooms_min=client.rooms_min,
        rooms_max=client.rooms_max,
        districts=client.districts or [],
        notes=client.notes,
        deals_count=d_count,
        created_at=client.created_at,
        updated_at=client.updated_at
    )


@router.delete("/clients/{client_id}")
async def delete_crm_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant = await get_tenant_for_user(db, current_user)
    stmt = select(CrmClient).where(CrmClient.id == client_id, CrmClient.tenant_id == tenant.id)
    res = await db.execute(stmt)
    client = res.scalars().first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")
    await db.execute(update(CrmDeal).where(CrmDeal.client_id == client.id).values(client_id=None))
    await db.delete(client)
    await db.commit()
    return {"message": "Client deleted successfully.", "client_id": client_id}


# --- CRM Deals Endpoints ---

@router.get("/deals", response_model=List[CrmDealResponse])
async def list_crm_deals(
    stage: Optional[str] = None,
    client_id: Optional[int] = None,
    include_archived: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant = await get_tenant_for_user(db, current_user)
    stmt = select(CrmDeal).where(CrmDeal.tenant_id == tenant.id)
    if not include_archived:
        stmt = stmt.where(CrmDeal.is_archived == False)
    if stage:
        stmt = stmt.where(CrmDeal.stage == stage)
    if client_id:
        stmt = stmt.where(CrmDeal.client_id == client_id)

    stmt = stmt.order_by(desc(CrmDeal.updated_at))
    res = await db.execute(stmt)
    deals = res.scalars().all()

    # Bulk fetch referenced clients
    client_ids = {d.client_id for d in deals if d.client_id}
    clients_map = {}
    if client_ids:
        stmt_c = select(CrmClient).where(CrmClient.id.in_(client_ids))
        res_c = await db.execute(stmt_c)
        clients_map = {c.id: c for c in res_c.scalars().all()}

    # Bulk fetch recent activities
    deal_ids = [d.id for d in deals]
    activities_map = {d_id: [] for d_id in deal_ids}
    if deal_ids:
        stmt_act = select(CrmActivity).where(CrmActivity.deal_id.in_(deal_ids)).order_by(desc(CrmActivity.created_at))
        res_act = await db.execute(stmt_act)
        for a in res_act.scalars().all():
            if len(activities_map.get(a.deal_id, [])) < 5:
                activities_map[a.deal_id].append(CrmActivityResponse(
                    id=a.id,
                    deal_id=a.deal_id,
                    action_type=a.action_type,
                    description=a.description,
                    created_at=a.created_at
                ))

    result = []
    for d in deals:
        c = clients_map.get(d.client_id) if d.client_id else None
        client_name = c.name if c else None
        client_phone = (c.phone or c.whatsapp_number) if c else None

        result.append(CrmDealResponse(
            id=d.id,
            tenant_id=d.tenant_id,
            client_id=d.client_id,
            client_name=client_name,
            client_phone=client_phone,
            listing_id=d.listing_id,
            listing_title=d.listing_title,
            listing_price=d.listing_price,
            listing_currency=d.listing_currency,
            listing_url=d.listing_url,
            listing_image=d.listing_image,
            listing_location=d.listing_location,
            stage=d.stage,
            custom_offer_price=d.custom_offer_price,
            commission_amount=d.commission_amount,
            commission_percent=d.commission_percent,
            private_notes=d.private_notes,
            scheduled_viewing_at=d.scheduled_viewing_at,
            is_archived=d.is_archived,
            created_at=d.created_at,
            updated_at=d.updated_at,
            activities=activities_map.get(d.id, [])
        ))
    return result


@router.post("/deals", response_model=CrmDealResponse)
async def create_crm_deal(
    body: CrmDealCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant = await get_tenant_for_user(db, current_user)
    
    # If listing_id provided, fetch any extra info if missing
    image = body.listing_image
    url = body.listing_url
    loc = body.listing_location
    if body.listing_id and (not image or not loc):
        stmt_l = select(Listing).where(Listing.id == body.listing_id)
        res_l = await db.execute(stmt_l)
        l = res_l.scalars().first()
        if l:
            image = image or (l.images[0] if l.images else None)
            url = url or l.listing_url
            loc = loc or l.district or l.metro_station

    deal = CrmDeal(
        tenant_id=tenant.id,
        client_id=body.client_id,
        listing_id=body.listing_id,
        listing_title=body.listing_title,
        listing_price=body.listing_price,
        listing_currency=body.listing_currency,
        listing_url=url,
        listing_image=image,
        listing_location=loc,
        stage=body.stage,
        custom_offer_price=body.custom_offer_price,
        commission_amount=body.commission_amount,
        commission_percent=body.commission_percent,
        private_notes=body.private_notes,
        scheduled_viewing_at=body.scheduled_viewing_at
    )
    db.add(deal)
    await db.commit()
    await db.refresh(deal)

    # Add initial activity log
    act = CrmActivity(
        tenant_id=tenant.id,
        deal_id=deal.id,
        action_type="deal_created",
        description=f"Elan CRM-ə əlavə edildi ({deal.listing_title})"
    )
    db.add(act)
    await db.commit()

    c_name = None
    c_phone = None
    if deal.client_id:
        stmt_c = select(CrmClient).where(CrmClient.id == deal.client_id)
        res_c = await db.execute(stmt_c)
        c_obj = res_c.scalars().first()
        if c_obj:
            c_name = c_obj.name
            c_phone = c_obj.phone or c_obj.whatsapp_number

    return CrmDealResponse(
        id=deal.id,
        tenant_id=deal.tenant_id,
        client_id=deal.client_id,
        client_name=c_name,
        client_phone=c_phone,
        listing_id=deal.listing_id,
        listing_title=deal.listing_title,
        listing_price=deal.listing_price,
        listing_currency=deal.listing_currency,
        listing_url=deal.listing_url,
        listing_image=deal.listing_image,
        listing_location=deal.listing_location,
        stage=deal.stage,
        custom_offer_price=deal.custom_offer_price,
        commission_amount=deal.commission_amount,
        commission_percent=deal.commission_percent,
        private_notes=deal.private_notes,
        scheduled_viewing_at=deal.scheduled_viewing_at,
        is_archived=deal.is_archived,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
        activities=[
            CrmActivityResponse(
                id=act.id,
                deal_id=act.deal_id,
                action_type=act.action_type,
                description=act.description,
                created_at=act.created_at
            )
        ]
    )


@router.patch("/deals/{deal_id}", response_model=CrmDealResponse)
async def update_crm_deal(
    deal_id: int,
    body: CrmDealUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant = await get_tenant_for_user(db, current_user)
    stmt = select(CrmDeal).where(CrmDeal.id == deal_id, CrmDeal.tenant_id == tenant.id)
    res = await db.execute(stmt)
    deal = res.scalars().first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found.")

    # Track stage changes for activity logging
    old_stage = deal.stage
    if body.stage is not None and body.stage != old_stage:
        deal.stage = body.stage
        act = CrmActivity(
            tenant_id=tenant.id,
            deal_id=deal.id,
            action_type="stage_changed",
            description=f"Status dəyişdirildi: {old_stage} ➔ {body.stage}"
        )
        db.add(act)

    if body.client_id is not None:
        deal.client_id = body.client_id
    if body.custom_offer_price is not None:
        deal.custom_offer_price = body.custom_offer_price
    if body.commission_amount is not None:
        deal.commission_amount = body.commission_amount
    if body.commission_percent is not None:
        deal.commission_percent = body.commission_percent
    if body.private_notes is not None:
        deal.private_notes = body.private_notes
    if body.scheduled_viewing_at is not None:
        deal.scheduled_viewing_at = body.scheduled_viewing_at
        act = CrmActivity(
            tenant_id=tenant.id,
            deal_id=deal.id,
            action_type="viewing_scheduled",
            description=f"Baxış təyin edildi: {body.scheduled_viewing_at.strftime('%d.%m.%Y %H:%M')}"
        )
        db.add(act)
    if body.is_archived is not None:
        deal.is_archived = body.is_archived

    await db.commit()
    await db.refresh(deal)

    client_name = None
    client_phone = None
    if deal.client_id:
        stmt_c = select(CrmClient).where(CrmClient.id == deal.client_id)
        res_c = await db.execute(stmt_c)
        c = res_c.scalars().first()
        if c:
            client_name = c.name
            client_phone = c.phone or c.whatsapp_number

    stmt_act = select(CrmActivity).where(CrmActivity.deal_id == deal.id).order_by(desc(CrmActivity.created_at)).limit(10)
    res_act = await db.execute(stmt_act)
    acts = res_act.scalars().all()

    return CrmDealResponse(
        id=deal.id,
        tenant_id=deal.tenant_id,
        client_id=deal.client_id,
        client_name=client_name,
        client_phone=client_phone,
        listing_id=deal.listing_id,
        listing_title=deal.listing_title,
        listing_price=deal.listing_price,
        listing_currency=deal.listing_currency,
        listing_url=deal.listing_url,
        listing_image=deal.listing_image,
        listing_location=deal.listing_location,
        stage=deal.stage,
        custom_offer_price=deal.custom_offer_price,
        commission_amount=deal.commission_amount,
        commission_percent=deal.commission_percent,
        private_notes=deal.private_notes,
        scheduled_viewing_at=deal.scheduled_viewing_at,
        is_archived=deal.is_archived,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
        activities=[
            CrmActivityResponse(
                id=a.id,
                deal_id=a.deal_id,
                action_type=a.action_type,
                description=a.description,
                created_at=a.created_at
            ) for a in acts
        ]
    )


@router.delete("/deals/{deal_id}")
async def delete_crm_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant = await get_tenant_for_user(db, current_user)
    stmt = select(CrmDeal).where(CrmDeal.id == deal_id, CrmDeal.tenant_id == tenant.id)
    res = await db.execute(stmt)
    deal = res.scalars().first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found.")
    await db.execute(delete(CrmActivity).where(CrmActivity.deal_id == deal.id))
    await db.delete(deal)
    await db.commit()
    return {"message": "Deal deleted successfully.", "deal_id": deal_id}


# --- CRM Stats Overview ---

@router.get("/stats", response_model=CrmStatsResponse)
async def get_crm_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tenant = await get_tenant_for_user(db, current_user)
    
    stages = ["new", "offered", "viewing", "negotiation", "closed", "lost"]
    stage_counts = {s: 0 for s in stages}
    
    stmt = select(CrmDeal.stage, func.count(CrmDeal.id)).where(
        CrmDeal.tenant_id == tenant.id,
        CrmDeal.is_archived == False
    ).group_by(CrmDeal.stage)
    res = await db.execute(stmt)
    for row in res.all():
        stg, count = row[0], row[1]
        if stg in stage_counts:
            stage_counts[stg] = count

    # Total clients
    stmt_clients = select(func.count(CrmClient.id)).where(CrmClient.tenant_id == tenant.id)
    res_clients = await db.execute(stmt_clients)
    total_clients = res_clients.scalar() or 0

    # Total won commission
    stmt_comm = select(func.sum(CrmDeal.commission_amount)).where(
        CrmDeal.tenant_id == tenant.id,
        CrmDeal.stage == "closed"
    )
    res_comm = await db.execute(stmt_comm)
    total_won_comm = res_comm.scalar() or 0.0

    total_deals = sum(stage_counts.values())

    return CrmStatsResponse(
        total_deals=total_deals,
        stage_counts=stage_counts,
        total_clients=total_clients,
        total_won_commission=float(total_won_comm)
    )


# --- CRM Task & Viewing Reminders Endpoints (Baxış Xatırladıcısı) ---

async def format_reminder_response(db: AsyncSession, reminder: CrmReminder) -> CrmReminderResponse:
    client_name = None
    client_phone = None
    if reminder.client_id:
        c_res = await db.execute(select(CrmClient).where(CrmClient.id == reminder.client_id))
        client = c_res.scalars().first()
        if client:
            client_name = client.name
            client_phone = client.phone or client.whatsapp_number

    deal_title = None
    deal_price = None
    if reminder.deal_id:
        d_res = await db.execute(select(CrmDeal).where(CrmDeal.id == reminder.deal_id))
        deal = d_res.scalars().first()
        if deal:
            deal_title = deal.listing_title
            deal_price = deal.listing_price

    due_at = reminder.due_at
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)

    return CrmReminderResponse(
        id=reminder.id,
        tenant_id=reminder.tenant_id,
        client_id=reminder.client_id,
        deal_id=reminder.deal_id,
        title=reminder.title,
        reminder_type=reminder.reminder_type,
        notes=reminder.notes,
        due_at=due_at,
        due_at_formatted=CrmReminderService.format_azt_datetime(due_at),
        remind_before_minutes=reminder.remind_before_minutes,
        status=reminder.status,
        notified_at=reminder.notified_at,
        client_name=client_name,
        client_phone=client_phone,
        deal_title=deal_title,
        deal_price=deal_price,
        created_at=reminder.created_at,
        updated_at=reminder.updated_at
    )


@router.get("/reminders", response_model=List[CrmReminderResponse])
async def list_crm_reminders(
    status_filter: Optional[str] = Query(None, alias="status"),
    client_id: Optional[int] = None,
    deal_id: Optional[int] = None,
    upcoming_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all scheduled tasks and property viewing reminders for the authenticated agent."""
    tenant = await get_tenant_for_user(db, current_user)

    stmt = select(CrmReminder).where(CrmReminder.tenant_id == tenant.id)

    if status_filter:
        stmt = stmt.where(CrmReminder.status == status_filter)

    if client_id:
        stmt = stmt.where(CrmReminder.client_id == client_id)

    if deal_id:
        stmt = stmt.where(CrmReminder.deal_id == deal_id)

    if upcoming_only:
        now_utc = datetime.now(timezone.utc)
        stmt = stmt.where(
            CrmReminder.status.in_(["pending", "notified"]),
            CrmReminder.due_at >= (now_utc - timedelta(hours=1))
        )

    stmt = stmt.order_by(CrmReminder.due_at.asc())
    res = await db.execute(stmt)
    reminders = res.scalars().all()

    output = []
    for r in reminders:
        output.append(await format_reminder_response(db, r))
    return output


@router.post("/reminders", response_model=CrmReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_crm_reminder(
    payload: CrmReminderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Schedule a new viewing or follow-up reminder for a client or deal."""
    tenant = await get_tenant_for_user(db, current_user)

    due_dt = payload.due_at
    if due_dt.tzinfo is None:
        due_dt = due_dt.replace(tzinfo=timezone.utc)

    # Validate client belonging to tenant
    if payload.client_id:
        stmt_c = select(CrmClient).where(CrmClient.id == payload.client_id, CrmClient.tenant_id == tenant.id)
        res_c = await db.execute(stmt_c)
        if not res_c.scalars().first():
            raise HTTPException(status_code=404, detail="Müştəri tapılmadı.")

    # Validate deal belonging to tenant
    deal = None
    if payload.deal_id:
        stmt_d = select(CrmDeal).where(CrmDeal.id == payload.deal_id, CrmDeal.tenant_id == tenant.id)
        res_d = await db.execute(stmt_d)
        deal = res_d.scalars().first()
        if not deal:
            raise HTTPException(status_code=404, detail="Sövdə tapılmadı.")
        # If deal has no scheduled viewing, update deal.scheduled_viewing_at as well
        deal.scheduled_viewing_at = due_dt

    reminder = CrmReminder(
        tenant_id=tenant.id,
        client_id=payload.client_id,
        deal_id=payload.deal_id,
        title=payload.title.strip(),
        reminder_type=payload.reminder_type or "viewing",
        notes=payload.notes,
        due_at=due_dt,
        remind_before_minutes=payload.remind_before_minutes or 60,
        status="pending"
    )
    db.add(reminder)

    # Log activity on deal if present
    if deal:
        activity = CrmActivity(
            tenant_id=tenant.id,
            deal_id=deal.id,
            action_type="viewing_scheduled",
            description=f"📅 Xatırlatma təyin edildi: {reminder.title} ({CrmReminderService.format_azt_datetime(due_dt)})"
        )
        db.add(activity)

    await db.commit()
    await db.refresh(reminder)
    return await format_reminder_response(db, reminder)


@router.put("/reminders/{reminder_id}", response_model=CrmReminderResponse)
async def update_crm_reminder(
    reminder_id: int,
    payload: CrmReminderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update reminder details, reschedule appointment time, or mark completed/cancelled."""
    tenant = await get_tenant_for_user(db, current_user)

    stmt = select(CrmReminder).where(CrmReminder.id == reminder_id, CrmReminder.tenant_id == tenant.id)
    res = await db.execute(stmt)
    reminder = res.scalars().first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Xatırlatma tapılmadı.")

    if payload.title is not None:
        reminder.title = payload.title.strip()
    if payload.reminder_type is not None:
        reminder.reminder_type = payload.reminder_type
    if payload.notes is not None:
        reminder.notes = payload.notes
    if payload.remind_before_minutes is not None:
        reminder.remind_before_minutes = payload.remind_before_minutes
    if payload.status is not None:
        reminder.status = payload.status
    if payload.client_id is not None:
        reminder.client_id = payload.client_id
    if payload.deal_id is not None:
        reminder.deal_id = payload.deal_id
    if payload.due_at is not None:
        due_dt = payload.due_at
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=timezone.utc)
        reminder.due_at = due_dt
        if reminder.status == "notified":
            reminder.status = "pending" # Reset to pending if rescheduled

    reminder.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(reminder)
    return await format_reminder_response(db, reminder)


@router.delete("/reminders/{reminder_id}")
async def delete_crm_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a reminder."""
    tenant = await get_tenant_for_user(db, current_user)

    stmt = select(CrmReminder).where(CrmReminder.id == reminder_id, CrmReminder.tenant_id == tenant.id)
    res = await db.execute(stmt)
    reminder = res.scalars().first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Xatırlatma tapılmadı.")

    await db.delete(reminder)
    await db.commit()
    return {"message": "Xatırlatma uğurla silindi.", "reminder_id": reminder_id}

