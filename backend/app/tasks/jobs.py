import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select, update

from app.tasks.celery_app import celery_app
from app.db.session import SyncSessionLocal
from app.models.tenant import Tenant
from app.services.ingestion import IngestionService

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_scheduled_ingestion(self):
    """Celery periodic job to run scraping, normalization, AI match scoring, and notification dispatch."""
    logger.info("[CeleryJob] Starting scheduled ingestion cycle...")
    
    async def _runner():
        from app.db.session import AsyncSessionLocal
        from app.models.saved_search import SavedSearch
        result = await IngestionService.run_ingestion_cycle()
        logger.info(f"[CeleryJob] Cycle complete: {result}")

        try:
            async with AsyncSessionLocal() as db:
                stmt_s = select(SavedSearch).where(SavedSearch.is_active == True)
                res_s = await db.execute(stmt_s)
                active_searches = res_s.scalars().all()
                for s in active_searches:
                    await IngestionService.run_targeted_instant_backfill(db, s)
        except Exception as e_bf:
            logger.debug(f"[CeleryJob] Backfill notice: {e_bf}")

        return result

    try:
        return asyncio.run(_runner())
    except Exception as exc:
        logger.error(f"[CeleryJob] Ingestion cycle error: {exc}. Retrying...")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def run_historical_recheck(self, limit: int = 1000):
    """Celery job to heal and re-evaluate historical database listings."""
    logger.info(f"[CeleryJob] Starting historical listings recheck (limit: {limit})...")
    
    async def _runner():
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            return await IngestionService.recheck_and_heal_all_listings(db, limit=limit)

    try:
        return asyncio.run(_runner())
    except Exception as exc:
        logger.error(f"[CeleryJob] Recheck error: {exc}")
        return {"error": str(exc)}


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


@celery_app.task
def perform_database_backup():
    """Celery periodic job to execute automated database backup & tenant BaaS plan backups."""
    logger.info("[CeleryJob] Executing automated database & tenant backups...")
    from app.services.backup import BackupService
    
    # 1. Full System Backup
    sys_result = BackupService.create_backup()

    # 2. Tenant Automated Plan Backups
    async def _run_tenant_backups():
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            count = await BackupService.run_scheduled_tenant_backups(db)
            return count

    try:
        tenant_count = asyncio.run(_run_tenant_backups())
        logger.info(f"[CeleryJob] Generated tenant backups for {tenant_count} tenants.")
    except Exception as e:
        logger.error(f"[CeleryJob] Error running tenant backups: {e}")
        tenant_count = 0

    return {"system_backup": sys_result, "tenant_backups_created": tenant_count}
