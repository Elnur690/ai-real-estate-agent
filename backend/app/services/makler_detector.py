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
        from app.core.property_classifier import classify_property_and_offer, AGENCY_KEYWORDS, OWNER_KEYWORDS, COMMISSION_REGEX

        text_lower = f"{listing.title or ''} {listing.description or ''} {listing.address_raw or ''} {listing.listing_url or ''}".lower()
        score = 0.0

        # Run Property, Offer, and Seller classifier
        detected_offer, detected_prop, detected_seller = classify_property_and_offer(
            title=listing.title or "",
            description=listing.description or "",
            url=listing.listing_url or "",
            raw_text=text_lower
        )

        listing.offer_type = detected_offer
        listing.property_type = detected_prop

        has_agency_kw = any(kw in text_lower for kw in AGENCY_KEYWORDS) or bool(COMMISSION_REGEX.search(text_lower))
        has_owner_kw = any(kw in text_lower for kw in OWNER_KEYWORDS)

        # Agency / Broker signals strictly take precedence over "sahibindən"
        if has_agency_kw or detected_seller == "agency":
            score = 1.0
            listing.seller_type = "agency"
            listing.is_makler = True
            listing.makler_score = 1.0
        elif has_owner_kw and not has_agency_kw:
            score = 0.0
            listing.seller_type = "owner"
            listing.is_makler = False
            listing.makler_score = 0.0
        else:
            listing.seller_type = detected_seller
            listing.is_makler = (detected_seller == "agency")
            listing.makler_score = 1.0 if (detected_seller == "agency") else 0.0

        # First-Posting History Analysis
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
                
                # If earlier listing was from an agency, or if it was posted on major portal bina.az:
                # Any secondary aggregator re-post claiming "Sahibindən" is a makler disguise
                if (
                    earlier_listing.seller_type == "agency" or
                    earlier_listing.is_makler or
                    (earlier_listing.makler_score or 0.0) >= 0.30 or
                    "bina.az" in (earlier_listing.listing_url or "").lower()
                ):
                    score = 1.0
                    listing.seller_type = "agency"
                    listing.is_makler = True
                    listing.makler_score = 1.0
                    logger.info(f"[MaklerDetector] Listing #{listing.id} was ALREADY posted by agency/bina.az at {earlier_listing.listing_url}. Strictly overriding seller_type to AGENCY.")
                else:
                    score = max(score, 0.7)
                    listing.seller_type = "agency"
                    listing.is_makler = True
                    listing.makler_score = 1.0
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

            if phone_listings_count >= 2:
                score = 1.0
                listing.seller_type = "agency"
                listing.is_makler = True

        listing.makler_score = max(0.0, min(1.0, round(score, 2)))
        return listing
