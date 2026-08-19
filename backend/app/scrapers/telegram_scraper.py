import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List, Optional
from app.core.config import settings
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers
from app.core.baku_locations import (
    extract_baku_district, extract_metro_station, extract_baku_settlement,
    extract_az_phone, SETTLEMENT_TO_DISTRICT, METRO_TO_DISTRICT
)
from app.core.property_classifier import classify_property_and_offer

logger = logging.getLogger(__name__)

class TelegramChannelScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "@emlaktap") -> List[RawListingItem]:
        clean_handle = re.sub(r'^(https?://)?(t\.me/s/|t\.me/|@)?', '', url_or_handle).strip('/')
        logger.info(f"[TelegramChannelScraper] Scraping public channel: @{clean_handle}")
        items: List[RawListingItem] = []

        # 1. Scrape open web preview without needing credentials
        try:
            target_url = f"https://t.me/s/{clean_handle}"
            headers = get_random_headers(referer="https://t.me/")
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"

            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(target_url, headers=headers)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    messages = soup.find_all("div", class_=re.compile(r'tgme_widget_message_wrap'))

                    for m in messages:
                        text_div = m.find("div", class_=re.compile(r'tgme_widget_message_text'))
                        if not text_div:
                            continue
                        raw_text = text_div.get_text(separator=" | ", strip=True)
                        if len(raw_text) < 15:
                            continue

                        link_tag = m.find("a", class_=re.compile(r'tgme_widget_message_date'))
                        msg_url = link_tag['href'] if link_tag and 'href' in link_tag.attrs else f"https://t.me/{clean_handle}"
                        msg_id = msg_url.split('/')[-1] if '/' in msg_url else str(hash(raw_text))

                        photos = []
                        photo_tag = m.find("a", class_=re.compile(r'tgme_widget_message_photo_wrap'))
                        if photo_tag and 'style' in photo_tag.attrs:
                            bg_match = re.search(r"background-image:url\('([^']+)'\)", photo_tag['style'])
                            if bg_match:
                                photos.append(bg_match.group(1))

                        parsed_item = self.parse_telegram_message_text(
                            text=raw_text,
                            msg_url=msg_url,
                            msg_id=f"tg_{clean_handle}_{msg_id}",
                            channel_handle=clean_handle,
                            photos=photos
                        )
                        if parsed_item:
                            items.append(parsed_item)

                        if len(items) >= 30:
                            break

        except Exception as e:
            logger.warning(f"[TelegramChannelScraper] Web preview error: {e}")

        # 2. Optional Telethon fallback if credentials configured
        if not items and settings.TELEGRAM_API_ID and settings.TELEGRAM_API_HASH:
            try:
                from telethon import TelegramClient
                client = TelegramClient('anon_session', settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
                await client.connect()
                channel_entity = await client.get_entity(f"@{clean_handle}")
                messages = await client.get_messages(channel_entity, limit=10)

                for msg in messages:
                    if msg.message and len(msg.message) > 20:
                        parsed = self.parse_telegram_message_text(
                            text=msg.message,
                            msg_url=f"https://t.me/{clean_handle}/{msg.id}",
                            msg_id=f"tg_{clean_handle}_{msg.id}",
                            channel_handle=clean_handle
                        )
                        if parsed:
                            items.append(parsed)
                await client.disconnect()
            except Exception as e:
                logger.error(f"[TelegramChannelScraper] Telethon error: {e}")

        logger.info(f"[TelegramChannelScraper] Extracted {len(items)} listings from @{clean_handle}.")
        return items

    @staticmethod
    def parse_telegram_message_text(
        text: str,
        msg_url: str,
        msg_id: str,
        channel_handle: str = "telegram",
        photos: Optional[List[str]] = None
    ) -> Optional[RawListingItem]:
        """
        Parses raw Azerbaijani real estate text from a Telegram message into a structured RawListingItem.
        """
        if not text or len(text.strip()) < 15:
            return None

        raw_lower = text.lower()

        # 1. Price Extraction
        price_m = (
            re.search(r'([\d,.\s]+)\s*(?:AZN|₼|manat|USD|\$|\/\s*ay|\/\s*gün)', text, re.IGNORECASE) or
            re.search(r'(?:qiymət|qiymeti|qiyməti|qiymət:|qiymeti:)\s*([\d,.\s]+)', text, re.IGNORECASE) or
            re.search(r'(\d+)\s*min\s*(?:azn|manat|usd|\$)?', text, re.IGNORECASE) or
            re.search(r'(\d+[\d\s]*000)\s*(?:azn|manat)?', text, re.IGNORECASE)
        )
        price = 0.0
        currency = "AZN"
        if price_m:
            if "min" in price_m.group(0).lower():
                num_part = re.search(r'\d+', price_m.group(0))
                price = float(num_part.group()) * 1000 if num_part else 0.0
            else:
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
            url=msg_url,
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
            external_id=msg_id,
            title=title,
            description=f"Telegram (@{channel_handle}): {text[:400]}",
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
            listing_url=msg_url
        )
