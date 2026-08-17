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

class BinaAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://bina.az/items?city_id=1") -> List[RawListingItem]:
        logger.info(f"[BinaAzScraper] Starting comprehensive scrape from {url_or_handle}")
        items: List[RawListingItem] = []
        seen = set()

        # URLs to scrape to cover sales, rentals, villas, offices, direct Mülkiyyətçi (owners), and latest listings across Baku
        urls_to_fetch = [
            "https://bina.az/items?owner_type=owner&city_id=1",
            "https://bina.az/items?owner_type=owner&leased=true&city_id=1",
            "https://bina.az/items?category_id=2&city_id=1",
            "https://bina.az/items?category_id=1&city_id=1",
            "https://bina.az/items?category_id=4&city_id=1",
            "https://bina.az/items?leased=false&city_id=1",
            "https://bina.az/items?leased=true&city_id=1",
            "https://bina.az/items?city_id=1"
        ] if (url_or_handle.endswith("bina.az/") or "bina.az/items" in url_or_handle) else [url_or_handle]

        headers = get_random_headers(referer="https://bina.az/")
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        headers["Accept-Language"] = "az,ru;q=0.9,en-US;q=0.8,en;q=0.7"

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for target_url in urls_to_fetch:
                try:
                    res = await client.get(target_url, headers=headers)
                    if res.status_code != 200:
                        logger.warning(f"[BinaAzScraper] GET {target_url} returned status {res.status_code}")
                        continue

                    soup = BeautifulSoup(res.text, "html.parser")
                    cards = soup.find_all("div", class_=re.compile(r'items-i|items_i|card_item|item-card|vi_item'))

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

                        raw_text = c.get_text(separator=" | ", strip=True).replace('\xa0', ' ')
                        raw_lower = raw_text.lower()

                        # 1. Price Extraction
                        price = 0.0
                        currency = "AZN"
                        price_val_el = c.find("span", class_="price-val")
                        if price_val_el:
                            val_clean = re.sub(r'[^\d.]', '', price_val_el.get_text())
                            price = float(val_clean) if val_clean else 0.0
                        else:
                            price_m = re.search(r'([\d\s]+)\s*(?:AZN|₼|USD|\$|\/\s*ay)', raw_text) or re.search(r'([\d\s]+)\s*\|\s*AZN', raw_text)
                            if price_m:
                                price_clean = re.sub(r'[^\d]', '', price_m.group(1))
                                price = float(price_clean) if price_clean else 0.0

                        if "usd" in raw_lower or "$" in raw_text:
                            currency = "USD"

                        # 2. Offer Type (Sale vs Rent)
                        is_rent = "leased=true" in target_url or "/ ay" in raw_text or "aylıq" in raw_lower or "kirayə" in raw_lower or "icarə" in raw_lower
                        offer_type = "rent" if is_rent else "sale"

                        # 3. Rooms and Area
                        rooms_m = re.search(r'(\d+)\s*otaqlı', raw_text)
                        rooms = int(rooms_m.group(1)) if rooms_m else None
                        area_m = re.search(r'([\d.]+)\s*m²', raw_text)
                        area = float(area_m.group(1)) if area_m else None

                        # 4. Location Details (District, Settlement, Metro)
                        district = extract_baku_district(raw_text)
                        settlement = extract_baku_settlement(raw_text)
                        metro = extract_metro_station(raw_text)

                        # Auto-infer parent district if not explicitly present on card
                        if not district:
                            if settlement and settlement in SETTLEMENT_TO_DISTRICT:
                                district = SETTLEMENT_TO_DISTRICT[settlement]
                            elif metro and metro in METRO_TO_DISTRICT:
                                district = METRO_TO_DISTRICT[metro]

                        # 5. Property Type
                        if any(k in raw_lower for k in ["villa", "həyət evi", "heyet evi", "bağ evi", "bag evi", "bağ"]):
                            prop_type = "villa"
                        elif any(k in raw_lower for k in ["ofis", "plaza", "biznes mərkəzi"]):
                            prop_type = "office"
                        elif any(k in raw_lower for k in ["obyekt", "mağaza", "kafe", "restoran"]):
                            prop_type = "commercial"
                        elif "sot" in raw_lower or "torpaq" in raw_lower:
                            prop_type = "land"
                        else:
                            prop_type = "apartment"

                        # 6. Building Type (New vs Old)
                        if "yeni tikili" in raw_lower:
                            bld_type = "new"
                        elif "köhnə tikili" in raw_lower:
                            bld_type = "old"
                        else:
                            # Heuristic: multi-story >= 10 floors is new building
                            floor_m = re.search(r'(\d+)\/(\d+)\s*mərtəbə', raw_text)
                            if floor_m and int(floor_m.group(2)) >= 10:
                                bld_type = "new"
                            else:
                                bld_type = "new"

                        # 7. Seller Type (Strict Verification)
                        has_agency_badge = bool(
                            c.find("a", href=re.compile(r'/agentlikler|/complexes|/companies|/shops')) 
                            or c.find(class_=re.compile(r'agency|shop|complex|developer|broker|company|rieltor|items-i-agency', re.I))
                            or c.find("img", src=re.compile(r'agency|logo|shop', re.I))
                        )
                        has_owner_badge = bool(
                            c.find(class_=re.compile(r'owner|mulkiyyetci', re.I))
                            or any(kw in raw_lower for kw in ["mülkiyyətçi", "mulkiyyetci", "sahibindən", "sahibinden", "öz evimdir", "oz evimdir", "öz mənzilimdir", "vasitəçisiz", "maklersiz"])
                        )

                        if has_agency_badge or any(kw in raw_lower for kw in ["agentlik", "vasitəçi", "makler", "şirkət", "komissiya", "ofis haqqı"]):
                            seller_type = "agency"
                        elif has_owner_badge:
                            seller_type = "owner"
                        else:
                            # Portal listings without verified owner badge are agencies/brokers
                            seller_type = "agency"

                        # 8. Title
                        loc_label = settlement or metro or district or "Bakı"
                        prop_label = "Mənzil" if prop_type == "apartment" else prop_type.capitalize()
                        title = f"{rooms} otaqlı {prop_label} ({loc_label})" if rooms else f"{prop_label} ({loc_label})"

                        items.append(RawListingItem(
                            external_id=f"bina_{ext_id}",
                            title=title,
                            description=f"Bina.az: {raw_text}",
                            price=price,
                            currency=currency,
                            district=district,
                            metro_station=metro,
                            rooms=rooms,
                            area_sqm=area,
                            building_type=bld_type,
                            seller_type=seller_type,
                            offer_type=offer_type,
                            property_type=prop_type,
                            listing_url=f"https://bina.az{href}"
                        ))
                except Exception as e:
                    logger.error(f"[BinaAzScraper] Error fetching from {target_url}: {e}")

        logger.info(f"[BinaAzScraper] Extracted {len(items)} listings across all categories.")
        return items
