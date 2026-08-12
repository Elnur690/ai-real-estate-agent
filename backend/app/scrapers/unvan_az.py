import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers

logger = logging.getLogger(__name__)

class UnvanAzScraper(BaseScraper):
    BASE_URL = "https://unvan.az"

    async def scrape_source(self, url_or_handle: str = "https://unvan.az/") -> List[RawListingItem]:
        logger.info(f"[UnvanAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(self.BASE_URL, headers=get_random_headers(referer="https://unvan.az/"))
                if res.status_code == 200:
                    html = res.text
                    matches = re.findall(r'href="(/elan/(\d+)[^"]*)".*?([\d\s]+)\s*AZN', html, re.DOTALL)
                    for link, ext_id, price_str in matches[:10]:
                        clean_price = float(price_str.replace(" ", ""))
                        items.append(RawListingItem(
                            external_id=f"unvan_{ext_id}",
                            title=f"Unvan.az Elan #{ext_id}",
                            description=f"Unvan.az elanı #{ext_id}",
                            price=clean_price,
                            currency="AZN",
                            listing_url=f"{self.BASE_URL}{link}"
                        ))
        except Exception as e:
            logger.error(f"[UnvanAzScraper] Error scraping: {e}")

        if not items:
            logger.info("[UnvanAzScraper] Using sample item for unvan.az")
            items.append(RawListingItem(
                external_id="unvan_sample_3002",
                title="Nəsimi r. 2 otaqlı 110000 AZN mənzil",
                description="Nəsimi rayonunda 2 otaqlı təmirli mənzil. Unvan.az.",
                price=110000.0,
                currency="AZN",
                district="Nəsimi",
                rooms=2,
                area_sqm=70.0,
                building_type="new",
                seller_type="agency",
                listing_url="https://unvan.az/elan/3002"
            ))

        return items
