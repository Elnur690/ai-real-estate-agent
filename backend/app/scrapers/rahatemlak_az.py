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

class RahatEmlakAzScraper(BaseScraper):
    BASE_URL = "https://rahatemlak.az"
    LISTING_URL = "https://rahatemlak.az/alqi-satqi"

    @staticmethod
    async def fetch_item_details(item_id_or_url: str) -> dict:
        """Fetches full item details from RahatEmlak.az including real seller type and phone."""
        clean_url = str(item_id_or_url).strip()
        m = re.search(r'(\d+)', clean_url)
        if not m:
            return {}
        ext_id = m.group(1)
        if not clean_url.startswith("http"):
            clean_url = f"https://rahatemlak.az/elan/{ext_id}"

        headers = get_random_headers(referer="https://rahatemlak.az/")
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                res = await client.get(clean_url, headers=headers)
                if res.status_code != 200:
                    return {}

                soup = BeautifulSoup(res.text, "html.parser")
                page_text_lower = soup.get_text().lower()

                author_el = soup.find(class_=re.compile(r'author|user-info|contact|seller|agent', re.I))
                author_text = author_el.get_text(separator=" ", strip=True).lower() if author_el else ""

                desc_el = soup.find(class_=re.compile(r'text|description|more_info|item_text', re.I)) or soup.find("article")
                full_desc = desc_el.get_text(separator=" ", strip=True) if desc_el else ""

                from app.core.property_classifier import (
                    AGENCY_KEYWORDS, OWNER_KEYWORDS, COMMISSION_REGEX,
                    INVENTORY_CODE_REGEX, MULTI_INVENTORY_REGEX, normalize_az_text
                )

                norm_desc = normalize_az_text(full_desc)
                desc_for_agency = re.sub(
                    r'\b(?:vasitəçisiz|vasitecisiz|maklersiz|vasitəçi yoxdur|vasiteci yoxdur|vasitəçi deyiləm|vasiteci deyilem|vasitəçi deyil|vasiteci deyil|makler deyiləm|makler deyilem|makler deyil|maklerlər narahat etməsin|maklerler narahat etmesin|vasitəçilər narahat etməsin|vasiteciler narahat etmesin)\b',
                    ' [GENUINE_OWNER_FLAG] ',
                    norm_desc
                )

                has_agency_kw = (
                    any(kw in desc_for_agency for kw in AGENCY_KEYWORDS) or
                    bool(COMMISSION_REGEX.search(desc_for_agency)) or
                    bool(INVENTORY_CODE_REGEX.search(desc_for_agency)) or
                    bool(MULTI_INVENTORY_REGEX.search(desc_for_agency))
                )

                is_agent = has_agency_kw or any(k in author_text for k in ["vasitəçi", "vasiteci", "agent", "agentlik", "şirkət", "rieltor", "makler"])
                is_owner = ("mülkiyyətçi" in author_text or "sahibindən" in author_text) and not is_agent

                if is_agent:
                    seller_type = "agency"
                    is_makler = True
                    makler_score = 1.0
                elif is_owner:
                    seller_type = "owner"
                    is_makler = False
                    makler_score = 0.0
                else:
                    seller_type = "agency"
                    is_makler = True
                    makler_score = 0.8

                from app.core.baku_locations import extract_az_phone
                phone_res = extract_az_phone(page_text_lower)
                extracted_phone = phone_res[0] if phone_res else None

                return {
                    "phone_number": extracted_phone,
                    "full_description": full_desc,
                    "seller_type": seller_type,
                    "is_makler": is_makler,
                    "makler_score": makler_score
                }
        except Exception as e:
            logger.debug(f"[RahatEmlakAzScraper] Error fetching detail for {clean_url}: {e}")
            return {}

    async def scrape_source(self, url_or_handle: str = "https://rahatemlak.az/alqi-satqi") -> List[RawListingItem]:
        logger.info(f"[RahatEmlakAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []

        try:
            headers = get_random_headers(referer="https://rahatemlak.az/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(self.LISTING_URL, headers=headers)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", href=re.compile(r'/elan/|/item/|/alqi-satqi/|\.html|/\d+'))
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
                        if parent:
                            img_el = parent.find("img")
                            if img_el:
                                src_val = img_el.get("src") or img_el.get("data-src")
                                if src_val and "http" in src_val:
                                    card_photos.append(src_val)
                                elif src_val and src_val.startswith("/"):
                                    card_photos.append(f"{self.BASE_URL}{src_val}")

                        items.append(RawListingItem(
                            external_id=f"rahatemlak_{ext_id}",
                            title=title,
                            description=f"RahatEmlak.az elanı: {raw_text[:200]}",
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
                            listing_url=f"{self.BASE_URL}{href}" if href.startswith('/') else href,
                            photos=card_photos
                        ))
                        if len(items) >= 20:
                            break
                elif res.status_code == 403:
                    logger.warning(f"[RahatEmlakAzScraper] Site returned 403 Forbidden. Skipped gracefully.")
                else:
                    logger.warning(f"[RahatEmlakAzScraper] Unexpected HTTP status {res.status_code} fetching listings.")

        except Exception as e:
            logger.warning(f"[RahatEmlakAzScraper] Error scraping: {e}")

        logger.info(f"[RahatEmlakAzScraper] Extracted {len(items)} listings.")
        return items
