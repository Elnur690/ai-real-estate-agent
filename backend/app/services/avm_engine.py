import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.listing import Listing

logger = logging.getLogger(__name__)

class AVMEngineService:
    @staticmethod
    async def evaluate_listing_valuation(db: AsyncSession, listing: Listing) -> Listing:
        """
        Calculates listing price per sqm and compares against dynamic district average.
        Flags listings priced <= -10% below market average as Bargain Deals.
        """
        offer_type = getattr(listing, 'offer_type', 'sale') or 'sale'

        # Daily rentals are priced per day (not per sqm or monthly), so skip AVM sqm comparison
        if offer_type == 'daily_rent' or (listing.price and listing.price <= 200 and 'gunluk' in (listing.listing_url or '').lower()):
            listing.price_per_sqm = None
            listing.bargain_percentage = 0.0
            return listing

        if not listing.price or not listing.area_sqm or listing.area_sqm <= 0:
            return listing

        # 1. Price per SQM
        price_sqm = round(listing.price / listing.area_sqm, 2)
        listing.price_per_sqm = price_sqm

        if not listing.district:
            return listing

        # 2. Dynamic District Average Price per SQM (Separated strictly by Sale vs Monthly Rental & Property Type)
        from sqlalchemy import and_
        prop_type = listing.property_type or 'apartment'
        base_conds = [
            Listing.district == listing.district,
            Listing.price_per_sqm > 0,
            Listing.is_active == True,
            Listing.property_type == prop_type
        ]
        if offer_type in ['rent', 'kiraye', 'icare']:
            base_conds.extend([
                Listing.offer_type == 'rent',
                Listing.price >= 100,
                Listing.price < 50000
            ])
        else:
            base_conds.extend([
                Listing.offer_type == 'sale',
                Listing.price >= 15000
            ])

        stmt_prop = select(func.avg(Listing.price_per_sqm), func.count(Listing.id)).where(and_(*base_conds))
        res = await db.execute(stmt_prop)
        row = res.first()
        avg_sqm = row[0] if row else None
        count_samples = row[1] if row else 0

        # We require at least 3 comparable listings of the identical property type in the district to establish a valid market benchmark
        if count_samples < 3 or not avg_sqm or avg_sqm <= 0:
            listing.bargain_percentage = 0.0
            return listing

        district_avg = round(float(avg_sqm), 2)
        listing.district_avg_sqm = district_avg

        # Calculate Percentage Difference
        diff_pct = round(((price_sqm - district_avg) / district_avg) * 100, 1)
        listing.bargain_percentage = diff_pct
        
        if diff_pct <= -10.0:
            logger.info(f"[AVMEngine] Hot Deal Detected! Listing #{listing.id} ({prop_type}) in {listing.district} is {abs(diff_pct)}% BELOW market average ({district_avg} AZN/m² vs {price_sqm} AZN/m²)")

        return listing
