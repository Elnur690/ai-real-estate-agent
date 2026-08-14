import re
import logging
import httpx
from bs4 import BeautifulSoup
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
            headers = get_random_headers(referer="https://tap.az/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url_or_handle, headers=headers)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    cards = soup.find_all("a", href=re.compile(r'/elanlar/dasinmaz-emlak/menziller/(\d+)'))
                    seen = set()

                    for a in cards:
                        href = a['href']
                        m_id = re.search(r'/elanlar/dasinmaz-emlak/menziller/(\d+)', href)
                        if not m_id:
                            continue
                        ext_id = m_id.group(1)
                        if ext_id in seen:
                            continue
                        seen.add(ext_id)

                        raw_text = a.get_text(separator=" | ", strip=True)
                        # Example: "63 500 | ₼ | 1-otaqlı yeni tikili, Xırdalan ş., 32 m² | Xırdalan,"
                        price_m = re.search(r'([\d\s]+)\s*\|\s*₼', raw_text) or re.search(r'([\d\s]+)\s*₼', raw_text)
                        price = float(price_m.group(1).replace(" ", "")) if price_m else 0.0

                        rooms_m = re.search(r'(\d+)\s*-\s*otaqlı', raw_text) or re.search(r'(\d+)\s*otaqlı', raw_text)
                        rooms = int(rooms_m.group(1)) if rooms_m else None
                        area_m = re.search(r'([\d.]+)\s*m²', raw_text)
                        area = float(area_m.group(1)) if area_m else None

                        district = extract_baku_district(raw_text) 
                        metro = extract_metro_station(raw_text)

                        title = re.sub(r'[\d\s]+\|\s*₼\s*\|?', '', raw_text).strip()
                        title = title.replace('|', '').strip()
                        if not title:
                            title = f"{rooms or ''} otaqlı mənzil ({district})"

                        seller_type = "owner" if any(w in raw_text.lower() for w in ["sahibindən", "sahibindan", "mülkiyyətçi", "ev sahibi"]) else "agency"
                        bld_type = "new" if "yeni tikili" in raw_text.lower() else ("old" if "köhnə tikili" in raw_text.lower() else "new")

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
                            building_type=bld_type,
                            seller_type=seller_type,
                            listing_url=f"https://tap.az{href}"
                        ))
                        if len(items) >= 28:
                            break

        except Exception as e:
            logger.error(f"[TapAzScraper] Error scraping: {e}")

        logger.info(f"[TapAzScraper] Extracted {len(items)} listings.")
        return items
