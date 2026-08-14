import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers
from app.core.baku_locations import extract_baku_district, extract_metro_station

logger = logging.getLogger(__name__)

class BinaAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://bina.az/items?leased=false&category_id=1&city_id=1") -> List[RawListingItem]:
        logger.info(f"[BinaAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        # Ensure we hit the direct listings collection URL
        target_url = "https://bina.az/items?leased=false&category_id=1&city_id=1" if ("alqi-satqi" in url_or_handle or url_or_handle.endswith("bina.az/")) else url_or_handle

        try:
            headers = get_random_headers(referer="https://bina.az/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(target_url, headers=headers)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    cards = soup.find_all("div", class_=re.compile(r'items-i|items_i|card_item|item-card|vi_item'))
                    seen = set()

                    for c in cards:
                        link = c.find("a", href=re.compile(r'/items/(\d+)'))
                        if not link:
                            continue
                        href = link['href']
                        m_id = re.search(r'/items/(\d+)', href)
                        if not m_id:
                            continue
                        ext_id = m_id.group(1)
                        if ext_id in seen:
                            continue
                        seen.add(ext_id)

                        raw_text = c.get_text(separator=" | ", strip=True)
                        # Text example: "165 000 | AZN | Zığ q. | 4 otaqlı | 158 m² | Bakı, dünən 15:39"
                        price_m = re.search(r'([\d\s]+)\s*\|\s*AZN', raw_text) or re.search(r'([\d\s]+)\s*AZN', raw_text)
                        price = float(price_m.group(1).replace(" ", "")) if price_m else 0.0

                        rooms_m = re.search(r'(\d+)\s*otaqlı', raw_text)
                        rooms = int(rooms_m.group(1)) if rooms_m else None
                        area_m = re.search(r'([\d.]+)\s*m²', raw_text)
                        area = float(area_m.group(1)) if area_m else (rooms * 35.0 if rooms else 60.0)

                        district = extract_baku_district(raw_text) or "Bakı"
                        metro = extract_metro_station(raw_text)

                        seller_type = "agency" if "agentlik" in raw_text.lower() else "owner"
                        bld_type = "new" if "yeni tikili" in raw_text.lower() else ("old" if "köhnə tikili" in raw_text.lower() else "new")

                        title = f"{rooms or ''} otaqlı mənzil {int(price)} AZN ({district})" if rooms else f"Mənzil {int(price)} AZN ({district})"

                        items.append(RawListingItem(
                            external_id=f"bina_{ext_id}",
                            title=title,
                            description=f"Bina.az elanı: {raw_text}",
                            price=price,
                            currency="AZN",
                            district=district,
                            metro_station=metro,
                            rooms=rooms,
                            area_sqm=area,
                            building_type=bld_type,
                            seller_type=seller_type,
                            listing_url=f"https://bina.az{href}"
                        ))
                        if len(items) >= 28:
                            break

        except Exception as e:
            logger.error(f"[BinaAzScraper] Error scraping: {e}")

        logger.info(f"[BinaAzScraper] Extracted {len(items)} listings.")
        return items
