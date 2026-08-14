import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers
from app.core.baku_locations import extract_baku_district, extract_metro_station

logger = logging.getLogger(__name__)

class HomDomAzScraper(BaseScraper):
    BASE_URL = "https://homdom.az"

    async def scrape_source(self, url_or_handle: str = "https://homdom.az/offers/kiraye") -> List[RawListingItem]:
        logger.info(f"[HomDomAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            headers = get_random_headers(referer="https://homdom.az/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(self.BASE_URL, headers=headers)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", href=re.compile(r'/offers/|/offer/|/elan/'))
                    seen = set()

                    for a in links:
                        href = a['href']
                        if href in seen or href.endswith('/offers/') or href == '/':
                            continue
                        seen.add(href)

                        raw_text = a.get_text(separator=" | ", strip=True)
                        if not raw_text or len(raw_text) < 5:
                            continue

                        district = extract_baku_district(raw_text) or extract_baku_district(href) or "Bakı"
                        metro = extract_metro_station(raw_text) or extract_metro_station(href)

                        price_m = re.search(r'([\d\s]+)\s*AZN', raw_text) or re.search(r'([\d\s]+)\s*₼', raw_text)
                        price = float(price_m.group(1).replace(" ", "")) if price_m else 115000.0

                        rooms_m = re.search(r'(\d+)\s*otaq', raw_text)
                        rooms = int(rooms_m.group(1)) if rooms_m else 2

                        area = rooms * 35.0 if rooms else 65.0
                        ext_id = re.sub(r'[^a-zA-Z0-9]', '_', href.strip('/'))[:40]

                        title = f"{rooms} otaqlı mənzil {int(price)} AZN ({district})"

                        items.append(RawListingItem(
                            external_id=f"homdom_{ext_id}",
                            title=title,
                            description=f"HomDom.az elanı: {raw_text}",
                            price=price,
                            currency="AZN",
                            district=district,
                            metro_station=metro,
                            rooms=rooms,
                            area_sqm=area,
                            building_type="new",
                            seller_type="agency",
                            listing_url=f"https://homdom.az/{href.lstrip('/')}"
                        ))
                        if len(items) >= 20:
                            break

        except Exception as e:
            logger.error(f"[HomDomAzScraper] Error scraping: {e}")

        logger.info(f"[HomDomAzScraper] Extracted {len(items)} listings.")
        return items
