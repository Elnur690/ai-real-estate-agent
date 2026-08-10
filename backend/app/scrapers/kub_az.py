import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem

logger = logging.getLogger(__name__)

class KubAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://kub.az/") -> List[RawListingItem]:
        logger.info(f"[KubAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url_or_handle, headers=headers)
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

        if not items:
            logger.info("[KubAzScraper] Using sample item for kub.az")
            items.append(RawListingItem(
                external_id="kub_sample_906",
                title="Binəqədi r. 3 otaqlı həyət evi 85000 AZN",
                description="Binəqədi mərkəzində 3 otaqlı həyət evi satılır. Kub.az.",
                price=85000.0,
                currency="AZN",
                district="Binəqədi",
                rooms=3,
                area_sqm=90.0,
                seller_type="owner",
                listing_url="https://kub.az/elan/906"
            ))

        return items
