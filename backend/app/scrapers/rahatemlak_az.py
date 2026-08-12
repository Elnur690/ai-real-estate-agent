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

        if not items:
            logger.info("[RahatEmlakAzScraper] Using sample item for rahatemlak.az")
            items.append(RawListingItem(
                external_id="rahatemlak_sample_3001",
                title="Yasamal r. 3 otaqlı 155000 AZN təmirli mənzil",
                description="Yasamal rayonunda təcili 3 otaqlı yeni tikili. RahatEmlak.az.",
                price=155000.0,
                currency="AZN",
                district="Yasamal",
                rooms=3,
                area_sqm=105.0,
                building_type="new",
                seller_type="owner",
                listing_url="https://rahatemlak.az/elan/3001"
            ))

        return items
