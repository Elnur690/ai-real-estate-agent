import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers
from app.core.baku_locations import extract_baku_district, extract_metro_station

logger = logging.getLogger(__name__)

class BinamAzScraper(BaseScraper):
    BASE_URL = "https://binam.az"

    async def scrape_source(self, url_or_handle: str = "https://binam.az/") -> List[RawListingItem]:
        logger.info(f"[BinamAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            headers = get_random_headers(referer="https://binam.az/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(self.BASE_URL, headers=headers)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", href=re.compile(r'/items/(\d+)'))
                    seen = set()

                    for a in links:
                        href = a['href']
                        m = re.search(r'/items/(\d+)', href)
                        if not m:
                            continue
                        ext_id = m.group(1)
                        if ext_id in seen:
                            continue
                        seen.add(ext_id)

                        parent = a.find_parent("div", class_=re.compile(r'item|card|col', re.I)) or a
                        raw_text = parent.get_text(separator=" | ", strip=True)

                        price_m = re.search(r'([\d\s]+)\s*AZN', raw_text) or re.search(r'([\d\s]+)\s*₼', raw_text)
                        price = float(price_m.group(1).replace(" ", "")) if price_m else 110000.0

                        rooms_m = re.search(r'(\d+)\s*otaq', raw_text)
                        rooms = int(rooms_m.group(1)) if rooms_m else None

                        area_m = re.search(r'([\d.]+)\s*m²', raw_text) or re.search(r'([\d.]+)\s*sot', raw_text) or re.search(r'([\d.]+)\s*kv', raw_text)
                        area = float(area_m.group(1)) if area_m else (rooms * 35.0 if rooms else 70.0)

                        district = extract_baku_district(raw_text) or extract_baku_district(href) or "Bakı"
                        metro = extract_metro_station(raw_text) or extract_metro_station(href)

                        title = f"{rooms or ''} otaqlı mənzil {int(price)} AZN ({district})" if rooms else f"Əmlak {int(price)} AZN ({district})"

                        items.append(RawListingItem(
                            external_id=f"binam_{ext_id}",
                            title=title,
                            description=f"Binam.az elanı: {raw_text[:200]}",
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
                        if len(items) >= 28:
                            break

        except Exception as e:
            logger.error(f"[BinamAzScraper] Error scraping: {e}")

        logger.info(f"[BinamAzScraper] Extracted {len(items)} listings.")
        return items
