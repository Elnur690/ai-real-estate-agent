import logging
from typing import List
from app.core.config import settings
from app.scrapers.base import BaseScraper, RawListingItem

logger = logging.getLogger(__name__)

class TelegramChannelScraper(BaseScraper):
    async def scrape_source(self, url_or_handle: str = "@baki_emlak_elanlari") -> List[RawListingItem]:
        logger.info(f"[TelegramChannelScraper] Scraping public channel {url_or_handle}")
        items: List[RawListingItem] = []

        if settings.TELEGRAM_API_ID and settings.TELEGRAM_API_HASH:
            try:
                from telethon import TelegramClient
                client = TelegramClient('anon_session', settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
                await client.connect()
                channel_entity = await client.get_entity(url_or_handle)
                messages = await client.get_messages(channel_entity, limit=10)

                for msg in messages:
                    if msg.message and len(msg.message) > 20:
                        items.append(RawListingItem(
                            external_id=f"tg_{msg.id}",
                            title=msg.message[:50] + "...",
                            description=msg.message,
                            price=0.0,  # Will be parsed by AI layer
                            currency="AZN",
                            listing_url=f"https://t.me/{url_or_handle.replace('@', '')}/{msg.id}"
                        ))
                await client.disconnect()
            except Exception as e:
                logger.error(f"[TelegramChannelScraper] Telethon error: {e}")

        if not items:
            logger.info("[TelegramChannelScraper] Using sample Telegram channel listing for testing")
            items.append(RawListingItem(
                external_id="tg_sample_303",
                title="Xətai r. 3 otaqlı yeni tikili 130000 AZN",
                description="Xətai rayonu, Həzi Aslanov metrosu yaxınlığında 3 otaqlı 105 kv/m mənzil satılır. Qiymət: 130000 AZN. Əlaqə: 0501234567.",
                price=130000.0,
                currency="AZN",
                district="Xətai",
                rooms=3,
                area_sqm=105.0,
                building_type="new",
                seller_type="owner",
                photos=[],
                listing_url="https://t.me/baki_emlak_elanlari/303"
            ))

        return items
