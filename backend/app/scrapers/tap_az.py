import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers
from app.core.baku_locations import (
    extract_baku_district, extract_metro_station, extract_baku_settlement,
    SETTLEMENT_TO_DISTRICT, METRO_TO_DISTRICT
)

logger = logging.getLogger(__name__)

class TapAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://tap.az/elanlar/dasinmaz-emlak") -> List[RawListingItem]:
        logger.info(f"[TapAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []
        seen = set()

        urls_to_fetch = [
            "https://tap.az/elanlar/dasinmaz-emlak/villalar-bag-evleri",
            "https://tap.az/elanlar/dasinmaz-emlak/menziller",
            "https://tap.az/elanlar/dasinmaz-emlak/ofisler",
            "https://tap.az/elanlar/dasinmaz-emlak"
        ] if ("tap.az/elanlar/dasinmaz-emlak" in url_or_handle) else [url_or_handle]

        headers = get_random_headers(referer="https://tap.az/")
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        headers["Accept-Language"] = "az,ru;q=0.9,en-US;q=0.8,en;q=0.7"

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for target_url in urls_to_fetch:
                try:
                    res = await client.get(target_url, headers=headers)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.text, "html.parser")
                        cards = soup.find_all("a", href=re.compile(r'/elanlar/dasinmaz-emlak/(?:menziller|heyet-evleri-baglar-villalar|ofisler|obyektler|torpaq)/(\d+)'))
                        if not cards:
                            cards = soup.find_all("a", href=re.compile(r'/elanlar/dasinmaz-emlak/[^"]+/(\d+)'))

                        for a in cards:
                            href = a.get('href', '')
                            m_id = re.search(r'/elanlar/dasinmaz-emlak/[^"]+/(\d+)', href)
                            if not m_id:
                                continue
                            ext_id = m_id.group(1)
                            if ext_id in seen:
                                continue
                            seen.add(ext_id)

                            raw_text = a.get_text(separator=" | ", strip=True).replace('\xa0', ' ')
                            raw_lower = raw_text.lower()

                            price_m = re.search(r'([\d\s]+)\s*\|\s*₼', raw_text) or re.search(r'([\d\s]+)\s*₼', raw_text) or re.search(r'([\d\s]+)\s*AZN', raw_text)
                            price = float(price_m.group(1).replace(" ", "")) if price_m else 0.0

                            rooms_m = re.search(r'(\d+)\s*-\s*otaqlı', raw_text) or re.search(r'(\d+)\s*otaqlı', raw_text)
                            rooms = int(rooms_m.group(1)) if rooms_m else None
                            area_m = re.search(r'([\d.]+)\s*m²', raw_text)
                            area = float(area_m.group(1)) if area_m else None

                            district = extract_baku_district(raw_text) 
                            settlement = extract_baku_settlement(raw_text)
                            metro = extract_metro_station(raw_text)

                            if not district:
                                if settlement and settlement in SETTLEMENT_TO_DISTRICT:
                                    district = SETTLEMENT_TO_DISTRICT[settlement]
                                elif metro and metro in METRO_TO_DISTRICT:
                                    district = METRO_TO_DISTRICT[metro]

                            is_rent = "kiraye" in href or "aylıq" in raw_lower or "icarə" in raw_lower or "/ ay" in raw_text
                            offer_type = "rent" if is_rent else "sale"

                            if "villa" in href or any(k in raw_lower for k in ["villa", "həyət evi", "heyet evi", "bağ evi", "bag evi"]):
                                prop_type = "villa"
                            elif "ofis" in href or any(k in raw_lower for k in ["ofis", "plaza"]):
                                prop_type = "office"
                            elif "obyekt" in href or "obyekt" in raw_lower:
                                prop_type = "commercial"
                            elif "torpaq" in href or "torpaq" in raw_lower:
                                prop_type = "land"
                            else:
                                prop_type = "apartment"

                            title = re.sub(r'[\d\s]+\|\s*₼\s*\|?', '', raw_text).strip().replace('|', '').strip()
                            if not title:
                                title = f"{rooms or ''} otaqlı {prop_type.capitalize()} ({district or settlement or 'Bakı'})"

                            seller_type = "agency" if any(w in raw_lower for w in ["agentlik", "vasitəçi", "makler", "şirkət"]) else "owner"
                            bld_type = "new" if "yeni tikili" in raw_lower else ("old" if "köhnə tikili" in raw_lower else "new")

                            items.append(RawListingItem(
                                external_id=f"tap_{ext_id}",
                                title=title,
                                description=f"Tap.az: {raw_text}",
                                price=price,
                                currency="AZN",
                                district=district,
                                metro_station=metro,
                                rooms=rooms,
                                area_sqm=area,
                                building_type=bld_type,
                                seller_type=seller_type,
                                offer_type=offer_type,
                                property_type=prop_type,
                                listing_url=f"https://tap.az{href}"
                            ))
                except Exception as e:
                    logger.warning(f"[TapAzScraper] Error fetching from {target_url}: {e}")

        logger.info(f"[TapAzScraper] Extracted {len(items)} listings.")
        return items
