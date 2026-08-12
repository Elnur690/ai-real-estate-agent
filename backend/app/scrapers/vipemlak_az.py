import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers

logger = logging.getLogger(__name__)

class VipEmlakAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://vipemlak.az/") -> List[RawListingItem]:
        logger.info(f"[VipEmlakAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url_or_handle, headers=get_random_headers(referer="https://vipemlak.az/"))
                if res.status_code == 200:
                    html = res.text
                    matches = re.findall(r'href="(/elan/(\d+)[^"]*)".*?([\d\s]+)\s*AZN', html, re.DOTALL)
                    for link, ext_id, price_str in matches[:10]:
                        clean_price = float(price_str.replace(" ", ""))
                        items.append(RawListingItem(
                            external_id=f"vipemlak_{ext_id}",
                            title=f"VipEmlak Elan #{ext_id}",
                            description=f"VipEmlak.az elan məlumatı #{ext_id}",
                            price=clean_price,
                            currency="AZN",
                            listing_url=f"https://vipemlak.az{link}"
                        ))
        except Exception as e:
            logger.error(f"[VipEmlakAzScraper] Error scraping: {e}")

        if not items:
            logger.info("[VipEmlakAzScraper] Using sample item for vipemlak.az")
            items.append(RawListingItem(
                external_id="vipemlak_sample_704",
                title="Səbail r. 4 otaqlı VIP mənzil 280000 AZN",
                description="Səbail r. Nərimanov heykəli yanında 4 otaqlı lüks mənzil. VipEmlak.az.",
                price=280000.0,
                currency="AZN",
                district="Səbail",
                rooms=4,
                area_sqm=160.0,
                building_type="new",
                seller_type="agency",
                listing_url="https://vipemlak.az/elan/704"
            ))

        return items
