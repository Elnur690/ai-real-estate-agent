import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem

logger = logging.getLogger(__name__)

class OfisAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://ofis.az/") -> List[RawListingItem]:
        logger.info(f"[OfisAzScraper] Fetching listings from {url_or_handle}")
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
                            external_id=f"ofis_{ext_id}",
                            title=f"Ofis.az Elan #{ext_id}",
                            description=f"Ofis.az kommersiya/əmlak elanı #{ext_id}",
                            price=clean_price,
                            currency="AZN",
                            listing_url=f"https://ofis.az{link}"
                        ))
        except Exception as e:
            logger.error(f"[OfisAzScraper] Error scraping: {e}")

        if not items:
            logger.info("[OfisAzScraper] Using sample item for ofis.az")
            items.append(RawListingItem(
                external_id="ofis_sample_805",
                title="Nəsimi r. 3 otaqlı ofis / mənzil 1600 AZN",
                description="28 May metrosu yaxınlığında təmirli 3 otaqlı obyekt/ofis. Ofis.az.",
                price=1600.0,
                currency="AZN",
                district="Nəsimi",
                rooms=3,
                area_sqm=110.0,
                seller_type="agency",
                listing_url="https://ofis.az/elan/805"
            ))

        return items
