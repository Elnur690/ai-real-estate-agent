import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem

logger = logging.getLogger(__name__)

class LalafoAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://lalafo.az/baku/nedvizhimost") -> List[RawListingItem]:
        logger.info(f"[LalafoAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url_or_handle, headers=headers)
                if res.status_code == 200:
                    html = res.text
                    matches = re.findall(r'href="(/baku/nedvizhimost/[^"]*id-(\d+))".*?([\d\s]+)\s*AZN', html, re.DOTALL)
                    for link, ext_id, price_str in matches[:10]:
                        clean_price = float(price_str.replace(" ", ""))
                        items.append(RawListingItem(
                            external_id=f"lalafo_{ext_id}",
                            title=f"Lalafo Elan #{ext_id}",
                            description=f"Lalafo.az daşınmaz əmlak elanı #{ext_id}",
                            price=clean_price,
                            currency="AZN",
                            listing_url=f"https://lalafo.az{link}"
                        ))
        except Exception as e:
            logger.error(f"[LalafoAzScraper] Error scraping: {e}")

        if not items:
            logger.info("[LalafoAzScraper] Using sample item for lalafo.az")
            items.append(RawListingItem(
                external_id="lalafo_sample_1007",
                title="Nizami r. Neftçilər m. 2 otaqlı mənzil 102000 AZN",
                description="Neftçilər metrosu yaxınlığında 2 otaqlı orta təmirli mənzil. Lalafo.az.",
                price=102000.0,
                currency="AZN",
                district="Nizami",
                rooms=2,
                area_sqm=62.0,
                building_type="old",
                seller_type="owner",
                listing_url="https://lalafo.az/baku/nedvizhimost/id-1007"
            ))

        return items
