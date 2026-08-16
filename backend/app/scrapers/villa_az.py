import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers
from app.core.baku_locations import (
    extract_baku_district, extract_metro_station, extract_baku_settlement,
    SETTLEMENT_TO_DISTRICT, METRO_TO_DISTRICT
)

logger = logging.getLogger(__name__)

class VillaAzScraper(BaseScraper):
    BASE_URL = "https://villa.az"

    async def scrape_source(self, url_or_handle: str = "https://villa.az/") -> List[RawListingItem]:
        logger.info(f"[VillaAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            headers = get_random_headers(referer="https://villa.az/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            headers["Accept-Language"] = "az,ru;q=0.9,en-US;q=0.8,en;q=0.7"
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                res = await client.get(self.BASE_URL, headers=headers)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", href=re.compile(r'/elan/|/item/|/villa/|\.html|/\d+'))
                    seen = set()

                    for a in links:
                        href = a.get('href', '')
                        m = re.search(r'(\d+)', href)
                        if not m:
                            continue
                        ext_id = m.group(1)
                        if ext_id in seen:
                            continue
                        seen.add(ext_id)

                        parent = a.find_parent("div") or a.find_parent("tr")
                        raw_text = parent.get_text(separator=" | ", strip=True).replace('\xa0', ' ') if parent else a.get_text(strip=True).replace('\xa0', ' ')
                        raw_lower = raw_text.lower()

                        price_m = re.search(r'([\d\s]+)\s*AZN', raw_text) or re.search(r'([\d\s]+)\s*₼', raw_text) or re.search(r'([\d\s]+)\s*\$', raw_text)
                        price = float(price_m.group(1).replace(" ", "")) if price_m else 0.0

                        rooms_m = re.search(r'(\d+)\s*otaq', raw_text)
                        rooms = int(rooms_m.group(1)) if rooms_m else None

                        area_m = re.search(r'([\d.]+)\s*m²', raw_text) or re.search(r'([\d.]+)\s*sot', raw_text) or re.search(r'([\d.]+)\s*kv', raw_text)
                        area = float(area_m.group(1)) if area_m else None

                        district = extract_baku_district(raw_text) or extract_baku_district(href) 
                        settlement = extract_baku_settlement(raw_text) or extract_baku_settlement(href)
                        metro = extract_metro_station(raw_text) or extract_metro_station(href)

                        if not district:
                            if settlement and settlement in SETTLEMENT_TO_DISTRICT:
                                district = SETTLEMENT_TO_DISTRICT[settlement]
                            elif metro and metro in METRO_TO_DISTRICT:
                                district = METRO_TO_DISTRICT[metro]

                        is_rent = "kirayə" in raw_lower or "icarə" in raw_lower or "gunluk" in raw_lower
                        offer_type = "rent" if is_rent else "sale"

                        loc_label = settlement or metro or district or 'Bakı'
                        title = f"{rooms or ''} otaqlı villa/bağ evi {int(price)} AZN ({loc_label})" if rooms else f"Villa/Bağ evi {int(price)} AZN ({loc_label})"

                        items.append(RawListingItem(
                            external_id=f"villa_{ext_id}",
                            title=title,
                            description=f"Villa.az elanı: {raw_text[:200]}",
                            price=price,
                            currency="AZN",
                            district=district,
                            metro_station=metro,
                            rooms=rooms,
                            area_sqm=area,
                            building_type="new",
                            seller_type="owner",
                            offer_type=offer_type,
                            property_type="villa",
                            listing_url=f"{self.BASE_URL}{href}" if href.startswith('/') else href
                        ))
                        if len(items) >= 20:
                            break

        except Exception as e:
            logger.warning(f"[VillaAzScraper] Source villa.az DNS/host unreachable: {e}")

        logger.info(f"[VillaAzScraper] Extracted {len(items)} listings.")
        return items
