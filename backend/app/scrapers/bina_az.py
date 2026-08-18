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
from app.core.property_classifier import classify_property_and_offer

logger = logging.getLogger(__name__)

class BinaAzScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "https://bina.az/items?leased=false&category_id=1&city_id=1") -> List[RawListingItem]:
        logger.info(f"[BinaAzScraper] Starting scrape from {url_or_handle}")
        items: List[RawListingItem] = []
        seen = {}

        # If a custom/targeted URL with search parameters is provided, scrape it directly
        if "?" in url_or_handle and not url_or_handle.endswith("bina.az/alqi-satqi"):
            urls_to_fetch = [url_or_handle]
        else:
            # Primary active feeds for sales, owner postings, rentals, and houses
            urls_to_fetch = [
                "https://bina.az/items?leased=false&category_id=1&city_id=1",
                "https://bina.az/items?leased=false&category_id=2&owner_type=owner",
                "https://bina.az/items?leased=true&category_id=1&city_id=1",
                "https://bina.az/items?leased=false&category_id=5"
            ]

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
                    links = soup.find_all("a", href=re.compile(r'/items/(\d+)'))

                    for a in links:
                        m_id = re.search(r'/items/(\d+)', a.get('href', ''))
                        if not m_id:
                            continue
                        ext_id = m_id.group(1)
                        parent = a.find_parent("div", class_=lambda c: c and any(x in str(c) for x in ['items-i', 'items_i', 'card_item', 'products-i'])) or a.find_parent("div")
                        card_text = parent.get_text(separator=" | ", strip=True).replace('\xa0', ' ') if parent else a.get_text(strip=True).replace('\xa0', ' ')

                        if ext_id not in seen or len(card_text) > len(seen[ext_id].get('text', '')):
                            seen[ext_id] = {'href': a['href'], 'text': card_text, 'card': parent, 'target_url': target_url}

                except Exception as e:
                    logger.error(f"[BinaAzScraper] Error fetching from {target_url}: {e}")

        for ext_id, data in seen.items():
            href = data['href']
            raw_text = data['text']
            raw_lower = raw_text.lower()
            c = data['card']
            target_url = data['target_url']

            # 1. Price Extraction & Currency
            price = 0.0
            currency = "AZN"
            price_val_el = c.find("span", class_="price-val") if c else None
            if price_val_el:
                val_clean = re.sub(r'[^\d.]', '', price_val_el.get_text())
                price = safe_float(val_clean, default=0.0)
            else:
                price_m = re.search(r'([\d\s]+)\s*(?:AZN|₼|USD|\$|\/\s*ay|\/\s*gün)', raw_text) or re.search(r'([\d\s]+)\s*\|\s*AZN', raw_text)
                if price_m:
                    price_clean = re.sub(r'[^\d]', '', price_m.group(1))
                    price = safe_float(price_clean, default=0.0)

            if "usd" in raw_lower or "$" in raw_text:
                currency = "USD"

            # 2. Offer Type (Sale, Monthly Rent, Daily Rent)
            if "gunluk" in target_url or "/ gün" in raw_text or "/gun" in raw_lower or "günlük" in raw_lower:
                offer_type = "daily_rent"
            elif "/kiraye" in target_url or "kiraye" in target_url or "/ ay" in raw_text or "aylıq" in raw_lower or "icarə" in raw_lower:
                offer_type = "rent"
            else:
                offer_type = "sale"

            # 3. Rooms, Floor, Area, and Land (Sot)
            rooms_m = re.search(r'(\d+)\s*otaqlı', raw_text)
            rooms = int(rooms_m.group(1)) if rooms_m else None

            area_m = re.search(r'([\d.]+)\s*m²', raw_text)
            area = safe_optional_float(area_m.group(1) if area_m else None)

            land_m = re.search(r'([\d.]+)\s*sot', raw_text)
            land_sot = safe_optional_float(land_m.group(1) if land_m else None)

            floor, total_floors = None, None
            floor_m = re.search(r'(\d+)\s*\/\s*(\d+)\s*mərtəbə', raw_text)
            if floor_m:
                floor = int(floor_m.group(1))
                total_floors = int(floor_m.group(2))

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

            # 5. Property Category Classification
            detected_offer, detected_prop, detected_seller = classify_property_and_offer(
                title="",
                description=raw_text,
                url=href,
                raw_text=raw_text
            )
            if offer_type == "daily_rent":
                detected_offer = "daily_rent"

            # 6. Building Type (Yeni tikili vs Köhnə tikili)
            if "yeni tikili" in raw_lower or "yeni-tikili" in target_url:
                bld_type = "new"
            elif "köhnə tikili" in raw_lower or "kohne tikili" in raw_lower or "kohne-tikili" in target_url:
                bld_type = "old"
            elif detected_prop == "apartment":
                if total_floors and total_floors >= 10:
                    bld_type = "new"
                elif total_floors and total_floors <= 9:
                    bld_type = "old"
                else:
                    bld_type = "new"
            else:
                bld_type = None

            # 7. Seller Type (Strict Mülkiyyətçi Verification)
            has_agency_badge = bool(
                c and (
                    c.find("a", href=re.compile(r'/agentlikler|/complexes|/companies|/shops')) 
                    or c.find(class_=re.compile(r'agency|shop|complex|developer|broker|company|rieltor|items-i-agency', re.I))
                    or c.find("img", src=re.compile(r'agency|logo|shop', re.I))
                )
            )
            has_owner_badge = bool(
                "owner_type=owner" in target_url
                or (c and c.find(class_=re.compile(r'owner|mulkiyyetci|badge-owner', re.I)))
                or any(kw in raw_lower for kw in ["mülkiyyətçi", "mulkiyyetci", "sahibindən", "sahibinden", "öz evimdir", "oz evimdir", "öz mənzilimdir", "vasitəçisiz", "maklersiz"])
            )

            if has_agency_badge or any(kw in raw_lower for kw in ["agentlik", "vasitəçi", "makler", "şirkət", "komissiya", "ofis haqqı"]):
                seller_type = "agency"
            elif has_owner_badge:
                seller_type = "owner"
            else:
                seller_type = "agency"

            # 8. Title construction without repeating price
            prop_label_map = {
                "apartment": "Mənzil",
                "house": "Həyət evi / Bağ evi",
                "office": "Ofis",
                "commercial": "Obyekt",
                "land": "Torpaq sahəsi"
            }
            prop_name = prop_label_map.get(detected_prop, "Əmlak")
            loc_label = settlement or metro or district or "Bakı"

            if detected_prop == "land" and land_sot:
                title = f"{land_sot} sot {prop_name} ({loc_label})"
            elif rooms:
                title = f"{rooms} otaqlı {prop_name} ({loc_label})"
            else:
                title = f"{prop_name} ({loc_label})"

            desc_extra = []
            if land_sot:
                desc_extra.append(f"Torpaq sahəsi: {land_sot} sot")
            if floor and total_floors:
                desc_extra.append(f"Mərtəbə: {floor}/{total_floors}")
            if "çıxarış" in raw_lower or "kupça" in raw_lower:
                desc_extra.append("Çıxarış (Kupça): Var")
            if "ipoteka" in raw_lower:
                desc_extra.append("İpoteka: Var")

            full_desc = f"Bina.az: {raw_text}" + (f" | {' | '.join(desc_extra)}" if desc_extra else "")

            clean_url = href if href.startswith("http") else f"https://bina.az{href}"
            items.append(RawListingItem(
                external_id=f"bina_{ext_id}",
                title=title,
                description=full_desc,
                price=price,
                currency=currency,
                district=district,
                metro_station=metro,
                rooms=rooms,
                area_sqm=area,
                floor=floor,
                total_floors=total_floors,
                building_type=bld_type,
                seller_type=seller_type,
                offer_type=detected_offer,
                property_type=detected_prop,
                listing_url=clean_url
            ))

        logger.info(f"[BinaAzScraper] Extracted {len(items)} listings across all categories.")
        return items
