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
            raw_text=text_lower,
            existing_seller_type=listing.seller_type
        )

        listing.offer_type = detected_offer
        listing.property_type = detected_prop

        has_agency_kw = any(kw in text_lower for kw in AGENCY_KEYWORDS) or bool(COMMISSION_REGEX.search(text_lower))
        has_owner_kw = any(kw in text_lower for kw in OWNER_KEYWORDS) or "owner_type=owner" in (listing.listing_url or "").lower() or (listing.seller_type == "owner")

        # Agency / Broker signals strictly take precedence over "sahibindən"
        if has_agency_kw:
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
            listing.seller_type = detected_seller or listing.seller_type or "owner"
            listing.is_makler = (listing.seller_type == "agency")
            listing.makler_score = 1.0 if (listing.seller_type == "agency") else 0.0

        # First-Posting History Analysis (Requires high precision matching: floor + total_floors + strict area & price)
        if listing.district and listing.rooms and listing.area_sqm and listing.floor and listing.total_floors:
            min_area = listing.area_sqm - 1.0
            max_area = listing.area_sqm + 1.0
            min_price = listing.price * 0.97
            max_price = listing.price * 1.03

            created_time = listing.created_at or datetime.now(timezone.utc)
            if created_time.tzinfo is None:
                created_time = created_time.replace(tzinfo=timezone.utc)

            stmt_earlier = select(Listing).where(
                Listing.id != listing.id,
                Listing.district == listing.district,
                Listing.rooms == listing.rooms,
                Listing.floor == listing.floor,
                Listing.total_floors == listing.total_floors,
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
                
                # If earlier listing was explicitly from an agency, flag as makler repost
                if (
                    earlier_listing.seller_type == "agency" or
                    earlier_listing.is_makler or
                    (earlier_listing.makler_score or 0.0) >= 0.70
                ):
                    score = 1.0
                    listing.seller_type = "agency"
                    listing.is_makler = True
                    listing.makler_score = 1.0
                    logger.info(f"[MaklerDetector] Listing #{listing.id} was ALREADY posted by agency at {earlier_listing.listing_url}. Setting seller_type to AGENCY.")
            else:
                listing.is_first_posting = True
                listing.earlier_posting_url = None

        # Phone Number Multi-Listing Frequency Analysis (Mobile and Landlines)
        raw_phone_str = listing.phone_number or ""
        if not raw_phone_str:
            phone_match = re.search(r'(\+?994|0)?\s*(50|51|55|70|77|99|10|12|60|18)\s*\d{3}\s*\d{2}\s*\d{2}', text_lower)
            if phone_match:
                raw_phone_str = phone_match.group()

        if raw_phone_str:
            raw_digits = re.sub(r'\D', '', raw_phone_str)
            phone_suffix = raw_digits[-7:] if len(raw_digits) >= 7 else raw_digits
            if phone_suffix:
                stmt_count = select(func.count(Listing.id)).where(
                    Listing.id != listing.id,
                    (Listing.phone_number.like(f"%{phone_suffix}%")) |
                    (Listing.description.like(f"%{phone_suffix}%"))
                )
                res_count = await db.execute(stmt_count)
                phone_listings_count = res_count.scalar() or 0

                if phone_listings_count >= 1:
                    score = 1.0
                    listing.seller_type = "agency"
                    listing.is_makler = True
                    listing.makler_score = 1.0
                    logger.info(f"[MaklerDetector] Listing #{listing.id} shares phone {phone_suffix} with {phone_listings_count} other listings in database. Classified as AGENCY.")

        listing.makler_score = max(0.0, min(1.0, round(score, 2)))
        return listing
