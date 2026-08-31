from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin
from app.models.listing import ListingSource, Listing
from app.models.match import Match
from app.services.ingestion import IngestionService

router = APIRouter(prefix="/scrapers", tags=["Scrapers"])

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ListingSourceCreate(BaseModel):
    name: str
    type: str  # 'facebook_group', 'facebook_page', 'telegram_channel', 'website'
    url_or_handle: str

class ListingSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    name: str
    url_or_handle: str
    tenant_id: Optional[int] = None
    status: str
    last_scraped_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

@router.get("/sources", response_model=List[ListingSourceResponse])
async def list_sources(db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    stmt = select(ListingSource).order_by(ListingSource.id)
    res = await db.execute(stmt)
    sources = res.scalars().all()
    return sources

@router.post("/sources", response_model=ListingSourceResponse)
async def create_source(payload: ListingSourceCreate, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Add a new Facebook Group, Facebook Page, Telegram channel, or real estate portal source."""
    new_src = ListingSource(
        name=payload.name.strip(),
        type=payload.type.strip(),
        url_or_handle=payload.url_or_handle.strip(),
        status="active"
    )
    db.add(new_src)
    await db.commit()
    await db.refresh(new_src)
    return new_src

@router.patch("/sources/{source_id}/toggle", response_model=ListingSourceResponse)
async def toggle_source(source_id: int, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Toggle source status between active and paused."""
    from fastapi import HTTPException
    stmt = select(ListingSource).where(ListingSource.id == source_id)
    res = await db.execute(stmt)
    source = res.scalars().first()
    if not source:
        raise HTTPException(status_code=404, detail="Mənbə tapılmadı")

    source.status = "paused" if source.status == "active" else "active"
    await db.commit()
    await db.refresh(source)
    return source

@router.delete("/sources/{source_id}")
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Delete a listing source."""
    from fastapi import HTTPException
    stmt = select(ListingSource).where(ListingSource.id == source_id)
    res = await db.execute(stmt)
    source = res.scalars().first()
    if not source:
        raise HTTPException(status_code=404, detail="Mənbə tapılmadı")

    await db.delete(source)
    await db.commit()
    return {"status": "deleted", "id": source_id}

async def _bg_run_ingestion():
    import logging
    logger = logging.getLogger("scrapers_api")
    logger.info("[ManualTrigger] Manual scraping and matching triggered from Admin Dashboard...")
    try:
        from app.db.session import AsyncSessionLocal
        from app.services.ingestion import IngestionService
        from app.models.saved_search import SavedSearch

        async with AsyncSessionLocal() as db:
            result = await IngestionService.run_ingestion_cycle(db)
            logger.info(f"[ManualTrigger] Ingestion cycle completed: {result}")

            # Run backfill for all active saved searches to deliver matching listings immediately
            stmt_s = select(SavedSearch).where(SavedSearch.is_active == True)
            res_s = await db.execute(stmt_s)
            active_searches = res_s.scalars().all()
            for s in active_searches:
                await IngestionService.run_targeted_instant_backfill(db, s)
    except Exception as e:
        logger.error(f"[ManualTrigger] Error during manual scraping cycle: {e}")

async def _bg_recheck_listings(limit: int = 1000):
    import logging
    logger = logging.getLogger("scrapers_api")
    from app.db.session import AsyncSessionLocal
    logger.info(f"[ManualRecheck] Healing and re-evaluating top {limit} listings...")
    try:
        async with AsyncSessionLocal() as db:
            result = await IngestionService.recheck_and_heal_all_listings(db, limit=limit)
            logger.info(f"[ManualRecheck] Completed: {result}")
    except Exception as e:
        logger.error(f"[ManualRecheck] Error during listings recheck: {e}")

@router.post("/recheck")
async def recheck_historical_listings(background_tasks: BackgroundTasks, current_admin = Depends(get_current_admin)):
    """Heals historical listings in background: purges hotlines, refetches real phones & seller classifications, and delivers matches."""
    background_tasks.add_task(_bg_recheck_listings, 1000)
    return {
        "status": "started",
        "message": "Baza elanlarının təmizlənməsi və yenidən yoxlanılması arxa planda uğurla başladıldı."
    }

@router.post("/trigger")
async def trigger_ingestion(background_tasks: BackgroundTasks, current_admin = Depends(get_current_admin)):
    """Manually trigger scraping, parsing, and match delivery cycle in background."""
    background_tasks.add_task(_bg_run_ingestion)
    return {
        "status": "started",
        "message": "Skreyp və uyğunlaşdırma dövrü arxa planda uğurla başladıldı."
    }

@router.get("/stats")
async def get_system_stats(db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    from sqlalchemy import func
    stmt_sources = select(func.count(ListingSource.id))
    sources_cnt = (await db.execute(stmt_sources)).scalar() or 0

    stmt_listings = select(func.count(Listing.id))
    listings_cnt = (await db.execute(stmt_listings)).scalar() or 0

    stmt_matches = select(func.count(Match.id))
    matches_cnt = (await db.execute(stmt_matches)).scalar() or 0

    return {
        "total_sources": sources_cnt,
        "total_listings": listings_cnt,
        "total_matches": matches_cnt
    }
