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

    async def scrape_source(self, url_or_handle: str = "https://lalafo.az/baku/nedvizhimost") -> List[RawListingItem]:
        logger.info(f"[LalafoAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            headers = get_random_headers(referer="https://lalafo.az/")
            headers["Accept"] = "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                # 1. Try Lalafo JSON search feed API first
                api_url = "https://lalafo.az/api/search/v3/feed/details?expand=url&per-page=25&category_id=2043&city_id=103184"
                try:
                    api_res = await client.get(api_url, headers=headers)
                    if api_res.status_code == 200 and "application/json" in api_res.headers.get("content-type", ""):
                        data = api_res.json()
                        feed_items = data.get("items", []) or []
                        for item in feed_items:
                            ext_id = str(item.get("id"))
                            if not ext_id:
                                continue
                            raw_title = item.get("title") or ""
                            raw_desc = item.get("description") or ""
                            full_text = f"{raw_title} {raw_desc}"
                            price = safe_float(item.get("price"), default=0.0)
                            curr = item.get("currency") or "AZN"
                            
                            district = extract_baku_district(full_text)
                            settlement = extract_baku_settlement(full_text)
                            metro = extract_metro_station(full_text)
                            
                            if not district:
                                if settlement and settlement in SETTLEMENT_TO_DISTRICT:
                                    district = SETTLEMENT_TO_DISTRICT[settlement]
                                elif metro and metro in METRO_TO_DISTRICT:
                                    district = METRO_TO_DISTRICT[metro]

                            from app.core.property_classifier import classify_property_and_offer
                            item_url = item.get("url") or f"/baku/ads/item-id-{ext_id}"
                            detected_offer, detected_prop, detected_seller = classify_property_and_offer(
                                title=raw_title,
                                description=raw_desc,
                                url=item_url,
                                raw_text=full_text
                            )
                            user_obj = item.get("user") or {}
                            if bool(user_obj.get("is_business") or user_obj.get("is_shop") or user_obj.get("account_type") == "business"):
                                detected_seller = "agency"

                            # Extract photos from JSON item
                            item_photos = []
                            if item.get("images"):
                                for img_obj in item["images"]:
                                    if isinstance(img_obj, dict) and img_obj.get("url"):
                                        item_photos.append(img_obj["url"])
                                    elif isinstance(img_obj, str):
                                        item_photos.append(img_obj)
                            elif item.get("image"):
                                item_photos.append(item["image"])

                            items.append(RawListingItem(
                                external_id=f"lalafo_{ext_id}",
                                title=raw_title or f"Əmlak ({district or 'Bakı'})",
                                description=raw_desc[:300] if raw_desc else f"Lalafo.az elanı #{ext_id}",
                                price=price,
                                currency=curr,
                                district=district,
                                metro_station=metro,
                                rooms=None,
                                area_sqm=None,
                                building_type="new",
                                seller_type=detected_seller,
                                offer_type=detected_offer,
                                property_type=detected_prop,
                                listing_url=f"https://lalafo.az{item_url}" if item_url.startswith('/') else item_url,
                                photos=item_photos
                            ))
                            if len(items) >= 25:
                                break
                except Exception as api_err:
                    logger.debug(f"[LalafoAzScraper] API feed fallback to HTML ({api_err})")

                # 2. Fallback to HTML scraping if API returned 0 items
                if not items:
                    res = await client.get(url_or_handle, headers=headers)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.text, "html.parser")
                        links = soup.find_all("a", href=re.compile(r'/baku/ads/.*-id-(\d+)'))
                        seen = set()

                        for a in links:
                            href = a.get('href', '')
                            m = re.search(r'-id-(\d+)', href)
                            if not m:
                                continue
                            ext_id = m.group(1)
                            if ext_id in seen:
                                continue
                            seen.add(ext_id)

                            raw_text = a.get_text(separator=" | ", strip=True).replace('\xa0', ' ')
                            raw_lower = raw_text.lower()

                            price_m = re.search(r'([\d\s]+)\s*(?:AZN|₼|manat)', raw_text) or re.search(r'([\d\s]+)\s*USD', raw_text)
                            price = safe_float(price_m.group(1) if price_m else None, default=0.0)

                            rooms_m = re.search(r'(\d+)\s*-\s*otaql', href) or re.search(r'(\d+)\s*otaql', raw_text) or re.search(r'(\d+)\s*otaq', raw_text)
                            rooms = int(rooms_m.group(1)) if rooms_m else None

                            area_m = re.search(r'(\d+)\s*-\s*kv', href) or re.search(r'([\d.]+)\s*m²', raw_text)
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
                            title = f"{rooms} otaqlı {prop_name} ({loc_label})" if rooms else f"{prop_name} ({loc_label})"

                            bld_type = "old" if "köhnə" in raw_lower else "new"

                            # Extract card photo
                            card_photos = []
                            img_el = a.find("img")
                            if img_el:
                                src_val = img_el.get("src") or img_el.get("data-src")
                                if src_val and "http" in src_val:
                                    card_photos.append(src_val)

                            items.append(RawListingItem(
                                external_id=f"lalafo_{ext_id}",
                                title=title,
                                description=f"Lalafo.az elanı: {raw_text[:200]}",
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
                            if len(items) >= 25:
                                break

        except Exception as e:
            logger.info(f"[LalafoAzScraper] Lalafo temporary scrape status: {e}")

        logger.info(f"[LalafoAzScraper] Extracted {len(items)} listings.")
        return items
