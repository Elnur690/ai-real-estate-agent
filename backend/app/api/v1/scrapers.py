from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin
from app.models.listing import ListingSource, Listing
from app.models.match import Match
from app.services.ingestion import IngestionService

router = APIRouter(prefix="/scrapers", tags=["Scrapers"])

@router.get("/sources")
async def list_sources(db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    stmt = select(ListingSource).order_by(ListingSource.id)
    res = await db.execute(stmt)
    sources = res.scalars().all()
    return sources

@router.post("/trigger")
async def trigger_ingestion(db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Manually trigger scraping, parsing, and match delivery cycle."""
    result = await IngestionService.run_ingestion_cycle(db)
    return {
        "status": "completed",
        "result": result
    }

@router.get("/stats")
async def get_system_stats(db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    stmt_sources = select(ListingSource)
    res_sources = await db.execute(stmt_sources)
    sources = res_sources.scalars().all()

    stmt_listings = select(Listing)
    res_listings = await db.execute(stmt_listings)
    listings = res_listings.scalars().all()

    stmt_matches = select(Match)
    res_matches = await db.execute(stmt_matches)
    matches = res_matches.scalars().all()

    return {
        "total_sources": len(sources),
        "total_listings": len(listings),
        "total_matches": len(matches)
    }
