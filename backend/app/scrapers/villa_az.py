import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers, safe_float, safe_optional_float
from app.core.baku_locations import (
    extract_baku_district, extract_metro_station, extract_baku_settlement,
    SETTLEMENT_TO_DISTRICT, METRO_TO_DISTRICT
)

logger = logging.getLogger(__name__)

class VillaAzScraper(BaseScraper):
    BASE_URL = "https://villa.az"
    API_URL = "https://villa.az/api/listings"

    async def scrape_source(self, url_or_handle: str = "https://villa.az/api/listings") -> List[RawListingItem]:
        logger.info(f"[VillaAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        # 1. Try villa.az JSON API first
        try:
            headers = get_random_headers(referer="https://villa.az/")
            headers["Accept"] = "application/json"
            headers["Accept-Language"] = "az,ru;q=0.9,en-US;q=0.8,en;q=0.7"
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                res = await client.get(self.API_URL, headers=headers)
                if res.status_code == 200 and "application/json" in res.headers.get("content-type", ""):
                    data = res.json()
                    listings_data = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                    for item in listings_data:
                        ext_id = str(item.get("id"))
                        if not ext_id:
                            continue
                        
                        title = item.get("title_az") or item.get("structured_title_az") or item.get("card_title_az") or f"Villa / Bağ evi #{ext_id}"
                        price = safe_float(item.get("price"), default=0.0)
                        curr = item.get("currency") or "AZN"
                        
                        rooms = item.get("rooms") if (item.get("rooms") and item.get("rooms") > 0) else None
                        area = safe_optional_float(item.get("area") if item.get("area") and item.get("area") > 0 else None)
                        floor = item.get("floor")
                        total_floors = item.get("totalFloors")
                        
                        loc_str = str(item.get("location") or "") + " " + str(item.get("city") or "") + " " + title
                        district = extract_baku_district(loc_str)
                        settlement = extract_baku_settlement(loc_str)
                        metro = extract_metro_station(loc_str)
                        
                        if not district:
                            if settlement and settlement in SETTLEMENT_TO_DISTRICT:
                                district = SETTLEMENT_TO_DISTRICT[settlement]
                            elif metro and metro in METRO_TO_DISTRICT:
                                district = METRO_TO_DISTRICT[metro]

                        is_agent = bool(item.get("isAgent") or item.get("agencyName"))
                        is_owner = bool(item.get("isPersonal"))
                        seller_type = "agency" if is_agent else ("owner" if is_owner else "agency")
                        
                        slug = item.get("slug_az") or item.get("slug_en") or str(ext_id)
                        listing_url = f"https://villa.az/{slug}" if not slug.startswith("http") else slug
                        
                        photos = []
                        if item.get("image"):
                            img_u = item.get("image")
                            photos.append(img_u if img_u.startswith("http") else f"https://villa.az{img_u}")

                        prop_slug = str(item.get("propertyTypeSlug") or "").lower()
                        if "land" in prop_slug or "torpaq" in prop_slug:
                            prop_type = "land"
                        elif "commercial" in prop_slug or "obyekt" in prop_slug:
                            prop_type = "commercial"
                        elif "office" in prop_slug or "ofis" in prop_slug:
                            prop_type = "office"
                        elif "apartment" in prop_slug or "menzil" in prop_slug:
                            prop_type = "apartment"
                        else:
                            prop_type = "house"

                        rent_slug = str(item.get("listingTypeSlug") or "").lower()
                        offer_type = "rent" if ("rent" in rent_slug or "kiraye" in rent_slug) else "sale"

                        items.append(RawListingItem(
                            external_id=f"villa_{ext_id}",
                            title=title,
                            description=f"Villa.az: {title} | {loc_str[:100]}",
                            price=price,
                            currency=curr,
                            district=district,
                            metro_station=metro,
                            rooms=rooms,
                            area_sqm=area,
                            floor=floor,
                            total_floors=total_floors,
                            building_type="new",
                            seller_type=seller_type,
                            offer_type=offer_type,
                            property_type=prop_type,
                            listing_url=listing_url,
                            photos=photos
                        ))
                    if items:
                        logger.info(f"[VillaAzScraper] Extracted {len(items)} listings via JSON API.")
                        return items
        except Exception as e:
            logger.debug(f"[VillaAzScraper] API fetch error: {e}")

        # 2. Fallback to HTML scraping if API returned 0
        try:
            headers = get_random_headers(referer="https://villa.az/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                res = await client.get(self.BASE_URL, headers=headers)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", href=re.compile(r'/(?:[a-zA-Z0-9_-]+)-(\d+)'))
                    seen = set()

                    for a in links:
                        href = a.get('href', '')
                        m = re.search(r'-(\d+)', href)
                        if not m:
                            continue
                        ext_id = m.group(1)
                        if ext_id in seen:
                            continue
                        seen.add(ext_id)

                        parent = a.find_parent("div") or a.find_parent("tr")
                        raw_text = parent.get_text(separator=" | ", strip=True).replace('\xa0', ' ') if parent else a.get_text(strip=True).replace('\xa0', ' ')
                        
                        price_m = re.search(r'(?i)([\d\s]+)\s*(?:AZN|₼|manat|Azn|\$)', raw_text)
                        price = safe_float(price_m.group(1) if price_m else None, default=0.0)

                        rooms_m = re.search(r'(\d+)\s*otaq', raw_text)
                        rooms = int(rooms_m.group(1)) if rooms_m else None

                        area_m = re.search(r'([\d.]+)\s*m²', raw_text) or re.search(r'([\d.]+)\s*sot', raw_text) or re.search(r'([\d.]+)\s*kv', raw_text)
                        area = safe_optional_float(area_m.group(1) if area_m else None)

                        district = extract_baku_district(raw_text) or extract_baku_district(href) 
                        settlement = extract_baku_settlement(raw_text) or extract_baku_settlement(href)
                        metro = extract_metro_station(raw_text) or extract_metro_station(href)

                        from app.core.property_classifier import classify_property_and_offer
                        detected_offer, detected_prop, detected_seller = classify_property_and_offer(
                            title="",
                            description=raw_text,
                            url=href,
                            raw_text=raw_text
                        )

                        loc_label = settlement or metro or district or 'Bakı'
                        title = f"{rooms} otaqlı Villa/Bağ evi ({loc_label})" if rooms else f"Villa/Bağ evi ({loc_label})"

                        items.append(RawListingItem(
                            external_id=f"villa_{ext_id}",
                            title=title,
                            description=f"Villa.az elanı: {raw_text[:200]}",
                            price=price,
                            currency="AZN",
                            district=district,
                            metro_station=metro,
                            rooms=rooms,
                            area_sqm=area,
                            building_type="new",
                            seller_type=detected_seller,
                            offer_type=detected_offer,
                            property_type=detected_prop,
                            listing_url=f"{self.BASE_URL}{href}" if href.startswith('/') else href,
                            photos=[]
                        ))
        except Exception as e:
            logger.debug(f"[VillaAzScraper] HTML fetch notice: {e}")

        logger.info(f"[VillaAzScraper] Extracted {len(items)} listings.")
        return items
