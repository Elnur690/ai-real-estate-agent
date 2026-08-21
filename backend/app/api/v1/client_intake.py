from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.tenant import Tenant
from app.models.saved_search import SavedSearch
from app.ai.factory import ProviderFactory

router = APIRouter(prefix="/client-intake", tags=["Client Qualification Bot"])

class ClientIntakeRequest(BaseModel):
    client_name: str
    client_phone: str
    message: str # Free form request from Instagram DM / bio link / WhatsApp intake

@router.post("/{tenant_id}")
async def process_client_intake(
    tenant_id: int,
    body: ClientIntakeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Public intake endpoint for an agent's Instagram Bio / WhatsApp Link.
    Qualifies prospective buyer criteria with AI and creates a saved search under the agent's tenant account.
    """
    stmt = select(Tenant).where(Tenant.id == tenant_id, Tenant.status == "active")
    res = await db.execute(stmt)
    tenant = res.scalars().first()

    if not tenant:
        raise HTTPException(status_code=404, detail="Agent tenant account not found or inactive")

    # Parse criteria with AI
    ai_provider = await ProviderFactory.get_provider(db, task_type="criteria_parsing", tenant_id=tenant.id)
    parsed = await ai_provider.parse_search_criteria(body.message)

    # Save search criteria to agent tenant account
    new_search = SavedSearch(
        tenant_id=tenant.id,
        name=f"Client Lead: {body.client_name} ({parsed.district or 'Ümumi'})",
        raw_criteria_text=f"Lead {body.client_name} ({body.client_phone}): {body.message}",
        district=parsed.district,
        min_price=parsed.min_price,
        max_price=parsed.max_price,
        min_rooms=parsed.min_rooms,
        max_rooms=parsed.max_rooms,
        seller_type=parsed.seller_type,
        building_type=parsed.building_type,
        is_active=True
    )
    db.add(new_search)
    await db.commit()
    await db.refresh(new_search)

    # Run instant live targeted portal scrape and historical DB backfill
    delivered_count = 0
    try:
        from app.services.ingestion import IngestionService
        delivered_count = await IngestionService.run_targeted_instant_backfill(db, new_search)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"[ClientIntake] Error during instant targeted backfill: {e}")

    return {
        "status": "success",
        "saved_search_id": new_search.id,
        "delivered_matches_count": delivered_count,
        "parsed_criteria": parsed.summary_az,
        "message": f"Təşəkkür edirik {body.client_name}! Axtarışınız agentə yönləndirildi."
    }
