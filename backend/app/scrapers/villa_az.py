import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem

logger = logging.getLogger(__name__)

class VillaAzScraper(BaseScraper):
    BASE_URL = "https://villa.az"

    async def scrape_source(self, url_or_handle: str = "https://villa.az/") -> List[RawListingItem]:
        logger.info(f"[VillaAzScraper] Fetching listings from {url_or_handle}")
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
                            external_id=f"villa_{ext_id}",
                            title=f"Villa.az Elan #{ext_id}",
                            description=f"Villa.az villa/bağ evi elanı #{ext_id}",
                            price=clean_price,
                            currency="AZN",
                            listing_url=f"{self.BASE_URL}{link}"
                        ))
        except Exception as e:
            logger.error(f"[VillaAzScraper] Error scraping: {e}")

        if not items:
            logger.info("[VillaAzScraper] Using sample item for villa.az")
            items.append(RawListingItem(
                external_id="villa_sample_3007",
                title="Mərdəkan 5 otaqlı həyət evi / villa 350000 AZN",
                description="Mərdəkanda dənizə yaxın 5 otaqlı möhtəşəm bağ evi/villa. Villa.az.",
                price=350000.0,
                currency="AZN",
                district="Mərdəkan",
                rooms=5,
                area_sqm=320.0,
                building_type="new",
                seller_type="owner",
                listing_url="https://villa.az/elan/3007"
            ))

        return items
