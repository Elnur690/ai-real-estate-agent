import re
import logging
import urllib.parse
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

class KubAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://kub.az/") -> List[RawListingItem]:
        logger.info(f"[KubAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        target_urls = [
            url_or_handle,
            "https://kub.az/1-otaqli-yeni-tikili-evler-satilir",
            "https://kub.az/2-otaqli-yeni-tikili-evler-satilir",
            "https://kub.az/3-otaqli-yeni-tikili-evler-satilir"
        ] if url_or_handle == "https://kub.az/" else [url_or_handle]

        seen = set()
        try:
            headers = get_random_headers(referer="https://kub.az/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                for target_url in target_urls:
                    try:
                        res = await client.get(target_url, headers=headers)
                        if res.status_code == 200:
                            soup = BeautifulSoup(res.text, "html.parser")
                            links = soup.find_all("a", href=re.compile(r'/elan/|-id-(\d+)'))

                            for a in links:
                                href = a.get('href', '')
                                unquoted_href = urllib.parse.unquote(href)
                                m = re.search(r'-id-(\d+)', href) or re.search(r'/elan/.*?(\d+)', href) or re.search(r'(\d+)', href)
                                if not m:
                                    continue
                                ext_id = m.group(1)
                                if ext_id in seen:
                                    continue
                                seen.add(ext_id)

                                parent = a.find_parent("div") or a.find_parent("tr")
                                raw_text = parent.get_text(separator=" | ", strip=True).replace('\xa0', ' ') if parent else a.get_text(strip=True).replace('\xa0', ' ')
                                combined_text = f"{unquoted_href} | {raw_text}"
                                raw_lower = combined_text.lower()

                                price_m = re.search(r'(?i)([\d\s]+)\s*(?:AZN|₼|manat|Azn|\$)', combined_text) or re.search(r'([\d\s]+)\s*\|\s*AZN', combined_text) or re.search(r'-(\d{4,9})\s*azn', unquoted_href, re.I)
                                price = safe_float(price_m.group(1) if price_m else None, default=0.0)

                                rooms_m = re.search(r'(\d+)\s*otaq', combined_text)
                                rooms = int(rooms_m.group(1)) if rooms_m else None

                                area_m = re.search(r'([\d.]+)\s*m²', combined_text) or re.search(r'([\d.]+)\s*m2', combined_text) or re.search(r'([\d.]+)\s*kv', combined_text)
                                area = safe_optional_float(area_m.group(1) if area_m else None)

                                floor_m = re.search(r'(\d+)\s*Mərtəbə', unquoted_href, re.I) or re.search(r'(\d+)\s*/\s*(\d+)', combined_text)
                                floor = int(floor_m.group(1)) if floor_m else None

                                district = extract_baku_district(combined_text) or extract_baku_district(unquoted_href) 
                                settlement = extract_baku_settlement(combined_text) or extract_baku_settlement(unquoted_href)
                                metro = extract_metro_station(combined_text) or extract_metro_station(unquoted_href)

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
                                            card_photos.append(f"https://kub.az{src_val}")

                                items.append(RawListingItem(
                                    external_id=f"kub_{ext_id}",
                                    title=title,
                                    description=f"Kub.az elanı: {raw_text[:200]}",
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
                                    listing_url=f"https://kub.az{href}" if href.startswith('/') else href,
                                    photos=card_photos
                                ))
                                if len(items) >= 30:
                                    break
                    except Exception as loop_err:
                        logger.debug(f"[KubAzScraper] Error fetching {target_url}: {loop_err}")

        except Exception as e:
            logger.info(f"[KubAzScraper] Kub.az scrape status: {e}")

        logger.info(f"[KubAzScraper] Extracted {len(items)} listings.")
        return items
