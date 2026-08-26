import logging
from typing import List, Optional
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.listing import Listing, ListingSource

logger = logging.getLogger(__name__)

class DuplicateDetectorService:
    @classmethod
    async def analyze_and_group_duplicates(cls, db: AsyncSession, listing: Listing) -> Listing:
        """
        Detects if this listing is a duplicate/multi-broker posting of an already listed property.
        Groups identical properties across bina.az, tap.az, yeniemlak.az, etc.
        """
        if not listing.rooms or not listing.area_sqm:
            return listing

        try:
            # 1. Build candidates query
            conditions = [
                Listing.id != listing.id,
                Listing.is_active == True,
                Listing.rooms == listing.rooms,
                Listing.area_sqm >= (listing.area_sqm - 2.5),
                Listing.area_sqm <= (listing.area_sqm + 2.5),
                Listing.offer_type == (listing.offer_type or "sale")
            ]

            # Match location (district or metro)
            location_conds = []
            if listing.district:
                location_conds.append(Listing.district.ilike(f"%{listing.district}%"))
            if listing.metro_station:
                location_conds.append(Listing.metro_station.ilike(f"%{listing.metro_station}%"))
            if location_conds:
                conditions.append(or_(*location_conds))

            # Floor matching if available
            if listing.floor and listing.total_floors:
                conditions.append(or_(
                    and_(Listing.floor == listing.floor, Listing.total_floors == listing.total_floors),
                    Listing.floor.is_(None)
                ))

            stmt = select(Listing).where(and_(*conditions)).limit(10)
            res = await db.execute(stmt)
            candidates = res.scalars().all()

            if not candidates:
                listing.duplicate_count = 1
                listing.duplicate_listings = []
                return listing

            # 2. Refine matching with price range (±15%) or matching phone number
            matched_duplicates: List[Listing] = []
            for c in candidates:
                # If phone matches exactly -> definite duplicate
                if listing.phone_number and c.phone_number and listing.phone_number == c.phone_number:
                    matched_duplicates.append(c)
                    continue

                # If price is within ±15%
                if listing.price and c.price:
                    min_p = min(listing.price, c.price)
                    max_p = max(listing.price, c.price)
                    if (max_p - min_p) / max_p <= 0.15:
                        matched_duplicates.append(c)

            if not matched_duplicates:
                listing.duplicate_count = 1
                listing.duplicate_listings = []
                return listing

            # 3. Create or reuse Duplicate Group ID
            all_in_group = [listing] + matched_duplicates
            existing_group_ids = [l.duplicate_group_id for l in matched_duplicates if l.duplicate_group_id]
            valid_ids = [l.id for l in all_in_group if l.id is not None]
            min_id = min(valid_ids) if valid_ids else (listing.external_id or "0")
            group_id = existing_group_ids[0] if existing_group_ids else f"dup_grp_{min_id}"

            # 4. Serialize summary of duplicates
            group_data = []
            for l in all_in_group:
                group_data.append({
                    "id": l.id,
                    "external_id": l.external_id,
                    "price": l.price,
                    "seller_type": l.seller_type or "makler",
                    "phone": l.phone_number,
                    "url": l.listing_url,
                    "district": l.district,
                    "rooms": l.rooms,
                    "area_sqm": l.area_sqm
                })

            # Sort by price ascending so lowest price is first
            group_data.sort(key=lambda x: x.get("price") or 0)
            total_count = len(group_data)

            # Update current listing
            listing.duplicate_group_id = group_id
            listing.duplicate_count = total_count
            listing.duplicate_listings = group_data

            # If multi-broker postings exist with different phone numbers, different prices, or agency flags,
            # this property is being actively brokered across multiple agents.
            unique_phones = {l.phone_number for l in all_in_group if l.phone_number}
            unique_prices = {l.price for l in all_in_group if l.price}
            is_multi_broker = (
                len(unique_phones) > 1 or
                len(unique_prices) > 1 or
                any(l.seller_type == "agency" or l.is_makler for l in all_in_group)
            )

            if is_multi_broker:
                listing.is_makler = True
                listing.seller_type = "agency"
                listing.makler_score = 1.0

            # Update other listings in group
            for c in matched_duplicates:
                c.duplicate_group_id = group_id
                c.duplicate_count = total_count
                c.duplicate_listings = group_data
                if is_multi_broker:
                    c.is_makler = True
                    c.seller_type = "agency"
                    c.makler_score = 1.0

            logger.info(f"[DuplicateDetector] Grouped Listing #{listing.id} into group {group_id} ({total_count} duplicates detected, multi_broker={is_multi_broker})")
            return listing

        except Exception as e:
            logger.error(f"[DuplicateDetector] Error analyzing duplicates for #{listing.id}: {e}")
            return listing
