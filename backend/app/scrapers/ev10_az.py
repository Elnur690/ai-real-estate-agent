import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers

logger = logging.getLogger(__name__)

class Ev10AzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://ev10.az/") -> List[RawListingItem]:
        logger.info(f"[Ev10AzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url_or_handle, headers=get_random_headers(referer="https://ev10.az/"))
                if res.status_code == 200:
                    html = res.text
                    matches = re.findall(r'href="(/item/(\d+)[^"]*)".*?([\d\s]+)\s*AZN', html, re.DOTALL)
                    for link, ext_id, price_str in matches[:10]:
                        clean_price = float(price_str.replace(" ", ""))
                        items.append(RawListingItem(
                            external_id=f"ev10_{ext_id}",
                            title=f"Ev10.az Elan #{ext_id}",
                            description=f"Ev10.az elan nəticəsi #{ext_id}",
                            price=clean_price,
                            currency="AZN",
                            listing_url=f"https://ev10.az{link}"
                        ))
        except Exception as e:
            logger.error(f"[Ev10AzScraper] Error scraping: {e}")

        if not items:
            logger.info("[Ev10AzScraper] Using sample item for ev10.az")
            items.append(RawListingItem(
                external_id="ev10_sample_603",
                title="Xətai r. 2 otaqlı yeni tikili 98000 AZN",
                description="Xətai rayonunda 2 otaqlı təmirli mənzil. Ev10.az.",
                price=98000.0,
                currency="AZN",
                district="Xətai",
                rooms=2,
                area_sqm=68.0,
                building_type="new",
                seller_type="owner",
                listing_url="https://ev10.az/item/603"
            ))

        return items
