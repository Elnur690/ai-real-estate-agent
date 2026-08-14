import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers
from app.core.baku_locations import extract_baku_district, extract_metro_station

logger = logging.getLogger(__name__)

class VillaAzScraper(BaseScraper):
    BASE_URL = "https://villa.az"

    async def scrape_source(self, url_or_handle: str = "https://villa.az/") -> List[RawListingItem]:
        logger.info(f"[VillaAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            headers = get_random_headers(referer="https://villa.az/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(self.BASE_URL, headers=headers)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", href=re.compile(r'/elan/|/item/|/villa/|\.html|/\d+'))
                    seen = set()

                    for a in links:
                        href = a['href']
                        m = re.search(r'(\d+)', href)
                        if not m:
                            continue
                        ext_id = m.group(1)
                        if ext_id in seen:
                            continue
                        seen.add(ext_id)

                        parent = a.find_parent("div") or a.find_parent("tr")
                        raw_text = parent.get_text(separator=" | ", strip=True) if parent else a.get_text(strip=True)

                        price_m = re.search(r'([\d\s]+)\s*AZN', raw_text) or re.search(r'([\d\s]+)\s*₼', raw_text) or re.search(r'([\d\s]+)\s*\$', raw_text)
                        price = float(price_m.group(1).replace(" ", "")) if price_m else 0.0

                        rooms_m = re.search(r'(\d+)\s*otaq', raw_text)
                        rooms = int(rooms_m.group(1)) if rooms_m else None

                        area_m = re.search(r'([\d.]+)\s*m²', raw_text) or re.search(r'([\d.]+)\s*sot', raw_text) or re.search(r'([\d.]+)\s*kv', raw_text)
                        area = float(area_m.group(1)) if area_m else None

                        district = extract_baku_district(raw_text) or extract_baku_district(href) 
                        metro = extract_metro_station(raw_text) or extract_metro_station(href)

                        title = f"{rooms or ''} otaqlı villa/bağ evi {int(price)} AZN ({district})" if rooms else f"Villa/Bağ evi {int(price)} AZN ({district})"

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
                            seller_type="owner",
                            listing_url=f"{self.BASE_URL}{href}" if href.startswith('/') else href
                        ))
                        if len(items) >= 20:
                            break

        except Exception as e:
            logger.error(f"[VillaAzScraper] Error scraping: {e}")

        logger.info(f"[VillaAzScraper] Extracted {len(items)} listings.")
        return items
