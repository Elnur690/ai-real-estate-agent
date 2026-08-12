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
        if not listing.price or not listing.area_sqm or listing.area_sqm <= 0:
            return listing

        # 1. Price per SQM
        price_sqm = round(listing.price / listing.area_sqm, 2)
        listing.price_per_sqm = price_sqm

        if not listing.district:
            return listing

        # 2. Dynamic District Average Price per SQM
        stmt = select(func.avg(Listing.price_per_sqm)).where(
            Listing.district == listing.district,
            Listing.price_per_sqm > 0,
            Listing.is_active == True
        )
        res = await db.execute(stmt)
        avg_sqm = res.scalar()

        if avg_sqm and avg_sqm > 0:
            district_avg = round(float(avg_sqm), 2)
            listing.district_avg_sqm = district_avg

            # Calculate Percentage Difference
            diff_pct = round(((price_sqm - district_avg) / district_avg) * 100, 1)
            listing.bargain_percentage = diff_pct
            
            if diff_pct <= -10.0:
                logger.info(f"[AVMEngine] Hot Deal Detected! Listing #{listing.id} in {listing.district} is {abs(diff_pct)}% BELOW market average ({district_avg} AZN/m² vs {price_sqm} AZN/m²)")

        return listing
