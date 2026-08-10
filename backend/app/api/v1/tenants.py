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

class UpdateTenantRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None # active | expired | suspended | pending
    plan: Optional[str] = None
    plan_period: Optional[str] = None
    preferred_channel: Optional[str] = None
    whatsapp_number: Optional[str] = None
    telegram_chat_id: Optional[str] = None

@router.get("")
async def list_tenants(db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    stmt = select(Tenant).order_by(Tenant.id.desc())
    res = await db.execute(stmt)
    tenants = res.scalars().all()
    return tenants

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tenant(body: CreateTenantRequest, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    expires_at = datetime.now(timezone.utc) + (timedelta(days=30) if body.plan_period == "monthly" else timedelta(days=90))
    tenant = Tenant(
        name=body.name,
        type=body.type,
        phone=body.phone,
        telegram_handle=body.telegram_handle,
        preferred_channel=body.preferred_channel,
        whatsapp_number=body.whatsapp_number,
        telegram_chat_id=body.telegram_chat_id,
        plan=body.plan,
        plan_period=body.plan_period,
        plan_started_at=datetime.now(timezone.utc),
        plan_expires_at=expires_at,
        status="active"
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
    stmt_s = select(SavedSearch).where(SavedSearch.tenant_id == tenant_id)
    res_s = await db.execute(stmt_s)
    searches = res_s.scalars().all()

    return {
        "tenant": tenant,
        "saved_searches": searches
    }

@router.patch("/{tenant_id}")
async def update_tenant(tenant_id: int, body: UpdateTenantRequest, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(tenant, field, val)

    await db.commit()
    await db.refresh(tenant)
    return tenant
