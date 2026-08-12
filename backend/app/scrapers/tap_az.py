import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers

from app.core.baku_locations import extract_baku_district, extract_metro_station

logger = logging.getLogger(__name__)

class TapAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://tap.az/elanlar/dasinmaz-emlak/menziller") -> List[RawListingItem]:
        logger.info(f"[TapAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url_or_handle, headers=get_random_headers(referer="https://tap.az/"))
                if res.status_code == 200:
                    html = res.text
                    item_matches = re.finditer(r'href="(/elanlar/dasinmaz-emlak/menziller/(\d+))"', html)
                    seen = set()

                    for m in item_matches:
                        ext_id = m.group(2)
                        if ext_id in seen:
                            continue
                        seen.add(ext_id)

                        pos = m.start()
                        card_text = html[pos:pos+2500]

                        title_m = re.search(r'data-testid="ad-card-title"[^>]*>([^<]+)<', card_text) or re.search(r'alt="([^"]+)"', card_text)
                        price_m = re.search(r'data-testid="ad-card-price"[^>]*>\s*([\d\s]+)', card_text) or re.search(r'([\d\s]+)<!-- -->\s*₼', card_text)

                        if title_m and price_m:
                            title = title_m.group(1).strip()
                            price = float(price_m.group(1).replace(" ", ""))
                            link = m.group(1)

                            district = extract_baku_district(title)
                            metro = extract_metro_station(title)

                            rooms_m = re.search(r'(\d+)\s*-\s*otaqlı', title) or re.search(r'(\d+)\s*otaqlı', title)
                            area_m = re.search(r'([\d.]+)\s*m²', title)

                            rooms = int(rooms_m.group(1)) if rooms_m else None
                            area = float(area_m.group(1)) if area_m else None

                            title_lower = title.lower()
                            seller_type = "owner" if ("sahibindən" in title_lower or "sahibindan" in title_lower or "mülkiyyətçi" in title_lower or "ev sahibindən" in title_lower) else "agency"

                            items.append(RawListingItem(
                                external_id=f"tap_{ext_id}",
                                title=title,
                                description=f"Tap.az elanı: {title}",
                                price=price,
                                currency="AZN",
                                district=district,
                                metro_station=metro,
                                rooms=rooms,
                                area_sqm=area,
                                seller_type=seller_type,
                                listing_url=f"https://tap.az{link}"
                            ))
                            if len(items) >= 15:
                                break

        except Exception as e:
            logger.error(f"[TapAzScraper] Error scraping: {e}")

        return items
