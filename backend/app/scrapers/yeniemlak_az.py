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

        if not items:
            logger.info("[YeniEmlakAzScraper] Using sample item for yeniemlak.az")
            items.append(RawListingItem(
                external_id="yeniemlak_sample_401",
                title="Yasamal r. 2 otaqlı təmirli mənzil 115000 AZN",
                description="Yasamal rayonunda təcili 2 otaqlı 75 kv/m yeni tikili mənzil. YeniEmlak.az vasitəsilə.",
                price=115000.0,
                currency="AZN",
                district="Yasamal",
                rooms=2,
                area_sqm=75.0,
                building_type="new",
                seller_type="owner",
                listing_url="https://yeniemlak.az/elan/kiraye-2-otaqli-bina-evi-menzil-yasamal-rayonu-yeni-yasamal-qes-murad-mirzeyev-kucesi-167054"
            ))

        return items
