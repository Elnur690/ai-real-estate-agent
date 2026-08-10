import logging
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.listing import Listing
from app.models.saved_search import SavedSearch
from app.models.b2b_match import B2BMatch
from app.bot.telegram_adapter import send_telegram_notification
from app.bot.whatsapp_adapter import WhatsAppAdapter
from app.bot.command_handler import get_app_name

logger = logging.getLogger(__name__)

class B2BService:
    @staticmethod
    async def evaluate_b2b_cobrokering(db: AsyncSession, listing: Listing) -> int:
        """
        Evaluates an exclusive property submitted by Agent B against active saved searches of Agent A.
        Creates B2BMatch records and notifies both agents for 50/50 commission co-brokering.
        """
        if not listing.source_id:
            return 0

        stmt_searches = select(SavedSearch).where(SavedSearch.is_active == True)
        res_searches = await db.execute(stmt_searches)
        searches = res_searches.scalars().all()

        app_name = await get_app_name(db)
        b2b_count = 0

        for s in searches:
            # Check buyer tenant has B2B feature enabled
            stmt_t = select(Tenant).where(Tenant.id == s.tenant_id, Tenant.status == "active", Tenant.feature_b2b_cobrokering == True)
            res_t = await db.execute(stmt_t)
            buyer_tenant = res_t.scalars().first()

            if not buyer_tenant:
                continue

            # Evaluate matching criteria
            district_match = (not s.district) or (s.district.lower() in (listing.district or "").lower())
            price_match = (not s.max_price or listing.price <= s.max_price) and (not s.min_price or listing.price >= s.min_price)
            room_match = (not s.min_rooms or (listing.rooms and listing.rooms >= s.min_rooms))

            if district_match and price_match and room_match:
                # Check existing B2B match
                stmt_exist = select(B2BMatch).where(
                    B2BMatch.buyer_tenant_id == buyer_tenant.id,
                    B2BMatch.listing_id == listing.id
                )
                res_exist = await db.execute(stmt_exist)
                if res_exist.scalars().first():
                    continue

                # Create B2B Match
                b2b = B2BMatch(
                    buyer_tenant_id=buyer_tenant.id,
                    seller_tenant_id=listing.source_id, # Source owner tenant
                    saved_search_id=s.id,
                    listing_id=listing.id,
                    status="pending"
                )
                db.add(b2b)
                await db.commit()
                await db.refresh(b2b)
                b2b_count += 1

                # Send B2B Notification to Buyer Agent
                msg = (
                    f"🤝 *YENİ B2B PARTNYORLUQ İMKANI! ({app_name})*\n"
                    f"Başqa bir agent platformada sizin axtarışınıza (%50/50 Komissiya) tam uyğun eksklüziv elan paylaşdı!\n\n"
                    f"🏠 *{listing.title}*\n"
                    f"💰 *Qiymət:* {int(listing.price)} {listing.currency}\n"
                    f"📍 *Məkan:* {listing.district or 'Bakı'}\n\n"
                    f"💬 *Əlaqə yaratmaq üçün cavab verin:*\n"
                    f"`B2B Qəbul et {b2b.id}` | `B2B İmtina {b2b.id}`"
                )

                if buyer_tenant.preferred_channel == "telegram" and buyer_tenant.telegram_chat_id:
                    await send_telegram_notification(buyer_tenant.telegram_chat_id, msg)
                elif buyer_tenant.preferred_channel == "whatsapp" and buyer_tenant.whatsapp_number:
                    await WhatsAppAdapter.send_message(buyer_tenant.whatsapp_number, msg)

        return b2b_count
