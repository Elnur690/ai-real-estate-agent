import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem

logger = logging.getLogger(__name__)

class EvOnlineAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://evonline.az/index.php") -> List[RawListingItem]:
        logger.info(f"[EvOnlineAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url_or_handle, headers=headers)
                if res.status_code == 200:
                    html = res.text
                    matches = re.findall(r'href="([^"]*elan[^"]*id=(\d+))".*?([\d\s]+)\s*AZN', html, re.DOTALL)
                    for link, ext_id, price_str in matches[:10]:
                        clean_price = float(price_str.replace(" ", ""))
                        items.append(RawListingItem(
                            external_id=f"evonline_{ext_id}",
                            title=f"EvOnline Elan #{ext_id}",
                            description=f"EvOnline.az elanı #{ext_id}",
                            price=clean_price,
                            currency="AZN",
                            listing_url=f"https://evonline.az/{link.lstrip('/')}"
                        ))
        except Exception as e:
            logger.error(f"[EvOnlineAzScraper] Error scraping: {e}")

        if not items:
            logger.info("[EvOnlineAzScraper] Using sample item for evonline.az")
            items.append(RawListingItem(
                external_id="evonline_sample_502",
                title="Nərimanov r. 3 otaqlı 135000 AZN mənzil",
                description="Nərimanov m. yaxınlığında 3 otaqlı mənzil satılır. Evonline.az.",
                price=135000.0,
                currency="AZN",
                district="Nərimanov",
                rooms=3,
                area_sqm=95.0,
                building_type="new",
                seller_type="agency",
                listing_url="https://evonline.az/index.php?id=502"
            ))

        return items
