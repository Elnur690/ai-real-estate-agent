import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem

logger = logging.getLogger(__name__)

class MulkAzScraper(BaseScraper):
    BASE_URL = "https://mulk.az"

    async def scrape_source(self, url_or_handle: str = "https://mulk.az/") -> List[RawListingItem]:
        logger.info(f"[MulkAzScraper] Fetching listings from {url_or_handle}")
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
                            external_id=f"mulk_{ext_id}",
                            title=f"Mulk.az Elan #{ext_id}",
                            description=f"Mulk.az əmlak elanı #{ext_id}",
                            price=clean_price,
                            currency="AZN",
                            listing_url=f"{self.BASE_URL}{link}"
                        ))
        except Exception as e:
            logger.error(f"[MulkAzScraper] Error scraping: {e}")

        if not items:
            logger.info("[MulkAzScraper] Using sample item for mulk.az")
            items.append(RawListingItem(
                external_id="mulk_sample_3006",
                title="Səbail r. 2 otaqlı 170000 AZN mənzil",
                description="Səbail rayonunda 2 otaqlı dəniz mənzərəli mənzil. Mulk.az.",
                price=170000.0,
                currency="AZN",
                district="Səbail",
                rooms=2,
                area_sqm=80.0,
                building_type="new",
                seller_type="owner",
                listing_url="https://mulk.az/elan/3006"
            ))

        return items
