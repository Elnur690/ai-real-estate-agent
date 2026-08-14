import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers
from app.core.baku_locations import extract_baku_district, extract_metro_station

logger = logging.getLogger(__name__)

class YeniEmlakAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://yeniemlak.az/elan/axtar") -> List[RawListingItem]:
        logger.info(f"[YeniEmlakAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        target_url = "https://yeniemlak.az/elan/axtar" if ("yeniemlak.az" in url_or_handle and not url_or_handle.endswith("/elan/axtar")) else url_or_handle

        try:
            headers = get_random_headers(referer="https://yeniemlak.az/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(target_url, headers=headers)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", href=re.compile(r'/elan/(?:satilir|kiraye|gunluk)[^"]+-(\d+)'))
                    seen = set()

                    for a in links:
                        href = a['href']
                        m_id = re.search(r'-(\d+)$', href)
                        if not m_id:
                            continue
                        ext_id = m_id.group(1)
                        if ext_id in seen:
                            continue
                        seen.add(ext_id)

                        parent = a.find_parent("tr") or a.find_parent("table") or a.find_parent("div")
                        raw_text = parent.get_text(separator=" | ", strip=True) if parent else a.get_text(strip=True)

                        price_m = re.search(r'(\d+[\d\s]*)\s*(?:AZN|₼|manat)', raw_text, re.IGNORECASE) or re.search(r'qiymət\s*:?\s*(\d+[\d\s]*)', raw_text, re.IGNORECASE)
                        price = float(price_m.group(1).replace(" ", "")) if price_m else 100000.0

                        rooms_m = re.search(r'(\d+)\s*\|\s*otaq', raw_text) or re.search(r'(\d+)\s*otaqlı', raw_text)
                        rooms = int(rooms_m.group(1)) if rooms_m else None

                        area_m = re.search(r'([\d.]+)\s*\|\s*m2', raw_text) or re.search(r'([\d.]+)\s*m²', raw_text)
                        area = float(area_m.group(1)) if area_m else (rooms * 35.0 if rooms else 60.0)

                        district = extract_baku_district(raw_text) or extract_baku_district(href) or "Bakı"
                        metro = extract_metro_station(raw_text) or extract_metro_station(href)

                        bld_type = "new" if "yeni tikili" in raw_text.lower() else ("old" if "köhnə tikili" in raw_text.lower() else "new")
                        seller_type = "owner" if any(w in raw_text.lower() for w in ["sahibindən", "ev sahibi", "mülkiyyətçi"]) else "agency"

                        title = f"{rooms or ''} otaqlı mənzil, {district}" if rooms else f"Mənzil, {district}"

                        items.append(RawListingItem(
                            external_id=f"yeniemlak_{ext_id}",
                            title=title,
                            description=f"YeniEmlak elanı: {raw_text[:200]}",
                            price=price,
                            currency="AZN",
                            district=district,
                            metro_station=metro,
                            rooms=rooms,
                            area_sqm=area,
                            building_type=bld_type,
                            seller_type=seller_type,
                            listing_url=f"https://yeniemlak.az{href}"
                        ))
                        if len(items) >= 28:
                            break

        except Exception as e:
            logger.error(f"[YeniEmlakAzScraper] Error scraping: {e}")

        logger.info(f"[YeniEmlakAzScraper] Extracted {len(items)} listings.")
        return items
