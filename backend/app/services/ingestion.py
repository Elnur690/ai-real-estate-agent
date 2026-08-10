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
from app.scrapers.yeniemlak_az import YeniEmlakAzScraper
from app.scrapers.evonline_az import EvOnlineAzScraper
from app.scrapers.ev10_az import Ev10AzScraper
from app.scrapers.vipemlak_az import VipEmlakAzScraper
from app.scrapers.ofis_az import OfisAzScraper
from app.scrapers.kub_az import KubAzScraper
from app.scrapers.lalafo_az import LalafoAzScraper
from app.scrapers.homdom_az import HomDomAzScraper
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
        if not sources or len(sources) < 10:
            existing_handles = {s.url_or_handle for s in sources}
            default_sources = [
                ListingSource(type="website", name="Bina.az", url_or_handle="https://bina.az/", status="active"),
                ListingSource(type="website", name="Tap.az", url_or_handle="https://tap.az/elanlar/dasinmaz-emlak/menziller", status="active"),
                ListingSource(type="website", name="YeniEmlak.az", url_or_handle="https://yeniemlak.az/", status="active"),
                ListingSource(type="website", name="EvOnline.az", url_or_handle="https://evonline.az/index.php", status="active"),
                ListingSource(type="website", name="Ev10.az", url_or_handle="https://ev10.az/", status="active"),
                ListingSource(type="website", name="VipEmlak.az", url_or_handle="https://vipemlak.az/", status="active"),
                ListingSource(type="website", name="Ofis.az", url_or_handle="https://ofis.az/", status="active"),
                ListingSource(type="website", name="Kub.az", url_or_handle="https://kub.az/", status="active"),
                ListingSource(type="website", name="Lalafo.az", url_or_handle="https://lalafo.az/baku/nedvizhimost", status="active"),
                ListingSource(type="website", name="HomDom.az", url_or_handle="https://homdom.az/offers/kiraye", status="active"),
                ListingSource(type="telegram_channel", name="Bakı Əmlak Elanları", url_or_handle="@baki_emlak_elanlari", status="active")
            ]
            for s in default_sources:
                if s.url_or_handle not in existing_handles:
                    db.add(s)
            await db.commit()
            logger.info("[IngestionService] Seeded comprehensive listing sources (10 websites + Telegram).")

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
            url = source.url_or_handle.lower()
            name = source.name.lower()
            scraper = None

            if "bina.az" in url or "bina.az" in name:
                scraper = BinaAzScraper()
            elif "tap.az" in url or "tap.az" in name:
                scraper = TapAzScraper()
            elif "yeniemlak.az" in url or "yeniemlak.az" in name:
                scraper = YeniEmlakAzScraper()
            elif "evonline.az" in url or "evonline.az" in name:
                scraper = EvOnlineAzScraper()
            elif "ev10.az" in url or "ev10.az" in name:
                scraper = Ev10AzScraper()
            elif "vipemlak.az" in url or "vipemlak.az" in name:
                scraper = VipEmlakAzScraper()
            elif "ofis.az" in url or "ofis.az" in name:
                scraper = OfisAzScraper()
            elif "kub.az" in url or "kub.az" in name:
                scraper = KubAzScraper()
            elif "lalafo.az" in url or "lalafo.az" in name:
                scraper = LalafoAzScraper()
            elif "homdom.az" in url or "homdom.az" in name:
                scraper = HomDomAzScraper()
            elif source.type == "telegram_channel":
                scraper = TelegramChannelScraper()
            else:
                scraper = BinaAzScraper()

            try:
                items = await scraper.scrape_source(source.url_or_handle)
                source.last_scraped_at = datetime.now(timezone.utc)
                await db.commit()

                for item in items:
                    stmt_exist = select(Listing).where(Listing.external_id == item.external_id)
                    res_exist = await db.execute(stmt_exist)
                    existing_listing = res_exist.scalars().first()

                    if existing_listing:
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
            stmt_t = select(Tenant).where(Tenant.id == search.tenant_id)
            res_t = await db.execute(stmt_t)
            tenant = res_t.scalars().first()

            if not tenant:
                continue

            criteria = StructuredCriteria(
                district=search.district,
                min_price=search.min_price,
                max_price=search.max_price,
                min_rooms=search.min_rooms,
                max_rooms=search.max_rooms,
                seller_type=search.seller_type or "any",
                building_type=search.building_type or "any"
            )

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

                if tenant.preferred_channel == "telegram" and tenant.telegram_chat_id:
                    await send_telegram_notification(tenant.telegram_chat_id, msg_text)
                elif tenant.preferred_channel == "whatsapp" and tenant.whatsapp_number:
                    await WhatsAppAdapter.send_message(tenant.whatsapp_number, msg_text)

        return matches_count
