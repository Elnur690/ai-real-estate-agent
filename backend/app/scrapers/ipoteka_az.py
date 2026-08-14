import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers
from app.core.baku_locations import extract_baku_district, extract_metro_station

logger = logging.getLogger(__name__)

class IpotekaAzScraper(BaseScraper):
    BASE_URL = "https://ipoteka.az"

    async def scrape_source(self, url_or_handle: str = "https://ipoteka.az/") -> List[RawListingItem]:
        logger.info(f"[IpotekaAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(self.BASE_URL, headers=get_random_headers(referer="https://ipoteka.az/"))
                if res.status_code == 200:
                    html = res.text
                    matches = re.findall(r'href="(/elan/(\d+)-([^"]+))"', html)
                    seen = set()
                    for link, ext_id, slug in matches[:15]:
                        if ext_id in seen:
                            continue
                        seen.add(ext_id)

                        pos = html.find(link)
                        snippet = html[pos:pos+1000] if pos != -1 else ""
                        price_match = re.search(r'([\d\s]+)\s*AZN', snippet)
                        clean_price = float(price_match.group(1).replace(" ", "")) if price_match else 0.0

                        clean_slug = slug.replace("-", " ")
                        district = extract_baku_district(clean_slug) 
                        metro = extract_metro_station(clean_slug)

                        rooms_m = re.search(r'(\d+)\s*otaq', clean_slug) or re.search(r'(\d+)\s*otaq', snippet)
                        rooms = int(rooms_m.group(1)) if rooms_m else None
                        area_m = re.search(r'([\d.]+)\s*m²', snippet) or re.search(r'([\d.]+)\s*kv', snippet)
                        area = float(area_m.group(1)) if area_m else None

                        title = f"{rooms or ''} otaqlı ipotekalı mənzil ({district})" if rooms else f"İpotekalı mənzil ({district})"

                        items.append(RawListingItem(
                            external_id=f"ipoteka_{ext_id}",
                            title=title,
                            description=f"Ipoteka.az ipotekaya yararlı mənzil: {clean_slug}",
                            price=clean_price,
                            currency="AZN",
                            district=district,
                            metro_station=metro,
                            rooms=rooms,
                            area_sqm=area,
                            building_type="new",
                            seller_type="owner",
                            listing_url=f"{self.BASE_URL}{link}"
                        ))
        except Exception as e:
            logger.error(f"[IpotekaAzScraper] Error scraping: {e}")

        logger.info(f"[IpotekaAzScraper] Extracted {len(items)} listings.")
        return items
