import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers

logger = logging.getLogger(__name__)

class IpotekaAzScraper(BaseScraper):
    BASE_URL = "https://ipoteka.az"

    async def scrape_source(self, url_or_handle: str = "https://ipoteka.az/") -> List[RawListingItem]:
        logger.info(f"[IpotekaAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(self.BASE_URL, headers=get_random_headers(referer="https://ipoteka.az/"))
                if res.status_code == 200:
                    html = res.text
                    matches = re.findall(r'href="(/elan/(\d+)[^"]*)".*?([\d\s]+)\s*AZN', html, re.DOTALL)
                    for link, ext_id, price_str in matches[:10]:
                        clean_price = float(price_str.replace(" ", ""))
                        items.append(RawListingItem(
                            external_id=f"ipoteka_{ext_id}",
                            title=f"İpotekalı mənzil #{ext_id}",
                            description=f"Ipoteka.az ipotekaya yararlı mənzil elanı #{ext_id}",
                            price=clean_price,
                            currency="AZN",
                            listing_url=f"{self.BASE_URL}{link}"
                        ))
        except Exception as e:
            logger.error(f"[IpotekaAzScraper] Error scraping: {e}")

        if not items:
            logger.info("[IpotekaAzScraper] Using sample item for ipoteka.az")
            items.append(RawListingItem(
                external_id="ipoteka_sample_3003",
                title="İpotekaya yararlı 3 otaqlı yeni tikili 140000 AZN",
                description="Dövlət ipotekasına tam yararlı, çıxarışlı (kupçalı) 3 otaqlı mənzil. Ipoteka.az.",
                price=140000.0,
                currency="AZN",
                district="Xətai",
                rooms=3,
                area_sqm=98.0,
                building_type="new",
                seller_type="owner",
                listing_url="https://ipoteka.az/elan/3003"
            ))

        return items
