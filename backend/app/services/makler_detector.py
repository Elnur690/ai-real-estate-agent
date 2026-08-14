import re
import logging
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.listing import Listing

logger = logging.getLogger(__name__)

class MaklerDetectorService:
    @staticmethod
    async def analyze_listing(db: AsyncSession, listing: Listing) -> Listing:
        """
        Analyzes a newly scraped listing for:
        1. First-Posting Verification: Checks if the exact same property was posted earlier by an agency/other user.
        2. Makler Disguise Score (0.0 to 1.0): Evaluates seller authenticity.
        """
        text_lower = f"{listing.title} {listing.description or ''}".lower()
        score = 0.0

        # Keyword Signals
        if "vasitəçisiz" in text_lower or "sahibindən" in text_lower or "mülkiyyətçidən" in text_lower:
            score -= 0.2
        if "agentlik" in text_lower or "ofis haqqı" in text_lower or "xidmət haqqı" in text_lower or "komissiya" in text_lower:
            score += 0.6
            listing.seller_type = "agency"

        # First-Posting History Analysis
        # Search for any existing listing created BEFORE this listing with matching district, rooms, area (+/- 3sqm), and price (+/- 5%)
        if listing.district and listing.rooms and listing.area_sqm:
            min_area = listing.area_sqm - 3.0
            max_area = listing.area_sqm + 3.0
            min_price = listing.price * 0.95
            max_price = listing.price * 1.05

            created_time = listing.created_at or datetime.now(timezone.utc)
            if created_time.tzinfo is None:
                created_time = created_time.replace(tzinfo=timezone.utc)

            stmt_earlier = select(Listing).where(
                Listing.id != listing.id,
                Listing.district == listing.district,
                Listing.rooms == listing.rooms,
                Listing.area_sqm >= min_area,
                Listing.area_sqm <= max_area,
                Listing.price >= min_price,
                Listing.price <= max_price,
                Listing.created_at < created_time
            ).order_by(Listing.created_at.asc())

            res_earlier = await db.execute(stmt_earlier)
            earlier_listing = res_earlier.scalars().first()

            if earlier_listing:
                listing.is_first_posting = False
                listing.earlier_posting_url = earlier_listing.listing_url
                score += 0.4
                logger.info(f"[MaklerDetector] Listing #{listing.id} was ALREADY posted earlier at {earlier_listing.listing_url}")
            else:
                listing.is_first_posting = True
                listing.earlier_posting_url = None

        # Phone Number Multi-Listing Frequency Analysis
        phone_match = re.search(r'(\+?994|0)?\s*(50|51|55|70|77|99|10)\s*\d{3}\s*\d{2}\s*\d{2}', text_lower)
        if phone_match:
            raw_digits = re.sub(r'\D', '', phone_match.group())
            phone_suffix = raw_digits[-7:] if len(raw_digits) >= 7 else raw_digits
            stmt_count = select(func.count(Listing.id)).where(
                (Listing.phone_number.like(f"%{phone_suffix}%")) |
                (Listing.description.like(f"%{phone_suffix}%"))
            )
            res_count = await db.execute(stmt_count)
            phone_listings_count = res_count.scalar() or 0

            if phone_listings_count >= 3:
                score += 0.5
                listing.seller_type = "agency"

        listing.makler_score = max(0.0, min(1.0, round(score, 2)))
        return listing
