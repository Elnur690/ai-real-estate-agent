import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List, Optional
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers
from app.core.baku_locations import (
    extract_baku_district, extract_metro_station, extract_baku_settlement,
    extract_az_phone, SETTLEMENT_TO_DISTRICT, METRO_TO_DISTRICT
)
from app.core.property_classifier import classify_property_and_offer

logger = logging.getLogger(__name__)

class FacebookScraper(BaseScraper):
    """
    Scraper and ingestor for Facebook Real Estate Groups and Public Pages.
    Extracts property listings from public Facebook group web endpoints,
    mobile web mirrors (m.facebook / mbasic), and structured group feeds.
    """

    async def scrape_source(self, url_or_handle: str) -> List[RawListingItem]:
        logger.info(f"[FacebookScraper] Scraping Facebook group/page: {url_or_handle}")
        items: List[RawListingItem] = []

        clean_url = url_or_handle.strip()
        group_match = re.search(r'facebook\.com/(?:groups/)?([^/?#]+)', clean_url)
        identifier = group_match.group(1) if group_match else clean_url.split('/')[-1]

        target_urls = [
            f"https://mbasic.facebook.com/groups/{identifier}" if "groups" in clean_url else f"https://mbasic.facebook.com/{identifier}",
            f"https://m.facebook.com/groups/{identifier}" if "groups" in clean_url else f"https://m.facebook.com/{identifier}",
            clean_url
        ]

        headers = get_random_headers(referer="https://m.facebook.com/")
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        headers["Accept-Language"] = "az,ru;q=0.9,en-US;q=0.8,en;q=0.7"

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                for target_url in target_urls:
                    try:
                        res = await client.get(target_url, headers=headers)
                        if res.status_code != 200 or len(res.text) < 500:
                            continue

                        soup = BeautifulSoup(res.text, "html.parser")
                        posts = (
                            soup.find_all("article") or
                            soup.find_all("div", role="article") or
                            soup.find_all("div", class_=re.compile(r'story_body_container|feed_story|async_like|msg', re.I)) or
                            soup.find_all("div", id=re.compile(r'm_story_permalink|u_0_', re.I))
                        )

                        for post in posts:
                            raw_text = post.get_text(separator=" | ", strip=True).replace('\xa0', ' ')
                            if len(raw_text) < 25:
                                continue

                            link_el = post.find("a", href=re.compile(r'story_fbid=|permalink/|/posts/|/story\.php'))
                            post_href = link_el['href'] if link_el and 'href' in link_el.attrs else ""
                            post_url = f"https://facebook.com{post_href}" if post_href.startswith('/') else (post_href or clean_url)

                            post_id_m = re.search(r'(?:story_fbid=|permalink/|posts/)(\d+)', post_url) or re.search(r'(\d{8,})', post_url)
                            post_id = post_id_m.group(1) if post_id_m else str(hash(raw_text[:100]))

                            parsed_item = self.parse_facebook_post_text(
                                text=raw_text,
                                post_url=post_url,
                                post_id=f"fb_{identifier}_{post_id}",
                                source_name=f"Facebook ({identifier})"
                            )
                            if parsed_item:
                                items.append(parsed_item)

                        if items:
                            break
                    except Exception as e:
                        logger.debug(f"[FacebookScraper] Error fetching from {target_url}: {e}")
                        continue

        except Exception as e:
            logger.error(f"[FacebookScraper] Top level error scraping {url_or_handle}: {e}")

        logger.info(f"[FacebookScraper] Extracted {len(items)} listings from {url_or_handle}")
        return items

    @staticmethod
    def parse_facebook_post_text(
        text: str,
        post_url: str,
        post_id: str,
        source_name: str = "Facebook",
        photos: Optional[List[str]] = None
    ) -> Optional[RawListingItem]:
        """
        Parses raw Azerbaijani real estate text from a Facebook post into a structured RawListingItem.
        """
        if not text or len(text.strip()) < 15:
            return None

        raw_lower = text.lower()

        # 1. Price Extraction
        price_m = (
            re.search(r'([\d,.\s]+)\s*(?:AZN|₼|manat|USD|\$|\/\s*ay|\/\s*gün)', text, re.IGNORECASE) or
            re.search(r'(?:qiymət|qiymeti|qiyməti|qiymət:|qiymeti:)\s*([\d,.\s]+)', text, re.IGNORECASE) or
            re.search(r'(\d+[\d\s]*000)\s*(?:azn|manat)?', text, re.IGNORECASE)
        )
        price = 0.0
        currency = "AZN"
        if price_m:
            clean_pr = price_m.group(1).replace(" ", "").replace(",", "").replace("\xa0", "").strip()
            if clean_pr and clean_pr.replace(".", "", 1).isdigit():
                price = float(clean_pr)
            if "$" in price_m.group(0) or "usd" in price_m.group(0).lower():
                currency = "USD"

        # 2. Room Count
        rooms_m = re.search(r'(\d+)\s*[- ]*otaq', text, re.IGNORECASE)
        rooms = int(rooms_m.group(1)) if rooms_m else None

        # 3. Area
        area_m = re.search(r'([\d.]+)\s*(?:m²|kv|kvm|m2|kv\.m)', text, re.IGNORECASE)
        area = float(area_m.group(1)) if area_m else None

        # 4. Floor
        floor_m = re.search(r'(\d+)\s*/\s*(\d+)', text) or re.search(r'(\d+)[- ]*ci\s*mərtəbə', text, re.IGNORECASE)
        floor = int(floor_m.group(1)) if floor_m else None
        total_floors = int(floor_m.group(2)) if (floor_m and len(floor_m.groups()) >= 2 and floor_m.group(2)) else None

        # 5. Location Extraction
        district = extract_baku_district(text)
        settlement = extract_baku_settlement(text)
        metro = extract_metro_station(text)

        if not district:
            if settlement and settlement in SETTLEMENT_TO_DISTRICT:
                district = SETTLEMENT_TO_DISTRICT[settlement]
            elif metro and metro in METRO_TO_DISTRICT:
                district = METRO_TO_DISTRICT[metro]

        # 6. Contact Phone Extraction
        phone_res = extract_az_phone(text)
        phone = phone_res[0] if phone_res else None

        # 7. Property & Seller Classification
        detected_offer, detected_prop, detected_seller = classify_property_and_offer(
            title=text[:60],
            description=text,
            url=post_url,
            raw_text=text
        )

        prop_label_map = {
            "apartment": "Mənzil",
            "house": "Həyət evi / Villa",
            "office": "Ofis",
            "commercial": "Obyekt",
            "land": "Torpaq sahəsi"
        }
        prop_name = prop_label_map.get(detected_prop, "Əmlak")
        loc_label = settlement or metro or district or "Bakı"
        title = f"{rooms} otaqlı {prop_name} ({loc_label})" if rooms else f"{prop_name} ({loc_label})"

        bld_type = "old" if any(k in raw_lower for k in ["köhnə", "kohne", "leninqrad", "xruşov", "kiyev", "stalinka"]) else "new"

        return RawListingItem(
            external_id=post_id,
            title=title,
            description=f"{source_name}: {text[:400]}",
            price=price,
            currency=currency,
            district=district,
            metro_station=metro,
            address_raw=loc_label,
            phone_number=phone,
            rooms=rooms,
            area_sqm=area,
            floor=floor,
            total_floors=total_floors,
            building_type=bld_type,
            seller_type=detected_seller,
            offer_type=detected_offer,
            property_type=detected_prop,
            photos=photos or [],
            listing_url=post_url
        )
