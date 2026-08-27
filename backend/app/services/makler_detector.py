import re
import logging
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.listing import Listing
from app.models.agent_phone import AgentPhone

logger = logging.getLogger(__name__)

class MaklerDetectorService:
    @staticmethod
    async def inspect_photo_watermarks(listing: Listing) -> bool:
        """
        Fast inspection of listing photo paths and metadata for agency watermarks, logos, or agency stamps.
        """
        photos = listing.photos or []
        for p in photos[:4]:
            p_str = str(p).lower()
            if any(k in p_str for k in ['agent', 'agency', 'realtor', 'makler', 'watermark', 'logo', 'sirket', 'emlak_ofisi', 'baza']):
                return True
        return False

    @staticmethod
    async def analyze_listing(db: AsyncSession, listing: Listing) -> Listing:
        """
        Analyzes a newly scraped listing for:
        1. Instant O(1) AgentPhone Directory lookup.
        2. First-Posting Verification: Checks if the exact same property was posted earlier by an agency/other user.
        3. Makler Disguise Score (0.0 to 1.0): Evaluates seller authenticity and photo watermarks.
        """
        from app.core.property_classifier import (
            classify_property_and_offer, AGENCY_KEYWORDS, OWNER_KEYWORDS,
            COMMISSION_REGEX, INVENTORY_CODE_REGEX, MULTI_INVENTORY_REGEX, normalize_az_text
        )

        text_lower = normalize_az_text(f"{listing.title or ''} {listing.description or ''} {listing.address_raw or ''} {listing.listing_url or ''}")
        score = 0.0

        # Step 0: Fast O(1) lookup in persistent AgentPhone directory
        raw_phone_str = listing.phone_number or ""
        if not raw_phone_str:
            phone_match = re.search(r'(\+?994|0)?\s*(50|51|55|70|77|99|10|12|60|18)\s*\d{3}\s*\d{2}\s*\d{2}', text_lower)
            if phone_match:
                raw_phone_str = phone_match.group()

        if raw_phone_str:
            clean_digits = re.sub(r'\D', '', raw_phone_str)
            if len(clean_digits) >= 7:
                phone_key = clean_digits[-9:] if len(clean_digits) >= 9 else clean_digits
                try:
                    stmt_agent = select(AgentPhone).where(AgentPhone.phone_clean.like(f"%{phone_key}%"))
                    res_agent = await db.execute(stmt_agent)
                    agent_record = res_agent.scalars().first()
                    if agent_record and agent_record.is_blocked_makler:
                        listing.seller_type = "agency"
                        listing.is_makler = True
                        listing.makler_score = 1.0
                        agent_record.listing_count += 1
                        agent_record.last_seen_at = datetime.now(timezone.utc)
                        logger.info(f"[MaklerDetector] Listing #{listing.id} matched verified AgentPhone #{agent_record.id} ({agent_record.phone_clean}). Instantly flagged as AGENCY.")
                        return listing
                except Exception as e:
                    logger.debug(f"[MaklerDetector] AgentPhone check notice: {e}")

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

        # Check Photo Watermarks & Agency stamps
        has_photo_watermark = await MaklerDetectorService.inspect_photo_watermarks(listing)

        # Mask genuine owner negations to prevent false positives
        text_for_agency_check = re.sub(
            r'\b(?:vasitəçisiz|vasitecisiz|maklersiz|vasitəçi yoxdur|vasiteci yoxdur|vasitəçi deyiləm|vasiteci deyilem|vasitəçi deyil|vasiteci deyil|makler deyiləm|makler deyilem|makler deyil|maklerlər narahat etməsin|maklerler narahat etmesin|vasitəçilər narahat etməsin|vasiteciler narahat etmesin)\b',
            ' [GENUINE_OWNER_FLAG] ',
            text_lower
        )

        has_agency_kw = (
            any(kw in text_for_agency_check for kw in AGENCY_KEYWORDS) or
            bool(COMMISSION_REGEX.search(text_for_agency_check)) or
            bool(INVENTORY_CODE_REGEX.search(text_for_agency_check)) or
            bool(MULTI_INVENTORY_REGEX.search(text_for_agency_check)) or
            has_photo_watermark or
            (detected_seller == "agency")
        )
        has_owner_kw = (
            any(kw in text_lower for kw in OWNER_KEYWORDS) or
            "owner_type=owner" in (listing.listing_url or "").lower() or
            "sahibinden" in (listing.listing_url or "").lower()
        )

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
            listing.seller_type = detected_seller or "agency"
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
            if len(raw_digits) >= 7:
                phone_suffix = raw_digits[-7:]
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

                    # Also update sibling listings sharing this phone number to agency
                    from sqlalchemy import update
                    await db.execute(
                        update(Listing)
                        .where(
                            (Listing.phone_number.like(f"%{phone_suffix}%")) |
                            (Listing.description.like(f"%{phone_suffix}%"))
                        )
                        .values(seller_type="agency", is_makler=True, makler_score=1.0)
                    )

        # Step 3: Register phone in AgentPhone table if identified as Agency / Makler
        if (listing.seller_type == "agency" or listing.is_makler) and raw_phone_str:
            clean_d = re.sub(r'\D', '', raw_phone_str)
            if len(clean_d) >= 7:
                p_key = clean_d[-9:] if len(clean_d) >= 9 else clean_d
                try:
                    stmt_find = select(AgentPhone).where(
                        (AgentPhone.phone_clean == clean_d) |
                        (AgentPhone.phone_clean.like(f"%{p_key}%"))
                    )
                    res_find = await db.execute(stmt_find)
                    existing_entry = res_find.scalars().first()
                    if not existing_entry:
                        try:
                            async with db.begin_nested():
                                new_agent_phone = AgentPhone(
                                    phone_clean=clean_d,
                                    phone_raw=listing.phone_number or raw_phone_str,
                                    agency_name=listing.district or "Agency",
                                    listing_count=1,
                                    is_blocked_makler=True,
                                    source="makler_detector"
                                )
                                db.add(new_agent_phone)
                                await db.flush()
                        except Exception as e_dup:
                            logger.debug(f"[MaklerDetector] AgentPhone savepoint notice ({clean_d}): {e_dup}")
                    else:
                        existing_entry.listing_count = (existing_entry.listing_count or 1) + 1
                        existing_entry.last_seen_at = datetime.now(timezone.utc)
                except Exception as e:
                    logger.debug(f"[MaklerDetector] Error registering AgentPhone: {e}")

        listing.makler_score = max(0.0, min(1.0, round(score, 2)))
        return listing
