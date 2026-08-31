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

class LalafoAzScraper(BaseScraper):
    @staticmethod
    async def fetch_item_details(item_id_or_url: str) -> dict:
        """Fetches full item details from Lalafo.az including real seller type and phone."""
        clean_url = str(item_id_or_url).strip()
        m = re.search(r'(\d+)', clean_url)
        if not m:
            return {}
        ext_id = m.group(1)
        api_url = f"https://lalafo.az/api/search/v3/feed/details/{ext_id}"

        headers = get_random_headers(referer="https://lalafo.az/")
        headers["Accept"] = "application/json"
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                res = await client.get(api_url, headers=headers)
                if res.status_code == 200 and "application/json" in res.headers.get("content-type", ""):
                    data = res.json()
                    raw_desc = data.get("description") or ""
                    user_obj = data.get("user") or {}
                    is_business = bool(user_obj.get("is_business") or user_obj.get("is_shop") or user_obj.get("account_type") == "business")

                    from app.core.property_classifier import classify_property_and_offer
                    offer, prop, seller = classify_property_and_offer(
                        title=data.get("title") or "",
                        description=raw_desc,
                        url=f"https://lalafo.az/baku/ads/{ext_id}"
                    )
                    if is_business:
                        seller = "agency"

                    return {
                        "phone_number": data.get("mobile") or data.get("phone"),
                        "full_description": raw_desc,
                        "seller_type": seller,
                        "is_makler": seller == "agency",
                        "makler_score": 1.0 if seller == "agency" else 0.0
                    }
        except Exception as e:
            logger.debug(f"[LalafoAzScraper] Error fetching detail for {clean_url}: {e}")
        return {}

    async def scrape_source(self, url_or_handle: str = "https://lalafo.az/baku/kvartiry") -> List[RawListingItem]:
        logger.info(f"[LalafoAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        target_urls = [
            url_or_handle,
            "https://lalafo.az/baku/nedvizhimost",
            "https://lalafo.az/baku/doma-i-dachi"
        ] if url_or_handle == "https://lalafo.az/baku/kvartiry" else [url_or_handle]

        seen = set()
        try:
            headers = get_random_headers(referer="https://lalafo.az/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                for target_url in target_urls:
                    try:
                        res = await client.get(target_url, headers=headers)
                        if res.status_code == 200:
                            soup = BeautifulSoup(res.text, "html.parser")
                            links = soup.find_all("a", href=re.compile(r'/baku/ads/.*-id-(\d+)'))

                            for a in links:
                                href = a.get('href', '')
                                m = re.search(r'-id-(\d+)', href)
                                if not m:
                                    continue
                                ext_id = m.group(1)
                                if ext_id in seen:
                                    continue
                                seen.add(ext_id)

                                parent = (
                                    a.find_parent('article') or 
                                    a.find_parent('div', class_=lambda c: c and any(x in str(c) for x in ['adTile', 'card', 'item', 'listing'])) or 
                                    a.find_parent('div')
                                )
                                card_text = parent.get_text(separator=" | ", strip=True).replace('\xa0', ' ') if parent else a.get_text(strip=True).replace('\xa0', ' ')
                                raw_lower = card_text.lower()

                                price_m = re.search(r'(?i)([\d\s]+)\s*(?:AZN|₼|manat|Azn|\$|USD)', card_text)
                                price = safe_float(price_m.group(1) if price_m else None, default=0.0)

                                rooms_m = re.search(r'(\d+)\s*-\s*otaql', href) or re.search(r'(\d+)\s*otaql', card_text) or re.search(r'(\d+)\s*otaq', card_text)
                                rooms = int(rooms_m.group(1)) if rooms_m else None

                                area_m = re.search(r'(\d+)\s*-\s*kv', href) or re.search(r'([\d.]+)\s*m²', card_text) or re.search(r'([\d.]+)\s*kv', card_text) or re.search(r'([\d.]+)\s*sot', card_text)
                                area = safe_optional_float(area_m.group(1) if area_m else None)

                                district = extract_baku_district(card_text) or extract_baku_district(href) 
                                settlement = extract_baku_settlement(card_text) or extract_baku_settlement(href)
                                metro = extract_metro_station(card_text) or extract_metro_station(href)

                                if not district:
                                    if settlement and settlement in SETTLEMENT_TO_DISTRICT:
                                        district = SETTLEMENT_TO_DISTRICT[settlement]
                                    elif metro and metro in METRO_TO_DISTRICT:
                                        district = METRO_TO_DISTRICT[metro]

                                from app.core.property_classifier import classify_property_and_offer
                                detected_offer, detected_prop, detected_seller = classify_property_and_offer(
                                    title="",
                                    description=card_text,
                                    url=href,
                                    raw_text=card_text
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
                                img_el = a.find("img") or (parent.find("img") if parent else None)
                                if img_el:
                                    src_val = img_el.get("src") or img_el.get("data-src")
                                    if src_val and "http" in src_val:
                                        card_photos.append(src_val)

                                items.append(RawListingItem(
                                    external_id=f"lalafo_{ext_id}",
                                    title=title,
                                    description=f"Lalafo.az elanı: {card_text[:200]}",
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
                                    listing_url=f"https://lalafo.az{href}" if href.startswith('/') else href,
                                    photos=card_photos
                                ))
                                if len(items) >= 30:
                                    break
                    except Exception as loop_err:
                        logger.debug(f"[LalafoAzScraper] Error fetching {target_url}: {loop_err}")

        except Exception as e:
            logger.info(f"[LalafoAzScraper] Lalafo temporary scrape status: {e}")

        logger.info(f"[LalafoAzScraper] Extracted {len(items)} listings.")
        return items
