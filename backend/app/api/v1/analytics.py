from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin
from app.models.listing import Listing

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Baku District Centroids (Latitude, Longitude)
BAKU_DISTRICT_COORDINATES: Dict[str, Dict[str, float]] = {
    "Yasamal": {"lat": 40.3772, "lng": 49.8093},
    "Nəsimi": {"lat": 40.3850, "lng": 49.8350},
    "Xətai": {"lat": 40.3800, "lng": 49.8800},
    "Nərimanov": {"lat": 40.4050, "lng": 49.8700},
    "Səbail": {"lat": 40.3600, "lng": 49.8300},
    "Binəqədi": {"lat": 40.4500, "lng": 49.8200},
    "Nizami": {"lat": 40.4150, "lng": 49.9150},
    "Sabunçu": {"lat": 40.4400, "lng": 49.9500},
    "Suraxanı": {"lat": 40.4200, "lng": 50.0000},
    "Xəzər": {"lat": 40.4500, "lng": 50.1000},
    "Qaradağ": {"lat": 40.3000, "lng": 49.7000},
    "Pirallahi": {"lat": 40.4700, "lng": 50.3500}
}

@router.get("/map")
async def get_property_heatmap(db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Returns price/m² heatmap and property pins for Baku interactive map view."""
    stmt = select(Listing).where(Listing.is_active == True).order_by(Listing.id.desc()).limit(150)
    res = await db.execute(stmt)
    listings = res.scalars().all()

    district_stats: Dict[str, Dict[str, Any]] = {}
    pins = []

    for l in listings:
        district_name = l.district or "Yasamal"
        # Match district name case-insensitively
        matched_key = "Yasamal"
        for k in BAKU_DISTRICT_COORDINATES:
            if k.lower() in district_name.lower():
                matched_key = k
                break

        coords = BAKU_DISTRICT_COORDINATES.get(matched_key, {"lat": 40.3800, "lng": 49.8500})
        
        # Add slight random offset to prevent overlapping markers on map
        lat_offset = (hash(l.external_id or str(l.id)) % 100 - 50) * 0.0001
        lng_offset = (hash(str(l.id) + "lng") % 100 - 50) * 0.0001
        lat = coords["lat"] + lat_offset
        lng = coords["lng"] + lng_offset

        price_per_m2 = l.price_per_sqm or (round(l.price / l.area_sqm, 2) if l.area_sqm and l.area_sqm > 0 else 0.0)
        is_bargain = (l.bargain_percentage and l.bargain_percentage <= -10.0) or False

        pins.append({
            "id": l.id,
            "title": l.title,
            "price": l.price,
            "currency": l.currency,
            "district": matched_key,
            "metro_station": l.metro_station,
            "rooms": l.rooms,
            "area_sqm": l.area_sqm,
            "price_per_sqm": price_per_m2,
            "bargain_percentage": l.bargain_percentage or 0.0,
            "is_bargain": is_bargain,
            "lat": round(lat, 5),
            "lng": round(lng, 5),
            "listing_url": l.listing_url
        })

        if matched_key not in district_stats:
            district_stats[matched_key] = {"count": 0, "total_price_sqm": 0.0, "bargain_count": 0}
        
        district_stats[matched_key]["count"] += 1
        if price_per_m2 > 0:
            district_stats[matched_key]["total_price_sqm"] += price_per_m2
        if is_bargain:
            district_stats[matched_key]["bargain_count"] += 1

    district_heatmap = []
    for dist_name, stats in district_stats.items():
        coords = BAKU_DISTRICT_COORDINATES.get(dist_name, {"lat": 40.3800, "lng": 49.8500})
        avg_sqm = round(stats["total_price_sqm"] / stats["count"], 2) if stats["count"] > 0 else 0.0
        district_heatmap.append({
            "district": dist_name,
            "lat": coords["lat"],
            "lng": coords["lng"],
            "active_count": stats["count"],
            "avg_price_per_sqm": avg_sqm,
            "bargain_deals_count": stats["bargain_count"]
        })

    return {
        "districts_heatmap": district_heatmap,
        "property_pins": pins
    }
