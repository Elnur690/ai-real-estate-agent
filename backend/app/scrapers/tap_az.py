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

class TapAzScraper(BaseScraper):
    @staticmethod
    async def fetch_item_details(item_id_or_url: str) -> dict:
        """Fetches full item details from Tap.az including real seller type and phone number."""
        clean_url = str(item_id_or_url).strip()
        m = re.search(r'(\d+)', clean_url)
        if not m:
            return {}
        ext_id = m.group(1)
        if not clean_url.startswith("http"):
            clean_url = f"https://tap.az/elanlar/dasinmaz-emlak/menziller/{ext_id}"

        headers = get_random_headers(referer="https://tap.az/elanlar/dasinmaz-emlak")
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                res = await client.get(clean_url, headers=headers)
                if res.status_code != 200:
                    return {}

                soup = BeautifulSoup(res.text, "html.parser")
                page_text_lower = soup.get_text().lower()

                # Extract author elements
                author_el = soup.find(class_=re.compile(r'author|shop-contact|seller|user-info', re.I))
                author_text = author_el.get_text(separator=" ", strip=True).lower() if author_el else ""

                desc_el = soup.find(class_=re.compile(r'text|description|body', re.I))
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

                is_shop = bool(soup.find(class_=re.compile(r'shop-badge|shop-header|shop-contact', re.I))) or bool(soup.find("a", href=re.compile(r'/shops/')))
                is_agent = is_shop or has_agency_kw or (
                    any(k in author_text for k in ["vasitəçi", "vasiteci", "agent", "agentlik", "şirkət", "rieltor", "makler"])
                )

                is_owner = (
                    ("mülkiyyətçi" in author_text or "sahibindən" in author_text) and not is_agent
                )

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
            logger.debug(f"[TapAzScraper] Error fetching detail for {clean_url}: {e}")
            return {}

    async def scrape_source(self, url_or_handle: str = "https://tap.az/elanlar/dasinmaz-emlak") -> List[RawListingItem]:
        logger.info(f"[TapAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []
        seen = set()

        urls_to_fetch = [url_or_handle] if ("?" in url_or_handle or not url_or_handle.endswith("tap.az/elanlar/dasinmaz-emlak")) else [
            "https://tap.az/elanlar/dasinmaz-emlak?order=new",
            "https://tap.az/elanlar/dasinmaz-emlak/menziller?order=new",
            "https://tap.az/elanlar/dasinmaz-emlak/heyet-evleri-baglar-villalar?order=new",
            "https://tap.az/elanlar/dasinmaz-emlak/ofisler?order=new",
            "https://tap.az/elanlar/dasinmaz-emlak/obyektler?order=new",
            "https://tap.az/elanlar/dasinmaz-emlak/torpaq?order=new"
        ]

        headers = get_random_headers(referer="https://tap.az/")
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        headers["Accept-Language"] = "az,ru;q=0.9,en-US;q=0.8,en;q=0.7"

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for target_url in urls_to_fetch:
                try:
                    res = await client.get(target_url, headers=headers)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.text, "html.parser")
                        cards = soup.find_all("a", href=re.compile(r'/elanlar/dasinmaz-emlak/(?:menziller|heyet-evleri-baglar-villalar|ofisler|obyektler|torpaq)/(\d+)'))
                        if not cards:
                            cards = soup.find_all("a", href=re.compile(r'/elanlar/dasinmaz-emlak/[^"]+/(\d+)'))

                        for a in cards:
                            href = a.get('href', '')
                            m_id = re.search(r'/elanlar/dasinmaz-emlak/[^"]+/(\d+)', href)
                            if not m_id:
                                continue
                            ext_id = m_id.group(1)
                            if ext_id in seen:
                                continue
                            seen.add(ext_id)

                            raw_text = a.get_text(separator=" | ", strip=True).replace('\xa0', ' ')
                            raw_lower = raw_text.lower()

                            price_m = re.search(r'([\d\s]+)\s*\|\s*₼', raw_text) or re.search(r'([\d\s]+)\s*₼', raw_text) or re.search(r'([\d\s]+)\s*AZN', raw_text)
                            price = safe_float(price_m.group(1) if price_m else None, default=0.0)

                            rooms_m = re.search(r'(\d+)\s*-\s*otaqlı', raw_text) or re.search(r'(\d+)\s*otaqlı', raw_text)
                            rooms = int(rooms_m.group(1)) if rooms_m else None
                            area_m = re.search(r'([\d.]+)\s*m²', raw_text)
                            area = safe_optional_float(area_m.group(1) if area_m else None)

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
                            title = f"{rooms} otaqlı {prop_name} ({loc_label})" if rooms else f"{prop_name} ({loc_label})"

                            bld_type = "old" if "köhnə" in raw_lower else "new"

                            # Extract card photo
                            card_photos = []
                            img_el = a.find("img")
                            if img_el:
                                src_val = img_el.get("src") or img_el.get("data-src") or img_el.get("data-original")
                                if src_val and ("uploads/" in src_val or "azstatic" in src_val or "tap.az" in src_val):
                                    src_clean = src_val.replace('/thumbnail/', '/full/').replace('/f660x496/', '/full/')
                                    card_photos.append(src_clean)

                            items.append(RawListingItem(
                                external_id=f"tap_{ext_id}",
                                title=title,
                                description=f"Tap.az: {raw_text}",
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
                                listing_url=f"https://tap.az{href}",
                                photos=card_photos
                            ))
                except Exception as e:
                    logger.warning(f"[TapAzScraper] Error fetching from {target_url}: {e}")

        logger.info(f"[TapAzScraper] Extracted {len(items)} listings.")
        return items
