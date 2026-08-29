import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers, safe_float, safe_optional_float
from app.core.baku_locations import (
    extract_baku_district, extract_metro_station, extract_baku_settlement,
    SETTLEMENT_TO_DISTRICT, METRO_TO_DISTRICT
)

logger = logging.getLogger(__name__)

class VipEmlakAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://vipemlak.az/elanlar/") -> List[RawListingItem]:
        logger.info(f"[VipEmlakAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            headers = get_random_headers(referer="https://vipemlak.az/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url_or_handle, headers=headers)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", href=re.compile(r'/(?:[a-zA-Z0-9_-]+)-(\d+)\.html'))
                    seen = set()

                    for a in links:
                        href = a.get('href', '')
                        m = re.search(r'-(\d+)\.html', href)
                        if not m:
                            continue
                        ext_id = m.group(1)
                        if ext_id in seen:
                            continue
                        seen.add(ext_id)

                        parent = a.find_parent("div") or a.find_parent("tr")
                        raw_text = parent.get_text(separator=" | ", strip=True).replace('\xa0', ' ') if parent else a.get_text(strip=True).replace('\xa0', ' ')
                        raw_lower = raw_text.lower()

                        price_m = re.search(r'([\d\s]+)\s*(?:AZN|₼|manat)', raw_text) or re.search(r'([\d\s]+)\s*\|\s*AZN', raw_text)
                        price = safe_float(price_m.group(1) if price_m else None, default=0.0)

                        rooms_m = re.search(r'(\d+)\s*otaq', raw_text)
                        rooms = int(rooms_m.group(1)) if rooms_m else None

                        area_m = re.search(r'([\d.]+)\s*m²', raw_text) or re.search(r'([\d.]+)\s*kv', raw_text)
                        area = safe_optional_float(area_m.group(1) if area_m else None)

                        district = extract_baku_district(raw_text) or extract_baku_district(href) 
                        settlement = extract_baku_settlement(raw_text) or extract_baku_settlement(href)
                        metro = extract_metro_station(raw_text) or extract_metro_station(href)

                        if not district:
                            if settlement and settlement in SETTLEMENT_TO_DISTRICT:
                                district = SETTLEMENT_TO_DISTRICT[settlement]
                            elif metro and metro in METRO_TO_DISTRICT:
                                district = METRO_TO_DISTRICT[metro]

                        is_rent = "kirayə" in raw_lower or "icarə" in raw_lower
                        offer_type = "rent" if is_rent else "sale"

                        from app.core.property_classifier import classify_property_and_offer
                        detected_offer, detected_prop, detected_seller = classify_property_and_offer(
                            title="",
                            description=raw_text,
                            url=href,
                            raw_text=raw_text
                        )

                        prop_label_map = {
                            "apartment": "Mənzil",
                            "house": "Həyət evi / Villa",
                            "office": "Ofis",
                            "commercial": "Obyekt",
                            "land": "Torpaq sahəsi"
                        }
                        prop_name = prop_label_map.get(detected_prop, "Əmlak")
                        loc_label = settlement or metro or district or 'Bakı'
                        if detected_prop == "commercial":
                            title = f"{int(area)} m² Obyekt ({loc_label})" if area else f"Obyekt ({loc_label})"
                        elif detected_prop == "office":
                            title = f"{rooms} otaqlı Ofis ({loc_label})" if rooms else (f"{int(area)} m² Ofis ({loc_label})" if area else f"Ofis ({loc_label})")
                        elif detected_prop == "land":
                            title = f"{area} sot Torpaq ({loc_label})" if area else f"Torpaq sahəsi ({loc_label})"
                        elif rooms:
                            title = f"{rooms} otaqlı {prop_name} ({loc_label})"
                        else:
                            title = f"{prop_name} ({loc_label})"

                        bld_type = None if detected_prop in ["commercial", "office", "land"] else ("old" if "köhnə" in raw_lower else "new")

                        # Extract card photo
                        card_photos = []
                        if parent:
                            img_el = parent.find("img")
                            if img_el:
                                src_val = img_el.get("src") or img_el.get("data-src")
                                if src_val and "http" in src_val:
                                    card_photos.append(src_val)
                                elif src_val and src_val.startswith("/"):
                                    card_photos.append(f"https://vipemlak.az{src_val}")

                        items.append(RawListingItem(
                            external_id=f"vipemlak_{ext_id}",
                            title=title,
                            description=f"VipEmlak elanı: {raw_text[:200]}",
                            price=price,
                            currency="AZN",
                            district=district,
                            metro_station=metro,
                            rooms=rooms,
                            area_sqm=area,
                            building_type=bld_type,
                            seller_type=detected_seller,
                            offer_type=detected_offer,
                            property_type=detected_prop,
                            listing_url=f"https://vipemlak.az{href}" if href.startswith('/') else href,
                            photos=card_photos
                        ))
                        if len(items) >= 25:
                            break

        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as e:
            logger.debug(f"[VipEmlakAzScraper] Source vipemlak.az temporarily unreachable: {e}")
        except Exception as e:
            logger.warning(f"[VipEmlakAzScraper] Error scraping: {e}")

        logger.info(f"[VipEmlakAzScraper] Extracted {len(items)} listings.")
        return items
