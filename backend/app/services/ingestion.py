import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.listing import ListingSource, Listing
from app.models.saved_search import SavedSearch
from app.models.match import Match
from app.scrapers.bina_az import BinaAzScraper
from app.scrapers.tap_az import TapAzScraper
from app.scrapers.telegram_scraper import TelegramChannelScraper
from app.ai.factory import ProviderFactory
from app.ai.base import StructuredCriteria
from app.bot.telegram_adapter import send_telegram_notification
from app.bot.whatsapp_adapter import WhatsAppAdapter
from app.bot.command_handler import get_app_name

logger = logging.getLogger(__name__)

class IngestionService:
    @staticmethod
    async def seed_default_sources(db: AsyncSession):
        stmt = select(ListingSource)
        res = await db.execute(stmt)
        sources = res.scalars().all()
        if not sources:
            default_sources = [
                ListingSource(type="website", name="Bina.az", url_or_handle="https://bina.az/baki/alqi-satki/menziller", status="active"),
                ListingSource(type="website", name="Tap.az", url_or_handle="https://tap.az/elanlar/dasinmaz-emlak/menziller", status="active"),
                ListingSource(type="telegram_channel", name="Bakı Əmlak Elanları", url_or_handle="@baki_emlak_elanlari", status="active")
            ]
            for s in default_sources:
                db.add(s)
            await db.commit()
            logger.info("[IngestionService] Seeded default listing sources.")

    @staticmethod
    async def run_ingestion_cycle(db: AsyncSession) -> dict:
        await IngestionService.seed_default_sources(db)
        
        stmt = select(ListingSource).where(ListingSource.status == "active")
        res = await db.execute(stmt)
        sources = res.scalars().all()

        total_scraped = 0
        total_matched = 0

        for source in sources:
            logger.info(f"[IngestionService] Scraping source: {source.name} ({source.type})")
            scraper = None
            if "bina.az" in source.url_or_handle or source.name.lower() == "bina.az":
                scraper = BinaAzScraper()
            elif "tap.az" in source.url_or_handle or source.name.lower() == "tap.az":
                scraper = TapAzScraper()
            elif source.type == "telegram_channel":
                scraper = TelegramChannelScraper()
            else:
                scraper = BinaAzScraper()

            try:
                items = await scraper.scrape_source(source.url_or_handle)
                source.last_scraped_at = datetime.now(timezone.utc)
                await db.commit()

                for item in items:
                    # Check if listing already exists
                    stmt_exist = select(Listing).where(Listing.external_id == item.external_id)
                    res_exist = await db.execute(stmt_exist)
                    existing_listing = res_exist.scalars().first()

                    if existing_listing:
                        # Price drop check
                        if item.price < existing_listing.price:
                            history = existing_listing.price_history or []
                            history.append({
                                "old_price": existing_listing.price,
                                "new_price": item.price,
                                "date": datetime.now(timezone.utc).isoformat()
                            })
                            existing_listing.price_history = history
                            existing_listing.price = item.price
                        existing_listing.last_seen_at = datetime.now(timezone.utc)
                        await db.commit()
                        db_listing = existing_listing
                    else:
                        db_listing = Listing(
                            source_id=source.id,
                            external_id=item.external_id,
                            title=item.title,
                            description=item.description,
                            price=item.price,
                            currency=item.currency,
                            district=item.district,
                            address_raw=item.address_raw,
                            rooms=item.rooms,
                            area_sqm=item.area_sqm,
                            floor=item.floor,
                            total_floors=item.total_floors,
                            building_type=item.building_type,
                            seller_type=item.seller_type,
                            photos=item.photos,
                            listing_url=item.listing_url,
                            is_active=True
                        )
                        db.add(db_listing)
                        await db.commit()
                        await db.refresh(db_listing)
                        total_scraped += 1

                    # Evaluate matches against active searches
                    matches_created = await IngestionService._evaluate_and_deliver_matches(db, db_listing)
                    total_matched += matches_created

            except Exception as e:
                logger.error(f"[IngestionService] Error processing source {source.name}: {e}")
                source.status = "error"
                await db.commit()

        return {"scraped_count": total_scraped, "matched_count": total_matched}

    @staticmethod
    async def _evaluate_and_deliver_matches(db: AsyncSession, listing: Listing) -> int:
        stmt = select(SavedSearch).where(SavedSearch.is_active == True)
        res = await db.execute(stmt)
        saved_searches = res.scalars().all()

        matches_count = 0
        app_name = await get_app_name(db)

        for search in saved_searches:
            # Fetch Tenant
            stmt_t = select(Tenant).where(Tenant.id == search.tenant_id)
            res_t = await db.execute(stmt_t)
            tenant = res_t.scalars().first()

            if not tenant:
                continue

            # Re-construct structured criteria
            criteria = StructuredCriteria(
                district=search.district,
                min_price=search.min_price,
                max_price=search.max_price,
                min_rooms=search.min_rooms,
                max_rooms=search.max_rooms,
                seller_type=search.seller_type or "any",
                building_type=search.building_type or "any"
            )

            # Score match via AI Provider Factory
            ai_provider = await ProviderFactory.get_provider(db, task_type="match_scoring", tenant_id=tenant.id)
            listing_dict = {
                "title": listing.title,
                "price": listing.price,
                "district": listing.district,
                "rooms": listing.rooms,
                "seller_type": listing.seller_type
            }
            score = await ai_provider.score_match(listing_dict, criteria)

            if score >= 0.65:
                # Check duplicate match
                stmt_m = select(Match).where(Match.listing_id == listing.id, Match.saved_search_id == search.id)
                res_m = await db.execute(stmt_m)
                if res_m.scalars().first():
                    continue

                new_match = Match(
                    listing_id=listing.id,
                    saved_search_id=search.id,
                    tenant_id=tenant.id,
                    score=score,
                    delivered_at=datetime.now(timezone.utc),
                    delivery_channel=tenant.preferred_channel,
                    status="sent"
                )
                db.add(new_match)
                await db.commit()
                await db.refresh(new_match)
                matches_count += 1

                # Construct Azerbaijani Notification Message
                seller_str = "Ev Sahibindən" if listing.seller_type == "owner" else "Vasitəçidən/Agentlikdən"
                bld_str = "Yeni tikili" if listing.building_type == "new" else ("Köhnə tikili" if listing.building_type == "old" else "")
                
                msg_text = (
                    f"🔥 *YENİ UYĞUN ELAN! ({app_name})*\n"
                    f"🎯 *Uyğunluq:* %{int(score * 100)}\n\n"
                    f"🏠 *{listing.title}*\n"
                    f"💰 *Qiymət:* {int(listing.price)} {listing.currency}\n"
                    f"📍 *Məkan:* {listing.district or listing.address_raw or 'Bakı'}\n"
                    f"📐 *Otaq / Sahə:* {listing.rooms or '-'} otaqlı | {listing.area_sqm or '-'} m²\n"
                    f"👤 *Satıcı:* {seller_str}\n"
                    f"🏢 *Bina:* {bld_str}\n\n"
                    f"🔗 [Elana keçid et]({listing.listing_url})\n\n"
                    f"💬 *Reaksiya bildirin:*\n"
                    f"`Maraqlanıram {new_match.id}` | `Keç {new_match.id}` | `Satılıb {new_match.id}`"
                )

                # Dispatch notification
                if tenant.preferred_channel == "telegram" and tenant.telegram_chat_id:
                    await send_telegram_notification(tenant.telegram_chat_id, msg_text)
                elif tenant.preferred_channel == "whatsapp" and tenant.whatsapp_number:
                    await WhatsAppAdapter.send_message(tenant.whatsapp_number, msg_text)

        return matches_count
