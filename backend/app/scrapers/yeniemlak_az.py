import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers

logger = logging.getLogger(__name__)

class YeniEmlakAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://yeniemlak.az/") -> List[RawListingItem]:
        logger.info(f"[YeniEmlakAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url_or_handle, headers=get_random_headers(referer="https://yeniemlak.az/"))
                if res.status_code == 200:
                    html = res.text
                    matches = re.findall(r'href="(/elan/([^"]+))".*?<span class="price">([\d\s]+)\s*AZN</span>.*?<div class="title">([^<]+)</div>', html, re.DOTALL)
                    for link, ext_id, price_str, title in matches[:10]:
                        clean_price = float(price_str.replace(" ", ""))
                        items.append(RawListingItem(
                            external_id=f"yeniemlak_{ext_id}",
                            title=title.strip(),
                            description=f"YeniEmlak.az elanı: {title.strip()}",
                            price=clean_price,
                            currency="AZN",
                            listing_url=f"https://yeniemlak.az{link}"
                        ))
        except Exception as e:
            logger.error(f"[YeniEmlakAzScraper] Error scraping: {e}")

        return items
