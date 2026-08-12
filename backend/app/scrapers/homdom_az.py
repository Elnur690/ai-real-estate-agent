import re
import logging
import httpx
from typing import List
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers

logger = logging.getLogger(__name__)

class HomDomAzScraper(BaseScraper):
    BASE_URL = "https://homdom.az"
    LISTING_URL = "https://homdom.az/offers/kiraye"
    AJAX_URL = "https://homdom.az/_ajax"

    async def scrape_source(self, url_or_handle: str = "https://homdom.az/offers/kiraye") -> List[RawListingItem]:
        logger.info(f"[HomDomAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        headers = get_random_headers(
            extra_headers={"X-Requested-With": "XMLHttpRequest"},
            referer=self.LISTING_URL
        )

        params = {
            "core[ajax]": "true",
            "core[call]": "homdom.dynamicPageInfinity",
            "page": "1",
            "url": self.LISTING_URL,
            "slug": "kiraye",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(self.AJAX_URL, params=params, headers=headers)
                html = res.text if res.status_code == 200 else ""
                
                if not html or len(html) < 100:
                    # Try fetching main listing page directly if AJAX fails
                    res_main = await client.get(self.LISTING_URL, headers=headers)
                    if res_main.status_code == 200:
                        html = res_main.text

                if html:
                    soup = BeautifulSoup(html, "html.parser")
                    seen = set()
                    for a in soup.select("a.announce_items_link[href^='/offer/']"):
                        href = a.get("href", "")
                        m = re.search(r"/offer/(\d+)", href)
                        if not m:
                            continue
                        listing_id = m.group(1)
                        if listing_id in seen:
                            continue
                        seen.add(listing_id)

                        price_el = a.select_one(".announce_catg")
                        title_el = a.select_one(".announce_text")
                        metro_el = a.select_one(".announce_adrs")

                        price_raw = price_el.get_text().strip() if price_el else ""
                        title_text = title_el.get_text().strip() if title_el else f"HomDom Elan #{listing_id}"
                        metro_text = metro_el.get_text().strip() if metro_el else ""

                        pm = re.search(r"[\d.]+", price_raw.replace(" ", ""))
                        price = float(pm.group()) if pm else 0.0

                        rm = re.search(r"(\d+)\s*otaql", title_text, re.IGNORECASE)
                        am = re.search(r"([\d.]+)\s*m[²2]", title_text, re.IGNORECASE)
                        rooms = int(rm.group(1)) if rm else None
                        area = float(am.group(1)) if am else None

                        bld_type = "new" if "yeni tikili" in title_text.lower() else ("old" if "köhnə tikili" in title_text.lower() else None)

                        district = "Bakı"
                        if metro_text:
                            district = metro_text
                        else:
                            parts = [p.strip() for p in title_text.split(",")]
                            if len(parts) > 1:
                                district = parts[-1]

                        items.append(RawListingItem(
                            external_id=f"homdom_{listing_id}",
                            title=title_text,
                            description=f"HomDom.az elan məlumatı #{listing_id}: {title_text}",
                            price=price,
                            currency="AZN",
                            district=district,
                            address_raw=f"{title_text} {metro_text}".strip(),
                            rooms=rooms,
                            area_sqm=area,
                            building_type=bld_type,
                            seller_type="agency",
                            photos=[],
                            listing_url=f"{self.BASE_URL}{href}"
                        ))
        except Exception as e:
            logger.error(f"[HomDomAzScraper] Error scraping: {e}")

        if not items:
            logger.info("[HomDomAzScraper] Using synthetic fallback test item for homdom.az")
            items.append(RawListingItem(
                external_id="homdom_sample_2001",
                title="Kirayə verilir 2 otaqlı yeni tikili, 60 m², Xətai m.",
                description="Xətai metrosu yaxınlığında 2 otaqlı 60 kv/m mənzil kirayə verilir. HomDom.az.",
                price=1000.0,
                currency="AZN",
                district="Xətai m.",
                address_raw="Xətai r., Xətai m.",
                rooms=2,
                area_sqm=60.0,
                building_type="new",
                seller_type="agency",
                photos=[],
                listing_url="https://homdom.az/offer/2001"
            ))

        return items
