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

class YeniEmlakAzScraper(BaseScraper):
    @staticmethod
    async def fetch_item_details(item_id_or_url: str) -> dict:
        """Fetches full item details from YeniEmlak.az including real seller type (Vasitəçi / Rieltor vs Mülkiyyətçi)."""
        clean_url = str(item_id_or_url).strip()
        m = re.search(r'(\d+)', clean_url)
        if not m:
            return {}
        ext_id = m.group(1)
        if not clean_url.startswith("http"):
            clean_url = f"https://yeniemlak.az/elan/{ext_id}"

        headers = get_random_headers(referer="https://yeniemlak.az/elan/axtar")
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                res = await client.get(clean_url, headers=headers)
                if res.status_code != 200:
                    return {}

                soup = BeautifulSoup(res.text, "html.parser")
                page_text_lower = soup.get_text().lower()

                # Extract full description
                desc_el = soup.find(class_=re.compile(r'elan_text|description|more_info|item_text|text', re.I)) or soup.find("article")
                full_desc = desc_el.get_text(separator=" ", strip=True) if desc_el else ""

                # Extract author / seller info specifically
                author_elements = soup.find_all(["td", "div", "span", "p", "tr"], text=re.compile(r'elan verən|vasitəçi|rieltor|mülkiyyətçi|sahibindən|şirkət|agent', re.I))
                author_text = " ".join(el.get_text(separator=" ", strip=True).lower() for el in author_elements)

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

                is_agent = (
                    any(k in page_text_lower for k in [
                        "vasitəçi / rieltor", "vasiteci / rieltor", "vasitəçi/rieltor", "vasiteci/rieltor",
                        "vasitəçi", "vasiteci", "rieltor", "realtor", "əmlak şirkəti", "emlak sirketi",
                        "şirkətin xidmət haqqı", "ofis haqqı", "1% ofis", "xidmət haqqı"
                    ]) and not any(k in page_text_lower for k in [
                        "vasitəçilər narahat etməsin", "vasiteciler narahat etmesin",
                        "makler narahat etməsin", "maklersiz", "vasitəçisiz"
                    ])
                ) or has_agency_kw

                is_owner = (
                    any(k in author_text for k in ["mülkiyyətçi", "mulkiyyetci", "öz mənzilimdir", "öz evimdir"]) or
                    ("mülkiyyətçi" in page_text_lower and not is_agent)
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

                # Extract phone
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
            logger.debug(f"[YeniEmlakAzScraper] Error fetching detail for {clean_url}: {e}")
            return {}

    async def scrape_source(self, url_or_handle: str = "https://yeniemlak.az/elan/axtar") -> List[RawListingItem]:
        logger.info(f"[YeniEmlakAzScraper] Fetching listings from {url_or_handle}")
        items: List[RawListingItem] = []
        seen = set()

        urls_to_fetch = [url_or_handle] if ("?" in url_or_handle and not url_or_handle.endswith("/elan/axtar")) else [
            "https://yeniemlak.az/elan/axtar",
            "https://yeniemlak.az/elan/axtar?elan_nov=1",
            "https://yeniemlak.az/elan/axtar?elan_nov=2",
            "https://yeniemlak.az/elan/axtar?sehife=2"
        ]

        headers = get_random_headers(referer="https://yeniemlak.az/")
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        headers["Accept-Language"] = "az,ru;q=0.9,en-US;q=0.8,en;q=0.7"

        for target_url in urls_to_fetch:
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    res = await client.get(target_url, headers=headers)
                    if res.status_code != 200:
                        continue
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", href=re.compile(r'/elan/(?:satilir|kiraye|gunluk)[^"]+-(\d+)'))

                    for a in links:
                        href = a['href']
                        m_id = re.search(r'-(\d+)$', href)
                        if not m_id:
                            continue
                        ext_id = m_id.group(1)
                        if ext_id in seen:
                            continue
                        seen.add(ext_id)

                        table = a.find_parent("table") or a.find_parent("div")
                        raw_text = table.get_text(separator=" | ", strip=True).replace('\xa0', ' ') if table else a.get_text(strip=True).replace('\xa0', ' ')
                        raw_lower = raw_text.lower()

                        # Price parsing: e.g. "Satılır | 245000" or "Kirayə | 650"
                        price_m = re.search(r'(?:Satılır|Kirayə|Satilir|Kiraye|QİYMƏT)\s*\|\s*(\d+[\d\s]*)', raw_text, re.IGNORECASE) or re.search(r'(\d+[\d\s]*)\s*(?:AZN|₼|manat)', raw_text, re.IGNORECASE)
                        price = float(price_m.group(1).replace(" ", "")) if price_m else 0.0

                        rooms_m = re.search(r'(\d+)\s*\|\s*otaq', raw_text) or re.search(r'(\d+)\s*otaqlı', raw_text)
                        rooms = int(rooms_m.group(1)) if rooms_m else None

                        area_m = re.search(r'([\d.]+)\s*\|\s*m2', raw_text) or re.search(r'([\d.]+)\s*m²', raw_text)
                        area = float(area_m.group(1)) if area_m else None

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
                        if table:
                            img_el = table.find("img")
                            if img_el:
                                src_val = img_el.get("src") or img_el.get("data-src")
                                if src_val and "http" in src_val:
                                    card_photos.append(src_val)
                                elif src_val and src_val.startswith("/"):
                                    card_photos.append(f"https://yeniemlak.az{src_val}")

                        items.append(RawListingItem(
                            external_id=f"yeniemlak_{ext_id}",
                            title=title,
                            description=f"YeniEmlak: {raw_text[:200]}",
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
                            listing_url=f"https://yeniemlak.az{href}",
                            photos=card_photos
                        ))
                        if len(items) >= 40:
                            break
            except Exception as e:
                logger.debug(f"[YeniEmlakAzScraper] Notice scraping {target_url}: {e}")

        logger.info(f"[YeniEmlakAzScraper] Extracted {len(items)} listings.")
        return items
