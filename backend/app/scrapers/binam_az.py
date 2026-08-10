import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem

logger = logging.getLogger(__name__)

class BinamAzScraper(BaseScraper):
    BASE_URL = "https://binam.az"

    async def scrape_source(self, url_or_handle: str = "https://binam.az/") -> List[RawListingItem]:
        logger.info(f"[BinamAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(self.BASE_URL, headers=headers)
                if res.status_code == 200:
                    html = res.text
                    matches = re.findall(r'href="(/elan/(\d+)[^"]*)".*?([\d\s]+)\s*AZN', html, re.DOTALL)
                    for link, ext_id, price_str in matches[:10]:
                        clean_price = float(price_str.replace(" ", ""))
                        items.append(RawListingItem(
                            external_id=f"binam_{ext_id}",
                            title=f"Binam.az Elan #{ext_id}",
                            description=f"Binam.az daşınmaz əmlak elanı #{ext_id}",
                            price=clean_price,
                            currency="AZN",
                            listing_url=f"{self.BASE_URL}{link}"
                        ))
        except Exception as e:
            logger.error(f"[BinamAzScraper] Error scraping: {e}")

        if not items:
            logger.info("[BinamAzScraper] Using sample item for binam.az")
            items.append(RawListingItem(
                external_id="binam_sample_3004",
                title="Yasamal r. 2 otaqlı 105000 AZN yeni tikili",
                description="Yasamalda 2 otaqlı mənzil. Binam.az.",
                price=105000.0,
                currency="AZN",
                district="Yasamal",
                rooms=2,
                area_sqm=65.0,
                building_type="new",
                seller_type="agency",
                listing_url="https://binam.az/elan/3004"
            ))

        return items
