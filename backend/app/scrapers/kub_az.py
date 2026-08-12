import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers

logger = logging.getLogger(__name__)

class KubAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://kub.az/") -> List[RawListingItem]:
        logger.info(f"[KubAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url_or_handle, headers=get_random_headers(referer="https://kub.az/"))
                if res.status_code == 200:
                    html = res.text
                    matches = re.findall(r'href="(/elan/(\d+)[^"]*)".*?([\d\s]+)\s*AZN', html, re.DOTALL)
                    for link, ext_id, price_str in matches[:10]:
                        clean_price = float(price_str.replace(" ", ""))
                        items.append(RawListingItem(
                            external_id=f"kub_{ext_id}",
                            title=f"Kub.az Elan #{ext_id}",
                            description=f"Kub.az elan nəticəsi #{ext_id}",
                            price=clean_price,
                            currency="AZN",
                            listing_url=f"https://kub.az{link}"
                        ))
        except Exception as e:
            logger.error(f"[KubAzScraper] Error scraping: {e}")

        return items
