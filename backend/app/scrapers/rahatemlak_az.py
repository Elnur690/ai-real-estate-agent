import re
import logging
import httpx
from typing import List
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers

logger = logging.getLogger(__name__)

class RahatEmlakAzScraper(BaseScraper):
    BASE_URL = "https://rahatemlak.az"
    LISTING_URL = "https://rahatemlak.az/alqi-satqi"

    async def scrape_source(self, url_or_handle: str = "https://rahatemlak.az/alqi-satqi") -> List[RawListingItem]:
        logger.info(f"[RahatEmlakAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(self.LISTING_URL, headers=get_random_headers(referer="https://rahatemlak.az/"))
                if res.status_code == 200:
                    html = res.text
                    matches = re.findall(r'href="(/elan/(\d+)[^"]*)".*?([\d\s]+)\s*AZN', html, re.DOTALL)
                    for link, ext_id, price_str in matches[:10]:
                        clean_price = float(price_str.replace(" ", ""))
                        items.append(RawListingItem(
                            external_id=f"rahatemlak_{ext_id}",
                            title=f"RahatEmlak Elan #{ext_id}",
                            description=f"RahatEmlak.az elan məlumatı #{ext_id}",
                            price=clean_price,
                            currency="AZN",
                            listing_url=f"{self.BASE_URL}{link}"
                        ))
        except Exception as e:
            logger.error(f"[RahatEmlakAzScraper] Error scraping: {e}")

        return items
