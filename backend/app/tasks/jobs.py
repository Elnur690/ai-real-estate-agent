import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select, update

from app.tasks.celery_app import celery_app
from app.db.session import SyncSessionLocal
from app.models.tenant import Tenant
from app.services.ingestion import IngestionService

logger = logging.getLogger(__name__)

@celery_app.task
def run_scheduled_ingestion():
    """Celery periodic job to run scraping, normalization, AI match scoring, and notification dispatch."""
    logger.info("[CeleryJob] Starting scheduled ingestion cycle...")
    
    async def _runner():
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await IngestionService.run_ingestion_cycle(db)
            logger.info(f"[CeleryJob] Cycle complete: {result}")
            return result

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    return loop.run_until_complete(_runner())


@celery_app.task
def check_plan_expirations():
    """Celery periodic job to check tenant plan expiry dates and mark status as 'expired'."""
    logger.info("[CeleryJob] Checking tenant plan expirations...")
    now = datetime.now(timezone.utc)
    
    with SyncSessionLocal() as session:
        stmt = update(Tenant).where(
            Tenant.plan_expires_at.is_not(None),
            Tenant.plan_expires_at < now,
            Tenant.status == "active"
        ).values(status="expired")
        
        result = session.execute(stmt)
        session.commit()
        logger.info(f"[CeleryJob] Updated {result.rowcount} expired tenants to 'expired' status.")
        return result.rowcount
