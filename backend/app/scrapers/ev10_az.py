import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers
from app.core.baku_locations import extract_baku_district, extract_metro_station

logger = logging.getLogger(__name__)

class Ev10AzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://ev10.az/elanlar/alqi-satqi") -> List[RawListingItem]:
        logger.info(f"[Ev10AzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            headers = get_random_headers(referer="https://ev10.az/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url_or_handle, headers=headers)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", href=re.compile(r'/posting/(\d+)'))
                    seen = {}

                    for a in links:
                        href = a.get('href', '')
                        m = re.search(r'/posting/(\d+)', href)
                        if not m:
                            continue
                        ext_id = m.group(1)
                        text = a.get_text(separator=" | ", strip=True)
                        if not text:
                            parent = a.find_parent("div", class_=lambda c: c and any(x in str(c) for x in ['MuiGrid-item', 'postingCard', 'item', 'card'])) or a.find_parent("div")
                            if parent:
                                text = parent.get_text(separator=" | ", strip=True)
                        if ext_id not in seen or len(text) > len(seen[ext_id].get('text', '')):
                            seen[ext_id] = {'href': href, 'text': text}

                    for ext_id, data in seen.items():
                        href = data['href']
                        raw_text = data['text']

                        price_m = re.search(r'([\d,.\s]+)\s*(?:AZN|₼|manat)', raw_text, re.IGNORECASE)
                        clean_pr_str = price_m.group(1).replace(" ", "").replace(",", "").replace("\xa0", "") if price_m else ""
                        price = float(clean_pr_str) if clean_pr_str and clean_pr_str.replace(".", "", 1).isdigit() else 0.0

                        rooms_m = re.search(r'(\d+)\s*otaq', raw_text)
                        rooms = int(rooms_m.group(1)) if rooms_m else None

                        area_m = re.search(r'([\d.]+)\s*m²', raw_text) or re.search(r'([\d.]+)\s*kv', raw_text)
                        area = float(area_m.group(1)) if area_m else None

                        floor_m = re.search(r'(\d+)\s*/\s*(\d+)', raw_text)
                        floor = int(floor_m.group(1)) if floor_m else None
                        total_floors = int(floor_m.group(2)) if floor_m else None

                        district = extract_baku_district(raw_text) or extract_baku_district(href)
                        metro = extract_metro_station(raw_text) or extract_metro_station(href)

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
                        loc_label = metro or district or 'Bakı'
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

                        bld_type = None if detected_prop in ["commercial", "office", "land"] else ("old" if "köhnə" in raw_text.lower() else "new")
                        clean_url = href if href.startswith("http") else f"https://ev10.az{href if href.startswith('/') else '/' + href}"

                        # Extract card photo
                        card_photos = []
                        if parent:
                            img_el = parent.find("img")
                            if img_el:
                                src_val = img_el.get("src") or img_el.get("data-src")
                                if src_val and "http" in src_val:
                                    card_photos.append(src_val)
                                elif src_val and src_val.startswith("/"):
                                    card_photos.append(f"https://ev10.az{src_val}")

                        items.append(RawListingItem(
                            external_id=f"ev10_{ext_id}",
                            title=title,
                            description=f"Ev10.az elanı: {raw_text[:200]}",
                            price=price,
                            currency="AZN",
                            district=district,
                            metro_station=metro,
                            rooms=rooms,
                            area_sqm=area,
                            floor=floor,
                            total_floors=total_floors,
                            building_type=bld_type,
                            seller_type=detected_seller,
                            offer_type=detected_offer,
                            property_type=detected_prop,
                            listing_url=clean_url,
                            photos=card_photos
                        ))
                        if len(items) >= 25:
                            break

        except Exception as e:
            logger.error(f"[Ev10AzScraper] Error scraping: {e}")

        logger.info(f"[Ev10AzScraper] Extracted {len(items)} listings.")
        return items
