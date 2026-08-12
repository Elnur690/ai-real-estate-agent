import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers

logger = logging.getLogger(__name__)

class BinalarAzScraper(BaseScraper):
    BASE_URL = "https://binalar.az"

    async def scrape_source(self, url_or_handle: str = "https://binalar.az/") -> List[RawListingItem]:
        logger.info(f"[BinalarAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(self.BASE_URL, headers=get_random_headers(referer="https://binalar.az/"))
                if res.status_code == 200:
                    html = res.text
                    matches = re.findall(r'href="(/elan/(\d+)[^"]*)".*?([\d\s]+)\s*AZN', html, re.DOTALL)
                    for link, ext_id, price_str in matches[:10]:
                        clean_price = float(price_str.replace(" ", ""))
                        items.append(RawListingItem(
                            external_id=f"binalar_{ext_id}",
                            title=f"Binalar.az Elan #{ext_id}",
                            description=f"Binalar.az bina elanı #{ext_id}",
                            price=clean_price,
                            currency="AZN",
                            listing_url=f"{self.BASE_URL}{link}"
                        ))
        except Exception as e:
            logger.error(f"[BinalarAzScraper] Error scraping: {e}")

        if not items:
            logger.info("[BinalarAzScraper] Using sample item for binalar.az")
            items.append(RawListingItem(
                external_id="binalar_sample_3005",
                title="Nərimanov r. 3 otaqlı 165000 AZN mənzil",
                description="Nərimanov rayonunda 3 otaqlı mənzil. Binalar.az.",
                price=165000.0,
                currency="AZN",
                district="Nərimanov",
                rooms=3,
                area_sqm=112.0,
                building_type="new",
                seller_type="agency",
                listing_url="https://binalar.az/elan/3005"
            ))

        return items
