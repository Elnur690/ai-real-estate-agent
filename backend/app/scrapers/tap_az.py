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
                    links = re.findall(r'href="(/elanlar/dasinmaz-emlak/[^"]+/(\d+))"', html)
                    seen = set()
                    for link, ext_id in links:
                        if ext_id in seen:
                            continue
                        seen.add(ext_id)
                        
                        pos = html.find(link)
                        snippet = html[max(0, pos-200):min(len(html), pos+500)]
                        price_match = re.search(r'class="[^\"]*price[^\"]*"[^>]*>\s*([\d\s]+)\s*AZN', snippet) or re.search(r'([\d\s]+)\s*AZN', snippet)
                        title_match = re.search(r'class="[^\"]*title[^\"]*"[^>]*>([^<]+)<', snippet) or re.search(r'title="([^"]+)"', snippet)
                        
                        clean_price = float(price_match.group(1).replace(" ", "")) if price_match else 120000.0
                        title = title_match.group(1).strip() if title_match else f"Mənzil #{ext_id}"
                        title_lower = title.lower()
                        seller_type = "owner" if ("sahibindən" in title_lower or "sahibindan" in title_lower or "mülkiyyətçi" in title_lower or "ev sahibindən" in title_lower) else "agency"
                        
                        items.append(RawListingItem(
                            external_id=f"tap_{ext_id}",
                            title=title,
                            description=f"Tap.az elanı: {title}",
                            price=clean_price,
                            currency="AZN",
                            seller_type=seller_type,
                            listing_url=f"https://tap.az{link}"
                        ))
                        if len(items) >= 15:
                            break

        except Exception as e:
            logger.error(f"[TapAzScraper] Error scraping: {e}")

        return items
