import re
import logging
import asyncio
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

def normalize_bina_url(url: str) -> str:
    """Preserves location slugs or converts short user-facing URLs to internal query URLs."""
    u = url.lower().strip()
    if "category_id=" in u or any(slug in u for slug in ['-r', '-m', '-q', 'khirdalan', 'sumqayit']) or ("/baki/" in u and len(u.split("/")) > 4):
        return url

    leased = "true" if ("/kiraye" in u or "leased=true" in u) else "false"
    city = "1" if ("/baki" in u or "city_id=1" in u) else "1"

    if any(k in u for k in ["heyet-evleri", "villa", "bag-evleri", "villalar"]):
        cat = "5"
    elif "yeni-tikili" in u:
        cat = "2"
    elif "kohne-tikili" in u:
        cat = "3"
    elif "ofis" in u:
        cat = "7"
    elif "obyekt" in u:
        cat = "10"
    elif "torpaq" in u:
        cat = "9"
    elif "qarac" in u or "qaraj" in u:
        cat = "8"
    else:
        cat = "1"

    params = [f"city_id={city}", f"category_id={cat}", f"leased={leased}"]
    if "gunluk" in u or "daily" in u:
        params.append("leased_type=daily")
    if "owner_type=owner" in u or "sahibinden" in u:
        params.append("owner_type=owner")

    return f"https://bina.az/items?{'&'.join(params)}"


class BinaAzScraper(BaseScraper):
    @staticmethod
    async def fetch_item_details(item_id_or_url: str) -> dict:
        """Fetches full item details including real contact phone numbers from API, category, and exact seller type from Bina.az."""
        m = re.search(r'(\d+)', str(item_id_or_url))
        if not m:
            return {}
        ext_id = m.group(1)
        url = f"https://bina.az/items/{ext_id}"
        headers = get_random_headers(referer="https://bina.az/items")

        phone = None
        # 1. Fetch real author phone number from Bina.az JSON endpoint
        try:
            phone_headers = dict(headers)
            phone_headers["X-Requested-With"] = "XMLHttpRequest"
            phone_headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
            async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
                r_phone = await client.get(f"https://bina.az/items/{ext_id}/phones", headers=phone_headers)
                if r_phone.status_code == 200:
                    p_data = r_phone.json()
                    if p_data.get("phones") and len(p_data["phones"]) > 0:
                        from app.core.baku_locations import extract_az_phone
                        p_res = extract_az_phone(p_data["phones"][0])
                        if p_res:
                            phone = p_res[0]
        except Exception as e:
            logger.debug(f"[BinaAzScraper] Error fetching phone JSON for #{ext_id}: {e}")

        try:
            async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
                res = await client.get(url, headers=headers)
                if res.status_code != 200:
                    return {"phone_number": phone} if phone else {}

                soup = BeautifulSoup(res.text, "html.parser")
                page_text_lower = soup.get_text().lower()

                # 2. Extract full description
                desc_el = soup.find("article") or soup.find(class_=re.compile(r'description|article_body|item_description', re.I))
                full_desc = desc_el.get_text(separator=" ", strip=True) if desc_el else ""

                # 3. Extract Category / Property Type (Breadcrumbs, H1, Parameters)
                breadcrumbs_el = soup.find(class_=re.compile(r'breadcrumb', re.I))
                breadcrumbs_text = breadcrumbs_el.get_text(separator=" ", strip=True).lower() if breadcrumbs_el else ""
                h1_el = soup.find("h1")
                h1_text = h1_el.get_text(strip=True).lower() if h1_el else ""
                
                combined_cat_text = f"{breadcrumbs_text} {h1_text} {full_desc[:300].lower()}"

                detected_prop = "apartment"
                if any(k in combined_cat_text for k in ["obyekt", "qeyri-yaşayış", "qeyri yasayis", "anbar", "istehsalat", "magaza", "mağaza", "restoran", "kafe", "salon", "klinika"]):
                    detected_prop = "commercial"
                elif any(k in combined_cat_text for k in ["ofis", "ofislər", "biznes mərkəzi"]):
                    detected_prop = "office"
                elif any(k in combined_cat_text for k in ["torpaq", "sot"]) and "otaqlı" not in combined_cat_text:
                    detected_prop = "land"
                elif any(k in combined_cat_text for k in ["həyət evi", "heyet evi", "bağ evi", "bag evi", "villa", "villalar"]):
                    detected_prop = "house"
                else:
                    detected_prop = "apartment"

                # 4. Extract Seller Type & Agency Status from Page
                owner_region_el = (
                    soup.find(class_='product-owner__info-region') or
                    soup.find(class_=re.compile(r'product-owner__info-region|seller_region|author-region', re.I)) or
                    soup.find(class_=re.compile(r'product-owner__info-type|author-type|product-author__type', re.I)) or
                    soup.find(class_=re.compile(r'product-owner__type|seller-type', re.I))
                )
                owner_region_text = owner_region_el.get_text(strip=True).lower() if owner_region_el else ""

                owner_name_el = soup.find(class_='product-owner__info-name') or soup.find(class_=re.compile(r'owner__info-name|author-name', re.I))
                owner_name = owner_name_el.get_text(strip=True) if owner_name_el else ""

                # Check all author / seller containers on the page
                author_elements = soup.find_all(class_=re.compile(r'product-owner__info|product-owner|product-author|product-sidebar|product-contacts', re.I))
                author_texts = [el.get_text(separator=" ", strip=True).lower() for el in author_elements]
                combined_author_text = " ".join(author_texts)

                # Check parameters list for seller row (e.g. "Elanın tipi: Vasitəçi" or "Satıcı: Vasitəçi")
                param_elements = soup.find_all(class_=re.compile(r'param|property|item_parameters', re.I))
                param_text = " ".join(p.get_text(separator=" ", strip=True).lower() for p in param_elements)

                # Distinguish specific profile links (e.g. /vasiteciler/123, /agentlikler/123, /agents/123)
                has_specific_agency_link = bool(
                    soup.find("a", href=re.compile(r'/agentlikler/\d+|/vasiteciler/\d+|/agents/\d+|/shops/\w+|/companies/\d+|/complexes/\d+|/users/\d+'))
                    or soup.find(class_=re.compile(r'author-agency|items-i-agency|product-owner__info-agency', re.I))
                )

                # Check scripts or JSON payloads on the page for agency indicators
                script_agency_flag = False
                for script in soup.find_all("script"):
                    if script.string and any(k in script.string.lower() for k in ['"is_agency":true', '"is_agent":true', '"seller_type":"agency"', '"user_type":"agent"', '"is_vasiteci":true']):
                        script_agency_flag = True
                        break

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

                is_author_agent = (
                    has_specific_agency_link or
                    script_agency_flag or
                    any(k in owner_region_text for k in ["vasitəçi", "vasiteci", "agent", "agentlik", "şirkət", "sirket", "rieltor", "makler"]) or
                    any(k in combined_author_text for k in ["vasitəçi (agent)", "vasiteci (agent)", "vasitəçi", "vasiteci", "agentlik", "şirkət"]) or
                    any(k in param_text for k in ["vasitəçi", "vasiteci", "agent", "agentlik"])
                )

                is_author_owner = (
                    ("mülkiyyətçi" in owner_region_text or "sahibindən" in owner_region_text) and
                    not is_author_agent
                )

                if is_author_agent or has_agency_kw:
                    seller_type = "agency"
                    is_makler = True
                    makler_score = 1.0
                elif is_author_owner:
                    seller_type = "owner"
                    is_makler = False
                    makler_score = 0.0
                elif any(k in norm_desc for k in OWNER_KEYWORDS):
                    seller_type = "owner"
                    is_makler = False
                    makler_score = 0.0
                else:
                    seller_type = "agency"
                    is_makler = True
                    makler_score = 0.8

                # 5. Extract Price & Price Per SQM from Detail Page
                price = None
                currency = "AZN"
                price_per_sqm = None

                for sp in soup.find_all(["span", "div"]):
                    txt = sp.get_text(separator=" ", strip=True).replace('\xa0', ' ')
                    if re.search(r'^\s*[\d\s]+\s*(?:AZN|₼|USD|\$)\s*$', txt):
                        m_val = re.search(r'([\d\s]+)', txt)
                        if m_val:
                            val_clean = m_val.group(1).replace(" ", "").strip()
                            if val_clean.isdigit():
                                val_num = float(val_clean)
                                if val_num > 0 and val_num != 2008 and (price is None or val_num > price):
                                    price = val_num
                                    if "$" in txt or "USD" in txt:
                                        currency = "USD"
                    elif 'AZN/m²' in txt or '₼/m²' in txt or 'USD/m²' in txt:
                        m_sqm = re.search(r'([\d\s]+)\s*(?:AZN|₼|USD|\$)\/m²', txt)
                        if m_sqm:
                            val_clean = m_sqm.group(1).replace(" ", "").strip()
                            if val_clean.isdigit():
                                price_per_sqm = float(val_clean)

                # 6. Extract Offer Type (sale vs rent vs daily_rent) strictly from H1 & breadcrumbs
                detected_offer = "sale"
                if "günlük" in h1_text or "gunluk" in h1_text or "sutkalıq" in h1_text:
                    detected_offer = "daily_rent"
                elif any(k in h1_text for k in ["icarə", "icare", "kirayə", "kiraye"]):
                    detected_offer = "rent"
                elif "satılır" in h1_text:
                    detected_offer = "sale"

                # 7. Extract exact rooms if present
                rooms = None
                rooms_m = re.search(r'(\d+)\s*otaq', f"{h1_text} {full_desc[:200].lower()}")
                if rooms_m:
                    rooms = int(rooms_m.group(1))

                # 8. Extract all Photos from Detail Page Gallery via ScraplingHelper
                from app.scrapers.utils import ScraplingHelper
                clean_photos = ScraplingHelper.extract_all_photos(res.text, base_url="https://bina.az")

                return {
                    "phone_number": phone,
                    "price": price,
                    "currency": currency,
                    "price_per_sqm": price_per_sqm,
                    "full_description": full_desc,
                    "property_type": detected_prop,
                    "offer_type": detected_offer,
                    "seller_type": seller_type,
                    "is_makler": is_makler,
                    "makler_score": makler_score,
                    "rooms": rooms,
                    "owner_name": owner_name,
                    "photos": clean_photos
                }
        except Exception as e:
            logger.debug(f"[BinaAzScraper] Error fetching detail for item {ext_id}: {e}")
            return {"phone_number": phone} if phone else {}

    async def scrape_source(self, url_or_handle: str = "https://bina.az/items?city_id=1&category_id=1&leased=false") -> List[RawListingItem]:
        logger.info(f"[BinaAzScraper] Starting scrape from {url_or_handle}")
        items: List[RawListingItem] = []
        seen = {}

        # Normalize slug URLs to items query URLs while preserving location slugs
        normalized_url = normalize_bina_url(url_or_handle)

        # Check if this is a targeted criteria query or generic source
        is_targeted_search = (
            any(k in normalized_url for k in ['owner_type=', 'rooms[]=', 'price_min=', 'price_max=', 'location_ids[]=', 'q=']) or
            any(slug in normalized_url for slug in ['-r', '-m', '-q', 'khirdalan', 'sumqayit']) or
            ("/baki/" in normalized_url and len(normalized_url.split("/")) > 4)
        )

        if is_targeted_search:
            urls_to_fetch = [normalized_url]
        else:
            # High-speed master streams covering all newly published real estate categories
            urls_to_fetch = [
                "https://bina.az/items?sort_by=created_at_desc",
                "https://bina.az/items?city_id=1&leased=true&sort_by=created_at_desc",
                "https://bina.az/items?city_id=1&category_id=1&leased=false&owner_type=owner&sort_by=created_at_desc",
                "https://bina.az/items?city_id=1&category_id=5&leased=false&sort_by=created_at_desc",
                "https://bina.az/items?city_id=1&category_id=10&leased=false&sort_by=created_at_desc"
            ]

        sem = asyncio.Semaphore(4)

        async def fetch_target(target_url: str):
            for attempt in range(1, 3):
                async with sem:
                    try:
                        await asyncio.sleep(0.1)
                        req_headers = get_random_headers(referer="https://bina.az/")
                        req_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                        req_headers["Accept-Language"] = "az,ru;q=0.9,en-US;q=0.8,en;q=0.7"
                        req_headers["Connection"] = "close"

                        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0), follow_redirects=True) as client:
                            res = await client.get(target_url, headers=req_headers)
                            if res.status_code != 200:
                                logger.debug(f"[BinaAzScraper] GET {target_url} returned status {res.status_code}")
                                return

                            soup = BeautifulSoup(res.text, "html.parser")
                            links = soup.find_all("a", href=re.compile(r'/items/(\d+)'))

                            for a in links:
                                m_id = re.search(r'/items/(\d+)', a.get('href', ''))
                                if not m_id:
                                    continue
                                ext_id = m_id.group(1)
                                parent = (
                                    a.find_parent("div", attrs={"data-cy": "item-card"}) or
                                    a.find_parent("div", class_=re.compile(r'item-card|items-i|items_i|card_item|products-i')) or
                                    a.find_parent("div")
                                )
                                card_text = parent.get_text(separator=" | ", strip=True).replace('\xa0', ' ') if parent else a.get_text(strip=True).replace('\xa0', ' ')

                                if ext_id not in seen or len(card_text) > len(seen[ext_id].get('text', '')):
                                    seen[ext_id] = {'href': a['href'], 'text': card_text, 'card': parent, 'target_url': target_url, 'link_elem': a}
                            return
                    except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadTimeout, Exception) as e:
                        if attempt < 2:
                            await asyncio.sleep(0.5)
                        else:
                            logger.debug(f"[BinaAzScraper] Notice fetching from {target_url}: {e}")

        await asyncio.gather(*[fetch_target(u) for u in urls_to_fetch])

        for ext_id, data in seen.items():
            href = data['href']
            raw_text = data['text']
            raw_lower = raw_text.lower()
            c = data['card']
            target_url = data['target_url']
            a_link = data.get('link_elem')
            aria_label = a_link.get('aria-label', '') if a_link else ''
            combined_text = f"{aria_label} | {raw_text}".replace('\xa0', ' ')
            combined_lower = combined_text.lower()

            # 1. Price Extraction & Currency
            price = 0.0
            currency = "AZN"
            price_val_el = (
                c.find(attrs={"data-cy": "item-card-price-full"}) or
                c.find(attrs={"data-cy": "item-card-price"}) or
                c.find("span", class_=re.compile(r'price-val|price-container|price', re.I))
            ) if c else None

            if price_val_el:
                val_clean = re.sub(r'[^\d.]', '', price_val_el.get_text().replace('\xa0', ' '))
                price = safe_float(val_clean, default=0.0)
            
            if not price or price == 0:
                price_m = re.search(r'([\d\s]+)\s*(?:AZN|₼|USD|\$|\/\s*ay|\/\s*gün)', raw_text) or re.search(r'([\d\s]+)\s*\|\s*AZN', raw_text) or re.search(r'(\d+[\d\s]{3,})', raw_text)
                if price_m:
                    price_clean = re.sub(r'[^\d]', '', price_m.group(1))
                    price = safe_float(price_clean, default=0.0)

            if "usd" in combined_lower or "$" in combined_text:
                currency = "USD"

            # 2. Offer Type (Sale, Monthly Rent, Daily Rent)
            if "gunluk" in target_url or "daily" in target_url or "/ gün" in combined_text or "/gun" in combined_lower or "günlük" in combined_lower or "sutkalıq" in combined_lower or "günlük kirayə" in combined_lower:
                offer_type = "daily_rent"
            elif "/kiraye" in target_url or "leased=true" in target_url or "kiraye" in target_url or "/ ay" in combined_text or "aylıq" in combined_lower or "icarə" in combined_lower or "kirayə" in combined_lower:
                offer_type = "rent"
            elif price > 0 and price <= 350:
                # Real estate in Baku is never sold for <= 350 AZN. If <= 350 AZN, it is daily/monthly rental.
                offer_type = "daily_rent"
            else:
                offer_type = "sale"

            # 3. Rooms, Floor, Area, and Land (Sot)
            rooms_m = re.search(r'(\d+)\s*otaqlı', combined_text)
            rooms = int(rooms_m.group(1)) if rooms_m else None

            area_m = re.search(r'([\d.]+)\s*m²', combined_text)
            area = safe_optional_float(area_m.group(1) if area_m else None)

            land_m = re.search(r'([\d.]+)\s*sot', combined_text)
            land_sot = safe_optional_float(land_m.group(1) if land_m else None)

            floor, total_floors = None, None
            floor_m = re.search(r'(\d+)\s*\/\s*(\d+)\s*mərtəbə', combined_text)
            if floor_m:
                floor = int(floor_m.group(1))
                total_floors = int(floor_m.group(2))

            # 4. Location Details (District, Settlement, Metro)
            district = extract_baku_district(combined_text)
            settlement = extract_baku_settlement(combined_text)
            metro = extract_metro_station(combined_text)

            # Auto-infer parent district if not explicitly present on card
            if not district:
                if settlement and settlement in SETTLEMENT_TO_DISTRICT:
                    district = SETTLEMENT_TO_DISTRICT[settlement]
                elif metro and metro in METRO_TO_DISTRICT:
                    district = METRO_TO_DISTRICT[metro]

            # 5. Property Category Classification based on card content & category_id
            if "sot" in combined_lower and "otaqlı" not in combined_lower and "mərtəbə" not in combined_lower:
                detected_prop = "land"
            elif any(k in combined_lower for k in ["həyət evi", "heyet evi", "bağ evi", "bag evi", "villa"]):
                detected_prop = "house"
            elif "ofis" in combined_lower:
                detected_prop = "office"
            elif "obyekt" in combined_lower:
                detected_prop = "commercial"
            elif "category_id=5" in target_url or "heyet-evleri" in target_url or "villa" in target_url:
                detected_prop = "house"
            elif "category_id=7" in target_url:
                detected_prop = "office"
            elif "category_id=10" in target_url or "obyekt" in target_url:
                detected_prop = "commercial"
            elif "category_id=9" in target_url or "torpaq" in target_url:
                detected_prop = "land"
            else:
                detected_prop = "apartment"

            detected_offer = offer_type

            # 6. Building Type (Yeni tikili vs Köhnə tikili)
            if detected_prop in ["commercial", "office", "land"]:
                bld_type = None
            elif "category_id=2" in target_url or "yeni tikili" in combined_lower or "yeni-tikili" in target_url:
                bld_type = "new"
            elif "category_id=3" in target_url or "köhnə tikili" in combined_lower or "kohne tikili" in combined_lower or "kohne-tikili" in target_url:
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

            # 7. Seller Type (Bina.az Agency Tag Detection)
            has_agency_badge = bool(
                c and (
                    c.find(attrs={"data-cy": "product-label-agency"}) 
                    or c.find("a", href=re.compile(r'/agentlikler|/vasiteciler|/complexes|/companies|/shops')) 
                    or c.find(class_=re.compile(r'agency|shop|complex|developer|broker|company|rieltor|items-i-agency', re.I))
                    or c.find("img", src=re.compile(r'agency|logo|shop', re.I))
                    or "agentlik" in combined_lower
                )
            )

            if "owner_type=owner" in target_url:
                seller_type = "owner"
            elif has_agency_badge:
                seller_type = "agency"
            else:
                from app.core.property_classifier import classify_property_and_offer
                _, _, detected_seller = classify_property_and_offer(
                    title="",
                    description=combined_text,
                    url=href,
                    raw_text=combined_text
                )
                seller_type = detected_seller

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
            elif detected_prop == "commercial":
                title = f"{int(area)} m² Obyekt ({loc_label})" if area else f"Obyekt ({loc_label})"
            elif detected_prop == "office":
                title = f"{rooms} otaqlı Ofis ({loc_label})" if rooms else (f"{int(area)} m² Ofis ({loc_label})" if area else f"Ofis ({loc_label})")
            elif rooms:
                title = f"{rooms} otaqlı {prop_name} ({loc_label})"
            else:
                title = f"{prop_name} ({loc_label})"

            desc_extra = []
            if land_sot:
                desc_extra.append(f"Torpaq sahəsi: {land_sot} sot")
            if floor and total_floors:
                desc_extra.append(f"Mərtəbə: {floor}/{total_floors}")
            if "çıxarış" in combined_lower or "kupça" in combined_lower:
                desc_extra.append("Çıxarış (Kupça): Var")
            if "ipoteka" in combined_lower:
                desc_extra.append("İpoteka: Var")

            full_desc = f"Bina.az: {raw_text}" + (f" | {' | '.join(desc_extra)}" if desc_extra else "")

            # Check if any phone is already mentioned in combined_text
            from app.core.baku_locations import extract_az_phone
            phone_found = extract_az_phone(combined_text)
            extracted_phone = phone_found[1] if phone_found else None

            # Extract card photo
            card_photos = []
            if c:
                img_el = c.find("img")
                if img_el:
                    src_val = img_el.get("data-src") or img_el.get("src") or img_el.get("data-full-src")
                    if src_val and ("uploads/" in src_val or "azstatic" in src_val or "bina.az" in src_val):
                        src_clean = src_val.replace('/thumbnail/', '/full/').replace('/f460x345/', '/full/').replace('/f660x496/', '/full/')
                        card_photos.append(src_clean)
                source_el = c.find("source")
                if source_el and source_el.get("srcset"):
                    s_src = source_el.get("srcset").split()[0]
                    if s_src and ("uploads/" in s_src or "azstatic" in s_src or "bina.az" in s_src):
                        s_clean = s_src.replace('/thumbnail/', '/full/').replace('/f460x345/', '/full/').replace('/f660x496/', '/full/')
                        if s_clean not in card_photos:
                            card_photos.append(s_clean)

            clean_url = href if href.startswith("http") else f"https://bina.az{href}"
            items.append(RawListingItem(
                external_id=f"bina_{ext_id}",
                title=title,
                description=full_desc,
                price=price,
                currency=currency,
                district=district,
                metro_station=metro,
                phone_number=extracted_phone,
                rooms=rooms,
                area_sqm=area,
                floor=floor,
                total_floors=total_floors,
                building_type=bld_type,
                seller_type=seller_type,
                offer_type=detected_offer,
                property_type=detected_prop,
                listing_url=clean_url,
                photos=card_photos
            ))

        logger.info(f"[BinaAzScraper] Extracted {len(items)} listings across all categories.")
        return items
