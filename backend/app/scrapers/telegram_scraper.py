import re
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from app.core.config import settings
from app.scrapers.base import BaseScraper, RawListingItem
from app.scrapers.utils import get_random_headers
from app.core.baku_locations import extract_baku_district, extract_metro_station, extract_az_phone
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

                        price_m = re.search(r'([\d,.\s]+)\s*(?:AZN|₼|manat|USD|\$)', raw_text, re.IGNORECASE)
                        clean_pr = price_m.group(1).replace(" ", "").replace(",", "").replace("\xa0", "") if price_m else "0"
                        price = float(clean_pr) if clean_pr and clean_pr.replace(".", "", 1).isdigit() else 0.0

                        rooms_m = re.search(r'(\d+)\s*[- ]*otaq', raw_text, re.IGNORECASE)
                        rooms = int(rooms_m.group(1)) if rooms_m else None

                        area_m = re.search(r'([\d.]+)\s*m²', raw_text) or re.search(r'([\d.]+)\s*kv', raw_text)
                        area = float(area_m.group(1)) if area_m else None

                        floor_m = re.search(r'(\d+)\s*/\s*(\d+)', raw_text)
                        floor = int(floor_m.group(1)) if floor_m else None
                        total_floors = int(floor_m.group(2)) if floor_m else None

                        district = extract_baku_district(raw_text)
                        metro = extract_metro_station(raw_text)
                        phone = extract_az_phone(raw_text)

                        detected_offer, detected_prop, detected_seller = classify_property_and_offer(
                            title=raw_text[:60],
                            description=raw_text,
                            url=msg_url,
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
                        loc_label = metro or district or "Bakı"
                        title = f"{rooms} otaqlı {prop_name} ({loc_label})" if rooms else f"{prop_name} ({loc_label})"

                        items.append(RawListingItem(
                            external_id=f"tg_{clean_handle}_{msg_id}",
                            title=title,
                            description=f"Telegram ({clean_handle}): {raw_text[:350]}",
                            price=price,
                            currency="AZN",
                            district=district,
                            metro_station=metro,
                            phone_number=phone[0] if phone else None,
                            rooms=rooms,
                            area_sqm=area,
                            floor=floor,
                            total_floors=total_floors,
                            building_type="old" if "köhnə" in raw_text.lower() else "new",
                            seller_type=detected_seller,
                            offer_type=detected_offer,
                            property_type=detected_prop,
                            listing_url=msg_url
                        ))
                        if len(items) >= 25:
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
                        items.append(RawListingItem(
                            external_id=f"tg_{clean_handle}_{msg.id}",
                            title=msg.message[:50] + "...",
                            description=msg.message,
                            price=0.0,
                            currency="AZN",
                            listing_url=f"https://t.me/{clean_handle}/{msg.id}"
                        ))
                await client.disconnect()
            except Exception as e:
                logger.error(f"[TelegramChannelScraper] Telethon error: {e}")

        logger.info(f"[TelegramChannelScraper] Extracted {len(items)} listings from @{clean_handle}.")
        return items
