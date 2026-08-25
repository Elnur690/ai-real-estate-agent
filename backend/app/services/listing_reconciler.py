import asyncio
import logging
from datetime import datetime, timezone, timedelta
import httpx
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.listing import Listing

logger = logging.getLogger(__name__)

class ListingReconcilerService:
    """
    Periodically checks active listings in the database to verify if they are still active
    on the original portal (Bina.az, Tap.az, etc.). If a listing is sold, deactivated,
    or deleted (404 / 'elan artıq aktiv deyil'), it marks is_active = False in the database.
    """

    INACTIVE_KEYWORDS = [
        "elan artıq aktiv deyil",
        "elan arxivləşdirilib",
        "elan silinib",
        "satıldı",
        "satilib",
        "kirayə verilib",
        "kiraye verilib",
        "tapılmadı",
        "elan müddəti bitib",
    ]

    @staticmethod
    async def check_url_liveness(url: str, client: httpx.AsyncClient) -> bool:
        """Returns True if the listing is still active, False if inactive/sold/deleted."""
        if not url or not url.startswith("http"):
            return True
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
            resp = await client.get(url, headers=headers, timeout=5.0)
            if resp.status_code in [404, 410]:
                return False
            
            if resp.status_code == 200:
                html = resp.text.lower()
                for kw in ListingReconcilerService.INACTIVE_KEYWORDS:
                    if kw in html:
                        return False
            return True
        except Exception as e:
            # On transient timeout or network glitch, do not falsely deactivate
            logger.debug(f"[ListingReconciler] Timeout/error checking {url}: {e}")
            return True

    @staticmethod
    async def reconcile_batch(batch_size: int = 30) -> dict:
        """
        Picks a batch of active listings that are older than 1 day and checks their liveness.
        """
        async with AsyncSessionLocal() as db:
            try:
                # Select active listings created between 1 day and 60 days ago
                now = datetime.now(timezone.utc)
                min_age = now - timedelta(days=1)
                max_age = now - timedelta(days=60)

                stmt = (
                    select(Listing)
                    .where(
                        Listing.is_active == True,
                        Listing.created_at <= min_age,
                        Listing.created_at >= max_age
                    )
                    .order_by(Listing.last_seen_at.asc())
                    .limit(batch_size)
                )
                res = await db.execute(stmt)
                listings = res.scalars().all()

                if not listings:
                    return {"checked": 0, "deactivated": 0}

                checked = 0
                deactivated = 0

                async with httpx.AsyncClient(follow_redirects=True) as client:
                    for item in listings:
                        target_url = getattr(item, 'listing_url', None) or getattr(item, 'url', None)
                        if not target_url:
                            continue
                        checked += 1
                        is_active = await ListingReconcilerService.check_url_liveness(target_url, client)
                        item.last_seen_at = datetime.now(timezone.utc)
                        if not is_active:
                            item.is_active = False
                            deactivated += 1
                            logger.info(f"[ListingReconciler] Deactivating sold/expired listing #{item.id} ({target_url})")
                        # Gentle pacing between checks
                        await asyncio.sleep(0.3)

                await db.commit()

                return {"checked": checked, "deactivated": deactivated}
            except Exception as e:
                logger.error(f"[ListingReconciler] Error during reconciliation batch: {e}")
                return {"checked": 0, "deactivated": 0, "error": str(e)}

    @staticmethod
    async def start_background_reconciler(interval_minutes: int = 15):
        """Runs the reconciliation loop continuously every 15 minutes."""
        logger.info(f"[ListingReconciler] Background reconciler started (interval: {interval_minutes}m)")
        await asyncio.sleep(60) # Wait 1 minute after startup
        while True:
            try:
                result = await ListingReconcilerService.reconcile_batch(batch_size=40)
                if result.get("checked", 0) > 0:
                    logger.info(f"[ListingReconciler] Reconciled {result['checked']} listings, deactivated {result['deactivated']} inactive listings.")
            except Exception as e:
                logger.error(f"[ListingReconciler] Loop error: {e}")
            await asyncio.sleep(interval_minutes * 60)
