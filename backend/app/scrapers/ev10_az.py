import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers, safe_float, safe_optional_float
from app.core.baku_locations import (
    extract_baku_district, extract_metro_station, extract_baku_settlement,
    SETTLEMENT_TO_DISTRICT, METRO_TO_DISTRICT, extract_az_phone
)

logger = logging.getLogger(__name__)

class Ev10AzScraper(BaseScraper):
    @staticmethod
    async def fetch_item_details(item_id_or_url: str) -> dict:
        """Fetches full item details including phone number and exact price from Ev10.az."""
        m = re.search(r'(\d+)', str(item_id_or_url))
        if not m:
            return {}
        ext_id = m.group(1)
        url = f"https://ev10.az/posting/{ext_id}"
        headers = get_random_headers(referer="https://ev10.az/")

        try:
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                res = await client.get(url, headers=headers)
                if res.status_code != 200:
                    return {}

                soup = BeautifulSoup(res.text, "html.parser")
                page_text = soup.get_text(separator=" ", strip=True).replace('\xa0', ' ')
                
                price_m = re.search(r'(?i)([\d,.\s]+)\s*AZN', page_text)
                price = safe_float(price_m.group(1).replace(",", "") if price_m else None, default=0.0)

                phone_found = extract_az_phone(page_text)
                phone = phone_found[0] if phone_found else None

                desc_el = soup.find(class_=re.compile(r'description|details|about|content', re.I)) or soup.find("article")
                desc = desc_el.get_text(separator=" ", strip=True) if desc_el else page_text[:400]

                return {
                    "price": price,
                    "phone_number": phone,
                    "full_description": desc
                }
        except Exception as e:
            logger.debug(f"[Ev10AzScraper] Error fetching detail for #{ext_id}: {e}")
            return {}

    async def scrape_source(self, url_or_handle: str = "https://ev10.az/son-elanlar") -> List[RawListingItem]:
        logger.info(f"[Ev10AzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        target_urls = [
            url_or_handle,
            "https://ev10.az/alqi-satqi",
            "https://ev10.az/kiraye"
        ] if url_or_handle == "https://ev10.az/son-elanlar" else [url_or_handle]

        seen = set()
        try:
            headers = get_random_headers(referer="https://ev10.az/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                for target_url in target_urls:
                    try:
                        res = await client.get(target_url, headers=headers)
                        if res.status_code == 200:
                            soup = BeautifulSoup(res.text, "html.parser")
                            links = soup.find_all("a", href=re.compile(r'/posting/(\d+)'))

                            for a in links:
                                href = a.get('href', '')
                                m = re.search(r'/posting/(\d+)', href)
                                if not m:
                                    continue
                                ext_id = m.group(1)
                                if ext_id in seen:
                                    continue

                                img_el = a.find("img")
                                alt_text = img_el.get("alt", "").strip() if img_el else ""
                                if not alt_text:
                                    continue

                                seen.add(ext_id)
                                raw_text = alt_text.replace('\xa0', ' ').replace('\n', ' ')
                                raw_lower = raw_text.lower()

                                rooms_m = re.search(r'(\d+)\s*otaql', raw_text) or re.search(r'(\d+)\s*otaq', raw_text)
                                rooms = int(rooms_m.group(1)) if rooms_m else None

                                area_m = re.search(r'([\d.]+)\s*m²', raw_text) or re.search(r'([\d.]+)\s*kv', raw_text)
                                area = safe_optional_float(area_m.group(1) if area_m else None)

                                land_m = re.search(r'([\d.]+)\s*sot', raw_text)
                                land_sot = safe_optional_float(land_m.group(1) if land_m else None)

                                district = extract_baku_district(raw_text)
                                settlement = extract_baku_settlement(raw_text)
                                metro = extract_metro_station(raw_text)

                                if not district:
                                    if settlement and settlement in SETTLEMENT_TO_DISTRICT:
                                        district = SETTLEMENT_TO_DISTRICT[settlement]
                                    elif metro and metro in METRO_TO_DISTRICT:
                                        district = METRO_TO_DISTRICT[metro]

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
                                    title = f"{land_sot or area} sot Torpaq ({loc_label})" if (land_sot or area) else f"Torpaq sahəsi ({loc_label})"
                                elif rooms:
                                    title = f"{rooms} otaqlı {prop_name} ({loc_label})"
                                else:
                                    title = f"{prop_name} ({loc_label})"

                                bld_type = "old" if "köhnə" in raw_lower else ("new" if "yeni" in raw_lower else None)

                                card_photos = []
                                if img_el:
                                    src_val = img_el.get("src") or img_el.get("data-src")
                                    if src_val and "http" in src_val:
                                        card_photos.append(src_val)

                                clean_url = href if href.startswith("http") else f"https://ev10.az{href if href.startswith('/') else '/' + href}"
                                items.append(RawListingItem(
                                    external_id=f"ev10_{ext_id}",
                                    title=title,
                                    description=f"Ev10.az: {raw_text}",
                                    price=0.0,
                                    currency="AZN",
                                    district=district,
                                    metro_station=metro,
                                    rooms=rooms,
                                    area_sqm=area,
                                    building_type=bld_type,
                                    seller_type=detected_seller,
                                    offer_type=detected_offer,
                                    property_type=detected_prop,
                                    listing_url=clean_url,
                                    photos=card_photos
                                ))
                                if len(items) >= 30:
                                    break
                    except Exception as loop_err:
                        logger.debug(f"[Ev10AzScraper] Error fetching {target_url}: {loop_err}")

        except Exception as e:
            logger.debug(f"[Ev10AzScraper] Error scraping: {e}")

        logger.info(f"[Ev10AzScraper] Extracted {len(items)} listings.")
        return items

