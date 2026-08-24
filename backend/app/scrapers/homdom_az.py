import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers, safe_float
from app.core.baku_locations import (
    extract_baku_district, extract_metro_station, extract_baku_settlement,
    SETTLEMENT_TO_DISTRICT, METRO_TO_DISTRICT
)

logger = logging.getLogger(__name__)

class HomDomAzScraper(BaseScraper):
    BASE_URL = "https://homdom.az"

    async def scrape_source(self, url_or_handle: str = "https://homdom.az/offers/kiraye") -> List[RawListingItem]:
        logger.info(f"[HomDomAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            headers = get_random_headers(referer="https://homdom.az/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(self.BASE_URL, headers=headers)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", href=re.compile(r'/offers/|/offer/|/elan/'))
                    seen = set()

                    for a in links:
                        href = a.get('href', '')
                        if href in seen or href.endswith('/offers/') or href == '/':
                            continue
                        seen.add(href)

                        raw_text = a.get_text(separator=" | ", strip=True).replace('\xa0', ' ')
                        if not raw_text or len(raw_text) < 5:
                            continue
                        raw_lower = raw_text.lower()

                        district = extract_baku_district(raw_text) or extract_baku_district(href) 
                        settlement = extract_baku_settlement(raw_text) or extract_baku_settlement(href)
                        metro = extract_metro_station(raw_text) or extract_metro_station(href)

                        if not district:
                            if settlement and settlement in SETTLEMENT_TO_DISTRICT:
                                district = SETTLEMENT_TO_DISTRICT[settlement]
                            elif metro and metro in METRO_TO_DISTRICT:
                                district = METRO_TO_DISTRICT[metro]

                        price_m = re.search(r'([\d\s]+)\s*(?:AZN|₼|manat)', raw_text) or re.search(r'([\d\s]+)\s*\|\s*AZN', raw_text)
                        price = safe_float(price_m.group(1) if price_m else None, default=0.0)

                        rooms_m = re.search(r'(\d+)\s*otaq', raw_text)
                        rooms = int(rooms_m.group(1)) if rooms_m else 2

                        area = rooms * 35.0 if rooms else 65.0
                        ext_id = re.sub(r'[^a-zA-Z0-9]', '_', href.strip('/'))[:40]

                        is_rent = "kirayə" in raw_lower or "icarə" in raw_lower
                        offer_type = "rent" if is_rent else "sale"

                        if any(k in raw_lower for k in ["villa", "həyət", "bağ"]):
                            prop_type = "villa"
                        elif "ofis" in raw_lower:
                            prop_type = "office"
                        elif "obyekt" in raw_lower:
                            prop_type = "commercial"
                        elif "torpaq" in raw_lower:
                            prop_type = "land"
                        else:
                            prop_type = "apartment"

                        loc_label = settlement or metro or district or 'Bakı'
                        title = f"{rooms} otaqlı {prop_type.capitalize()} ({loc_label})"

                        # Extract card photo
                        card_photos = []
                        parent = a.find_parent("div") or a.find_parent("tr") or a
                        if parent:
                            img_el = parent.find("img")
                            if img_el:
                                src_val = img_el.get("src") or img_el.get("data-src")
                                if src_val and "http" in src_val:
                                    card_photos.append(src_val)
                                elif src_val and src_val.startswith("/"):
                                    card_photos.append(f"https://homdom.az{src_val}")

                        items.append(RawListingItem(
                            external_id=f"homdom_{ext_id}",
                            title=title,
                            description=f"HomDom.az elanı: {raw_text}",
                            price=price,
                            currency="AZN",
                            district=district,
                            metro_station=metro,
                            rooms=rooms,
                            area_sqm=area,
                            building_type="new",
                            seller_type="agency",
                            offer_type=offer_type,
                            property_type=prop_type,
                            listing_url=f"https://homdom.az/{href.lstrip('/')}",
                            photos=card_photos
                        ))
                        if len(items) >= 20:
                            break

        except Exception as e:
            logger.warning(f"[HomDomAzScraper] Error scraping: {e}")

        logger.info(f"[HomDomAzScraper] Extracted {len(items)} listings.")
        return items
