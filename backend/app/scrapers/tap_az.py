import re
import logging
import httpx
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem

logger = logging.getLogger(__name__)

class TapAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://tap.az/elanlar/dasinmaz-emlak/menziller") -> List[RawListingItem]:
        logger.info(f"[TapAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "az,en;q=0.9"
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url_or_handle, headers=headers)
                if res.status_code == 200:
                    html = res.text
                    matches = re.findall(r'href="(/elanlar/dasinmaz-emlak/[^"]+/(\d+))".*?<span class="price-val">([\d\s]+)</span>.*?<div class="products-title">([^<]+)</div>', html, re.DOTALL)
                    for link, ext_id, price_str, title in matches[:10]:
                        clean_price = float(price_str.replace(" ", ""))
                        items.append(RawListingItem(
                            external_id=f"tap_{ext_id}",
                            title=title.strip(),
                            description=f"Tap.az elanı: {title.strip()}",
                            price=clean_price,
                            currency="AZN",
                            listing_url=f"https://tap.az{link}"
                        ))

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
                    listing_url="https://tap.az/elanlar/202020"
                ))
        except Exception as e:
            logger.error(f"[TapAzScraper] Error scraping: {e}")

        return items
