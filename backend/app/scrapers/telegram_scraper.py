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

        return items
