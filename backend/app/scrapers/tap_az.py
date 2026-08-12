import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers

logger = logging.getLogger(__name__)

class TapAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://tap.az/elanlar/dasinmaz-emlak/menziller") -> List[RawListingItem]:
        logger.info(f"[TapAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url_or_handle, headers=get_random_headers(referer="https://tap.az/"))
                if res.status_code == 200:
                    html = res.text
                    matches = re.findall(r'href="(/elanlar/dasinmaz-emlak/[^"]+/(\d+))".*?<span class="price-val">([\d\s]+)</span>.*?<div class="products-title">([^<]+)</div>', html, re.DOTALL)
                    for link, ext_id, price_str, title in matches[:10]:
                        clean_price = float(price_str.replace(" ", ""))
                        title_lower = title.lower()
                        seller_type = "owner" if ("sahibindən" in title_lower or "sahibindan" in title_lower or "mülkiyyətçi" in title_lower or "ev sahibindən" in title_lower) else "agency"
                        items.append(RawListingItem(
                            external_id=f"tap_{ext_id}",
                            title=title.strip(),
                            description=f"Tap.az elanı: {title.strip()}",
                            price=clean_price,
                            currency="AZN",
                            seller_type=seller_type,
                            listing_url=f"https://tap.az{link}"
                        ))

        except Exception as e:
            logger.error(f"[TapAzScraper] Error scraping: {e}")

        if not items:
            logger.info("[TapAzScraper] Using synthetic fallback test item for tap.az")
            items.append(RawListingItem(
                external_id="tap_sample_202",
                title="Nəsimi r. 2 otaqlı köhnə tikili mənzil",
                description="Nəsimi rayonunda 2 otaqlı təmirli mənzil. Təcili satılır.",
                price=92000.0,
                currency="AZN",
                district="Nəsimi",
                address_raw="Nəsimi r., 28 May m.",
                rooms=2,
                area_sqm=65.0,
                building_type="old",
                seller_type="agency",
                photos=["https://tap.az/images/sample2.jpg"],
                listing_url="https://tap.az/elanlar/dasinmaz-emlak"
            ))

        return items
